import io

import pymupdf
import pytest

from app.extensions import db
from app.models import (AuditLog, Bookmark, ExamSession, Paper, PaperComponent, PaperVariant, Prediction,
                        PredictionFeedback, PredictionRun, Question, QuestionTopic, QuestionType, Role,
                        StudyPlan, Subject, TopicStat, User)
from app.seed import seed_all
from app.services.aggregation import SERIES_ORDER
from app.services.topic_model import current_topics


@pytest.fixture()
def client(app):
    seed_all()
    return app.test_client()


def login(client, username):
    resp = client.post("/auth/login", data={"identifier": username, "password": "Demo#12345"})
    assert resp.status_code == 302
    return client


def make_pdf(lines):
    doc = pymupdf.open()
    doc.new_page().insert_text((50, 60), "\n".join(lines), fontsize=9)
    data = doc.tobytes()
    doc.close()
    return data


QP = ["5054/12/M/J/21", "1 Which unit is used to measure force?", "A joule", "B newton", "C watt", "D pascal",
      "2 A car has constant acceleration from rest. Which graph shows velocity?", "A straight line", "B curve", "C flat", "D steep",
      "3 A resistor has a current of 2 A and a voltage of 6 V. What is the resistance?", "A 3 ohm", "B 12 ohm", "C 0.3 ohm", "D 8 ohm",
      "4 A sample has a half-life of 3 days. Which radiation is gamma?", "A alpha", "B beta", "C gamma", "D proton"]
MS = ["Question Answer Marks", "1 B 1", "2 A 1", "3 A 1", "4 C 1"]


def upload(client, qp_name="5054_s21_qp_12.pdf", ms_name="5054_s21_ms_12.pdf", with_ms=True):
    data = {"qp_file": (io.BytesIO(make_pdf(QP)), qp_name)}
    if with_ms:
        data["ms_file"] = (io.BytesIO(make_pdf(MS)), ms_name)
    return client.post("/papers/upload", data=data, content_type="multipart/form-data")


def test_upload_runs_the_whole_pipeline(client):
    login(client, "contributor")
    resp = upload(client)
    assert resp.status_code == 302 and "/papers/" in resp.headers["Location"]
    paper = Paper.query.one()
    assert len(paper.files) == 2 and paper.session.label == "May/Jun 2021"
    qs = sorted(paper.questions, key=lambda q: q.number)
    assert [q.number for q in qs] == [1, 2, 3, 4]
    assert [o.label for o in qs[0].options if o.is_correct] == ["B"]
    run = paper.extraction_runs[-1]
    assert run.status == "done" and run.questions_found == 4 and "expected 40" in run.error_message
    assert paper.status == "needs_review" and all(q.topic_links for q in qs)
    page = client.get(f"/papers/{paper.id}").get_data(as_text=True)
    assert "Which unit is used" in page and client.get(f"/papers/{paper.id}/status").json["run"] == "done"


@pytest.mark.parametrize("qp_name,message", [
    ("physics.pdf", "File name must look like"),
    ("5054_s21_ms_12.pdf", "file but got"),
    ("9999_s21_qp_12.pdf", "Unknown subject code"),
])
def test_upload_server_side_validation(client, qp_name, message):
    login(client, "contributor")
    assert message in upload(client, qp_name=qp_name, with_ms=False).get_data(as_text=True)
    assert Paper.query.count() == 0


def test_upload_rejects_duplicates_and_mismatched_mark_scheme(client):
    login(client, "contributor")
    upload(client)
    assert "already been uploaded" in upload(client).get_data(as_text=True)
    assert "same paper" in upload(client, "5054_w21_qp_12.pdf", "5054_w21_ms_13.pdf").get_data(as_text=True)


def test_upload_permissions(client):
    assert upload(client).status_code == 302            # anonymous -> login
    login(client, "student")
    assert upload(client).status_code == 403            # wrong role


def test_delete_paper_removes_files(client):
    login(client, "contributor")
    upload(client)
    paper = Paper.query.one()
    assert client.post(f"/papers/{paper.id}/delete").status_code == 302
    assert Paper.query.count() == 0 and Question.query.count() == 0


def test_admin_crud_cycle_and_guards(client):
    login(client, "student")
    assert client.get("/admin/").status_code == 403
    client.post("/auth/logout")
    login(client, "admin")
    assert "roles" in client.get("/admin/").get_data(as_text=True)
    assert client.post("/admin/roles/new", data={"name": "tester", "description": "x"}).status_code == 302
    role = Role.query.filter_by(name="tester").one()
    assert client.post("/admin/roles/new", data={"name": "tester"}).status_code == 200   # duplicate -> message
    assert client.post(f"/admin/roles/{role.id}/edit", data={"name": "tester", "description": "changed"}).status_code == 302
    assert db.session.get(Role, role.id).description == "changed"
    assert client.post(f"/admin/roles/{role.id}/delete").status_code == 302
    assert Role.query.filter_by(name="tester").count() == 0
    assert AuditLog.query.filter(AuditLog.entity_type == "roles").count() == 3
    assert client.get("/admin/nope/").status_code == 404


