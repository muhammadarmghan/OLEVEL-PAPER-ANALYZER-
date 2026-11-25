from datetime import date

from flask import Blueprint, abort, flash, g, redirect, render_template, url_for
from sqlalchemy.exc import IntegrityError

from ..auth_utils import login_required
from ..extensions import db
from ..forms.study import PlanForm
from ..models import Bookmark, Question, StudyPlan, StudyPlanItem, Subject
from ..services.study_plan import schedule_topics
from .analytics import latest_run

bp = Blueprint("study", __name__, url_prefix="/study")


def _own_plan(plan_id):
    plan = db.get_or_404(StudyPlan, plan_id)
    if plan.user_id != g.user.id and not g.user.has_role("admin"):
        abort(404)
    return plan


@bp.route("/plans")
@login_required
def plans():
    items = StudyPlan.query.filter_by(user_id=g.user.id).order_by(StudyPlan.exam_date).all()
    return render_template("study/plans.html", plans=items)


@bp.route("/plans/new", methods=["GET", "POST"])
@login_required
def new_plan():
    form = PlanForm()
    form.subject_id.choices = [(s.id, s.name) for s in Subject.query.order_by(Subject.name)]
    if form.validate_on_submit():
        run = latest_run(form.subject_id.data)
        if run is None:
            flash("No prediction exists for this subject yet.", "danger")
            return render_template("study/plan_form.html", form=form, title="New study plan")
        top = sorted(run.predictions, key=lambda p: p.rank)[: form.top_n.data]
        plan = StudyPlan(user_id=g.user.id, subject_id=form.subject_id.data, name=form.name.data.strip(),
                         exam_date=form.exam_date.data)
        for i, (topic_id, day) in enumerate(schedule_topics([p.topic_id for p in top], date.today(), plan.exam_date), 1):
            plan.items.append(StudyPlanItem(topic_id=topic_id, planned_date=day, priority=i))
        db.session.add(plan)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("You already have a plan with that name.", "danger")
        else:
            flash("Study plan created.", "success")
            return redirect(url_for("study.plan_detail", plan_id=plan.id))  # Post-Redirect-Get
    return render_template("study/plan_form.html", form=form, title="New study plan")


@bp.route("/plans/<int:plan_id>")
@login_required
def plan_detail(plan_id):
    plan = _own_plan(plan_id)
    return render_template("study/plan_detail.html", plan=plan, items=sorted(plan.items, key=lambda i: i.priority))


@bp.route("/plans/<int:plan_id>/edit", methods=["GET", "POST"])
@login_required
def edit_plan(plan_id):
    plan = _own_plan(plan_id)
    form = PlanForm(obj=plan)
    del form.subject_id, form.top_n
    if form.validate_on_submit():
        plan.name, plan.exam_date = form.name.data.strip(), form.exam_date.data
        ordered = sorted(plan.items, key=lambda i: i.priority)
        for item, (_, day) in zip(ordered, schedule_topics([i.topic_id for i in ordered], date.today(), plan.exam_date)):
            item.planned_date = day
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("You already have a plan with that name.", "danger")
        else:
            flash("Study plan updated and rescheduled.", "success")
            return redirect(url_for("study.plan_detail", plan_id=plan.id))
    return render_template("study/plan_form.html", form=form, title="Edit study plan")


@bp.route("/plans/<int:plan_id>/delete", methods=["POST"])
@login_required
def delete_plan(plan_id):
    db.session.delete(_own_plan(plan_id))
    db.session.commit()
    flash("Study plan deleted.", "info")
    return redirect(url_for("study.plans"))


@bp.route("/items/<int:item_id>/toggle", methods=["POST"])
@login_required
def toggle_item(item_id):
    item = db.get_or_404(StudyPlanItem, item_id)
    _own_plan(item.plan_id)
    item.is_done = not item.is_done
    db.session.commit()
    return redirect(url_for("study.plan_detail", plan_id=item.plan_id))


@bp.route("/bookmarks")
@login_required
def bookmarks():
    rows = Bookmark.query.filter_by(user_id=g.user.id).order_by(Bookmark.id.desc()).all()
    return render_template("study/bookmarks.html", bookmarks=rows)


@bp.route("/bookmarks/<int:question_id>", methods=["POST"])
@login_required
def toggle_bookmark(question_id):
    question = db.get_or_404(Question, question_id)
    existing = Bookmark.query.filter_by(user_id=g.user.id, question_id=question.id).first()
    if existing:
        db.session.delete(existing)
        flash("Bookmark removed.", "info")
    else:
        db.session.add(Bookmark(user_id=g.user.id, question_id=question.id))
        flash("Question bookmarked.", "success")
    db.session.commit()
    return redirect(url_for("papers.detail", paper_id=question.paper_id))
