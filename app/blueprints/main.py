from flask import Blueprint, render_template
from sqlalchemy import func, select

from ..extensions import db
from ..models import Paper, Question, Subject, Topic

bp = Blueprint("main", __name__)


@bp.route("/")
def index():
    counts = {
        "Subjects": db.session.scalar(select(func.count(Subject.id))),
        "Topics": db.session.scalar(select(func.count(Topic.id))),
        "Papers": db.session.scalar(select(func.count(Paper.id))),
        "Questions": db.session.scalar(select(func.count(Question.id))),
    }
    subjects = Subject.query.order_by(Subject.name).all()
    recent_papers = Paper.query.order_by(Paper.id.desc()).limit(6).all()
    return render_template("main/index.html", counts=counts, subjects=subjects, recent_papers=recent_papers)


@bp.route("/subjects")
def subjects():
    items = Subject.query.order_by(Subject.name).all()
    return render_template("main/subjects.html", subjects=items)


@bp.route("/subjects/<int:subject_id>")
def subject_detail(subject_id):
    subject = db.get_or_404(Subject, subject_id)
    versions = sorted(subject.syllabus_versions, key=lambda v: (v.is_current, v.valid_from_year), reverse=True)
    units = versions[0].units if versions else []
    return render_template("main/subject_detail.html", subject=subject, units=units)


@bp.route("/about")
def about():
    return render_template("main/about.html")