def test_admin_lists_every_table_and_creates_users(client):
    login(client, "admin")
    for name in ("users", "user_roles", "topic_prerequisites", "question_topics", "audit_logs", "app_settings", "prediction_runs"):
        assert client.get(f"/admin/{name}/").status_code == 200, name
        assert client.get(f"/admin/{name}/new").status_code == 200, name
    resp = client.post("/admin/users/new", data={"username": "newbie", "email": "n@example.com", "password": "Passw0rdX", "is_active": "y"})
    assert resp.status_code == 302 and User.query.filter_by(username="newbie").one().check_password("Passw0rdX")


def synthetic_history(subject):
    """12 sessions x 6 approved questions; topics 0-2 appear every session, topic 3 every other session."""
    topics = current_topics(subject)
    component = PaperComponent.query.filter_by(subject_id=subject.id, paper_number=1).one()
    variant = PaperVariant.query.filter_by(component_id=component.id, variant_number=1).one()
    qtype = QuestionType.query.filter_by(code="mcq").one()
    sessions = sorted(ExamSession.query.all(), key=lambda s: (s.year, SERIES_ORDER[s.series_code]))[:12]
    for i, session in enumerate(sessions):
        paper = Paper(session=session, variant=variant, status="ready")
        for n in range(6):
            topic = topics[n % 3] if n < 4 or i % 2 == 0 else topics[3 + n % 4]
            q = Question(paper=paper, question_type=qtype, number=n + 1, text=f"q{n}", marks=1, review_status="approved")
            db.session.add(QuestionTopic(question=q, topic=topic, confidence=1.0, assigned_by="human"))
        db.session.add(paper)
    db.session.commit()


def test_prediction_dashboard_backtest_feedback(client):
    physics = Subject.query.filter_by(code="5054").one()
    login(client, "contributor")
    assert "at least 5" in client.post(f"/subjects/{physics.id}/predict", follow_redirects=True).get_data(as_text=True)
    synthetic_history(physics)
    resp = client.post(f"/subjects/{physics.id}/predict")
    assert resp.status_code == 302 and resp.headers["Location"].endswith(f"/subjects/{physics.id}/predictions")
    run = PredictionRun.query.one()
    assert len(run.predictions) == len(current_topics(physics)) and len(run.backtests) == 8
    assert TopicStat.query.count() > 0 and {p.tier for p in run.predictions} == {"very_likely", "likely", "lower"}
    top = min(run.predictions, key=lambda p: p.rank)
    assert top.topic_id in {t.id for t in current_topics(physics)[:3]}
    for path, text in ((f"/subjects/{physics.id}/dashboard", "Topic by session"),
                       (f"/subjects/{physics.id}/predictions", "what to study"),
                       (f"/subjects/{physics.id}/backtest", "Average hit rate")):
        assert text in client.get(path).get_data(as_text=True)
    assert client.post(f"/predictions/{top.id}/feedback", data={"rating": 5, "comment": "useful"}).status_code == 302
    assert PredictionFeedback.query.one().rating == 5
    assert "Rating must be" in client.post(f"/predictions/{top.id}/feedback", data={"rating": 9}, follow_redirects=True).get_data(as_text=True)


def test_study_plan_and_bookmark_crud(client):
    physics = Subject.query.filter_by(code="5054").one()
    synthetic_history(physics)
    login(client, "contributor")
    client.post(f"/subjects/{physics.id}/predict")
    client.post("/auth/logout")
    login(client, "student")
    data = {"subject_id": physics.id, "name": "Finals", "exam_date": "2030-05-01", "top_n": 5}
    assert "future" in client.post("/study/plans/new", data={**data, "exam_date": "2020-01-01"}).get_data(as_text=True)
    resp = client.post("/study/plans/new", data=data)
    plan = StudyPlan.query.one()
    assert resp.status_code == 302 and len(plan.items) == 5
    assert "already have a plan" in client.post("/study/plans/new", data=data).get_data(as_text=True)
    item = plan.items[0]
    client.post(f"/study/items/{item.id}/toggle")
    assert db.session.get(type(item), item.id).is_done
    assert client.post(f"/study/plans/{plan.id}/edit", data={"name": "Finals v2", "exam_date": "2031-01-01"}).status_code == 302
    assert db.session.get(StudyPlan, plan.id).name == "Finals v2"
    q = Question.query.first()
    client.post(f"/study/bookmarks/{q.id}")
    assert Bookmark.query.count() == 1
    client.post(f"/study/bookmarks/{q.id}")
    assert Bookmark.query.count() == 0
    client.post("/auth/logout")
    login(client, "contributor")
    assert client.get(f"/study/plans/{plan.id}").status_code == 404     # other users' plans are private
    client.post(f"/study/plans/{plan.id}/delete")


def test_review_queue_approves_and_logs(client):
    login(client, "contributor")
    upload(client)
    q = Question.query.filter_by(number=1).one()
    assert "Review queue" in client.get("/review/").get_data(as_text=True)
    topic = current_topics(Subject.query.filter_by(code="5054").one())[0]
    resp = client.post(f"/review/{q.id}", data={"text": q.text, "marks": 1, "topic_id": topic.id, "approve": "Approve"})
    assert resp.status_code == 302
    q = db.session.get(Question, q.id)
    assert q.review_status == "approved" and q.topic_links[0].assigned_by == "human" and q.topic_links[0].topic_id == topic.id
    assert AuditLog.query.filter_by(action="review").count() == 1
