from flask import Blueprint, flash, g, redirect, render_template, url_for

from ..auth_utils import login_required, role_required
from ..extensions import db
from ..forms.study import FeedbackForm
from ..models import (Paper, PaperComponent, PaperVariant, Prediction, PredictionFeedback, PredictionRun,
                      Question, Subject)
from ..services.aggregation import build_history
from ..services.predictions import run_prediction
from ..services.topic_model import current_topics

bp = Blueprint("analytics", __name__)


@bp.route("/analysis")
def hub():
    subjects = Subject.query.order_by(Subject.name).all()
    # Default to first subject if available
    default_sub = subjects[0] if subjects else None
    return redirect(url_for('analytics.dashboard', subject_id=default_sub.id)) if default_sub else render_template("analytics/hub.html", subjects=subjects)


def latest_run(subject_id):

    return PredictionRun.query.filter_by(subject_id=subject_id).order_by(PredictionRun.id.desc()).first()


@bp.route("/subjects/<int:subject_id>/dashboard")
def dashboard(subject_id):
    subject = db.get_or_404(Subject, subject_id)
    history = build_history(subject_id)
    topics = current_topics(subject)
    rows = [{"label": f"{t.code} {t.title}", "cells": list(zip(history.appeared[t.id], history.marks[t.id])),
             "total": sum(history.marks[t.id])} for t in topics]
    pending = (Question.query.join(Paper).join(PaperVariant).join(PaperComponent)
               .filter(PaperComponent.subject_id == subject_id, Question.review_status == "pending").count())
    return render_template("analytics/dashboard.html", subject=subject, history=history, rows=rows, pending=pending)


@bp.route("/subjects/<int:subject_id>/predict", methods=["POST"])
@role_required("contributor", "admin")
def predict(subject_id):
    db.get_or_404(Subject, subject_id)
    try:
        run_prediction(subject_id, user_id=g.user.id)
    except ValueError as exc:
        flash(str(exc), "danger")
        return redirect(url_for("analytics.dashboard", subject_id=subject_id))
    flash("New prediction generated.", "success")
    return redirect(url_for("analytics.predictions", subject_id=subject_id))  # Post-Redirect-Get


@bp.route("/subjects/<int:subject_id>/predictions")
def predictions(subject_id):
    subject = db.get_or_404(Subject, subject_id)
    run = latest_run(subject_id)
    items = sorted(run.predictions, key=lambda p: p.rank) if run else []
    return render_template("analytics/predictions.html", subject=subject, run=run, items=items)


@bp.route("/subjects/<int:subject_id>/backtest")
def backtest(subject_id):
    subject = db.get_or_404(Subject, subject_id)
    run = latest_run(subject_id)
    rows = sorted(run.backtests, key=lambda b: b.target_session.year * 10 + "msw".index(b.target_session.series_code)) if run else []
    n = len(rows) or 1
    avg = {k: sum(getattr(r, k) or 0 for r in rows) / n for k in ("hit_rate", "baseline_hit_rate", "mark_coverage")}
    return render_template("analytics/backtest.html", subject=subject, run=run, rows=rows, avg=avg)


@bp.route("/predictions/<int:prediction_id>/feedback", methods=["POST"])
@login_required
def feedback(prediction_id):
    prediction = db.get_or_404(Prediction, prediction_id)
    form = FeedbackForm()
    if form.validate_on_submit():
        row = PredictionFeedback.query.filter_by(prediction_id=prediction.id, user_id=g.user.id).first() \
            or PredictionFeedback(prediction_id=prediction.id, user_id=g.user.id)
        row.rating, row.comment = form.rating.data, form.comment.data
        db.session.add(row)
        db.session.commit()
        flash("Thanks for your feedback.", "success")
    else:
        flash("Rating must be between 1 and 5.", "danger")
    return redirect(url_for("analytics.predictions", subject_id=prediction.run.subject_id))
