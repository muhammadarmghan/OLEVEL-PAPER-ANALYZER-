from flask import Blueprint, flash, g, redirect, render_template, request, url_for

from ..auth_utils import role_required
from ..extensions import db
from ..forms.review import ReviewForm
from ..models import AuditLog, Question, QuestionTopic
from ..models.base import utcnow
from ..services.topic_model import current_topics

bp = Blueprint("review", __name__, url_prefix="/review")


@bp.route("/")
@role_required("contributor", "admin")
def queue():
    page = request.args.get("page", 1, type=int)
    stmt = db.select(Question).where(Question.review_status == "pending").order_by(Question.id)
    return render_template("review/list.html", pagination=db.paginate(stmt, page=page, per_page=20, error_out=False))


@bp.route("/<int:question_id>", methods=["GET", "POST"])
@role_required("contributor", "admin")
def detail(question_id):
    question = db.get_or_404(Question, question_id)
    topics = current_topics(question.paper.variant.component.subject)
    form = ReviewForm(obj=question)
    form.topic_id.choices = [(t.id, f"{t.code} {t.title}") for t in topics]
    if request.method == "GET" and question.topic_links:
        form.topic_id.data = question.topic_links[0].topic_id
    if form.validate_on_submit():
        question.text, question.marks = form.text.data, form.marks.data
        if form.approve.data:
            for link in list(question.topic_links):
                db.session.delete(link)
            db.session.flush()
            db.session.add(QuestionTopic(question_id=question.id, topic_id=form.topic_id.data, confidence=1.0,
                                         assigned_by="human", reviewed_by=g.user.id))
            question.review_status = "approved"
        else:
            question.review_status = "rejected"
        db.session.add(AuditLog(user_id=g.user.id, action="review", entity_type="questions",
                                entity_id=question.id, details={"result": question.review_status, "at": utcnow().isoformat()}))
        db.session.commit()
        flash(f"Question {question.number} {question.review_status}.", "success")
        return redirect(url_for("review.queue"))  # Post-Redirect-Get
    return render_template("review/detail.html", question=question, form=form)
