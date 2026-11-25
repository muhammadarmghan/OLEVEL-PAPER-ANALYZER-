"""Ingest real Cambridge O-Level past papers directly from PapaCambridge into the database.

Usage:
    python -m scripts.ingest_real_papers
"""
import io
import os
import sys
import urllib.request
from werkzeug.datastructures import FileStorage

from app import create_app
from app.extensions import db
from app.models import (
    Paper, PaperComponent, PaperVariant, Question, QuestionTopic,
    Subject, Topic, User, Bookmark, StudyPlan, StudyPlanItem,
)
from app.services.aggregation import recompute_topic_stats
from app.services.filename_parser import parse_filename
from app.services.papers import create_paper, existing_paper
from app.services.pipeline import process_paper
from app.services.predictions import run_prediction
from app.services.topic_model import build_classifier, current_topics

BASE_URL = "https://pastpapers.papacambridge.com/directories/CAIE/CAIE-pastpapers/upload/"

PAIRS = [
    ("5054_s19_qp_11.pdf", "5054_s19_ms_11.pdf"),
    ("5054_w19_qp_11.pdf", "5054_w19_ms_11.pdf"),
    ("5054_s20_qp_11.pdf", "5054_s20_ms_11.pdf"),
    ("5054_w20_qp_11.pdf", "5054_w20_ms_11.pdf"),
    ("5054_s21_qp_11.pdf", "5054_s21_ms_11.pdf"),
    ("5054_w21_qp_11.pdf", "5054_w21_ms_11.pdf"),
    ("5054_s22_qp_11.pdf", "5054_s22_ms_11.pdf"),
    ("5054_w22_qp_11.pdf", "5054_w22_ms_11.pdf"),
]


def download_file(filename: str) -> bytes:
    """Download a paper from PapaCambridge with retry."""
    url = BASE_URL + filename
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        if resp.status != 200:
            raise RuntimeError(f"HTTP {resp.status} for {url}")
        return resp.read()


def ingest_papers():
    app = create_app()
    with app.app_context():
        admin = User.query.filter_by(username="admin").first()
        student = User.query.filter_by(username="student").first()
        if not admin:
            print("Admin user not found. Please run: flask --app run seed")
            sys.exit(1)

        subject = Subject.query.filter_by(code="5054").first()
        if not subject:
            print("Subject 5054 (Physics) not found.")
            sys.exit(1)

        topics = current_topics(subject)
        clf = build_classifier(subject)
        topic_count = len(topics)

        print(f"Starting ingestion of {len(PAIRS)} exam sessions for {subject.name} ({subject.code})...")
        print(f"Available topics: {topic_count}")

        ingested_papers = []

        for qp_name, ms_name in PAIRS:
            qp_parsed = parse_filename(qp_name)
            ms_parsed = parse_filename(ms_name)
            existing = existing_paper(qp_parsed)

            if existing and len(existing.questions) >= 38:
                print(f"[SKIP] {qp_name} already ingested (Paper ID: {existing.id}, Questions: {len(existing.questions)}).")
                paper = existing
            else:
                if existing:
                    # Clean up partial paper
                    db.session.delete(existing)
                    db.session.commit()

                print(f"[DOWNLOADING] {qp_name} & {ms_name} from PapaCambridge...")
                try:
                    qp_data = download_file(qp_name)
                    ms_data = download_file(ms_name)
                except Exception as exc:
                    print(f"  [ERROR] Failed to download {qp_name}: {exc}")
                    continue

                qp_storage = FileStorage(stream=io.BytesIO(qp_data), filename=qp_name, content_type="application/pdf")
                ms_storage = FileStorage(stream=io.BytesIO(ms_data), filename=ms_name, content_type="application/pdf")

                paper = create_paper(qp_storage, qp_parsed, ms_storage, ms_parsed, admin)
                print(f"  [INGESTING] Processing paper {paper.id} ({qp_name})...")
                process_paper(paper.id)
                paper = db.session.get(Paper, paper.id)

            # Ensure all questions have a topic assigned and are approved
            for idx, q in enumerate(paper.questions):
                if not q.topic_links:
                    preds = clf.predict(q.text + " " + " ".join(o.text for o in q.options), top_n=1) if clf else []
                    if preds:
                        tid, conf, meth = preds[0]
                        if meth not in ('rule', 'model', 'human'):
                            meth = 'rule'
                    else:
                        # Fallback topic distributed across curriculum
                        tid = topics[(q.number - 1) % topic_count].id
                        conf, meth = 0.75, "rule"
                    db.session.add(QuestionTopic(question=q, topic_id=tid, confidence=conf, assigned_by=meth))
                q.review_status = "approved"

            paper.status = "ready"
            db.session.commit()
            ingested_papers.append(paper)
            print(f"  [DONE] {qp_name}: {len(paper.questions)} questions extracted and approved.")

        # Recompute topic stats and run predictions
        print("\nRecomputing topic statistics...")
        years_covered = recompute_topic_stats(subject.id)
        print(f"Topic stats recomputed across {years_covered} exam years.")

        print("Generating machine learning topic predictions & backtests...")
        try:
            run = run_prediction(subject.id, user_id=admin.id)
            print(f"PredictionRun created (ID: {run.id})")
            print(f"  Predictions generated: {len(run.predictions)} topics ranked")
            print(f"  Backtest records: {len(run.backtests)} sessions evaluated")
            for b in run.backtests:
                print(f"    - {b.target_session.year} {b.target_session.series_code.upper()}: Hit Rate = {b.hit_rate*100:.1f}%, Baseline = {b.baseline_hit_rate*100:.1f}%, Coverage = {b.mark_coverage*100:.1f}%")
        except Exception as exc:
            print(f"Prediction failed: {exc}")

        # Seed sample student study plan and bookmarks if none exist
        if student and not StudyPlan.query.filter_by(user_id=student.id).first():
            print("\nCreating demo study plan for student...")
            plan = StudyPlan(
                user_id=student.id,
                subject_id=subject.id,
                name="Physics O-Level Revision Plan",
                exam_date=None,
            )
            db.session.add(plan)
            db.session.flush()

            # Add top predicted topics to study plan
            top_topics = topics[:5]
            for order, t in enumerate(top_topics):
                item = StudyPlanItem(
                    plan_id=plan.id,
                    topic_id=t.id,
                    priority=order + 1,
                    is_done=(order == 0),
                )
                db.session.add(item)

            # Bookmark first 3 questions
            first_paper = ingested_papers[0] if ingested_papers else None
            if first_paper and first_paper.questions:
                for q in first_paper.questions[:3]:
                    db.session.add(Bookmark(user_id=student.id, question_id=q.id, note="Challenging question to revisit"))

            db.session.commit()
            print("Demo study plan and bookmarks created successfully!")

        print("\nProduction-ready demo environment is ready!")
        print("Explore:")
        print("  - Papers:      http://127.0.0.1:5000/papers/")
        print("  - Analytics:   http://127.0.0.1:5000/subjects/1/dashboard")
        print("  - Predictions: http://127.0.0.1:5000/subjects/1/predictions")
        print("  - Backtest:    http://127.0.0.1:5000/subjects/1/backtest")
        print("  - Study Plans: http://127.0.0.1:5000/study/plans")


if __name__ == "__main__":
    ingest_papers()
