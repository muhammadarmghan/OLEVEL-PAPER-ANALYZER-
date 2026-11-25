"""Analytics and prediction: 5 tables."""
from ..extensions import db
from .base import utcnow


class TopicStat(db.Model):
    __tablename__ = "topic_stats"
    __table_args__ = (db.UniqueConstraint("topic_id", "exam_year", name="uq_stat_topic_year"),)

    id = db.Column(db.Integer, primary_key=True)
    topic_id = db.Column(db.Integer, db.ForeignKey("topics.id", ondelete="CASCADE"), nullable=False)
    exam_year = db.Column(db.Integer, nullable=False)
    appearances = db.Column(db.Integer, default=0, nullable=False)
    total_marks = db.Column(db.Integer, default=0, nullable=False)
    mark_share = db.Column(db.Float, default=0.0, nullable=False)
    sessions_since_last = db.Column(db.Integer)
    computed_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    topic = db.relationship("Topic", backref=db.backref("stats", cascade="all, delete-orphan"))


class PredictionRun(db.Model):
    __tablename__ = "prediction_runs"

    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    algorithm_version = db.Column(db.String(20), nullable=False, default="v1")
    weights = db.Column(db.JSON)  # {"recency": 0.4, "marks": 0.3, ...}
    trained_through_year = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    subject = db.relationship("Subject", backref="prediction_runs")
    creator = db.relationship("User", backref="prediction_runs")
    predictions = db.relationship("Prediction", backref="run", cascade="all, delete-orphan")
    backtests = db.relationship("BacktestResult", backref="run", cascade="all, delete-orphan")


class Prediction(db.Model):
    __tablename__ = "predictions"
    __table_args__ = (
        db.UniqueConstraint("run_id", "topic_id", name="uq_prediction_run_topic"),
        db.CheckConstraint("tier IN ('very_likely','likely','lower')", name="tier_valid"),
    )

    id = db.Column(db.Integer, primary_key=True)
    run_id = db.Column(db.Integer, db.ForeignKey("prediction_runs.id", ondelete="CASCADE"), nullable=False)
    topic_id = db.Column(db.Integer, db.ForeignKey("topics.id", ondelete="CASCADE"), nullable=False)
    score = db.Column(db.Float, nullable=False)
    rank = db.Column(db.Integer, nullable=False)
    tier = db.Column(db.String(12), nullable=False)

    topic = db.relationship("Topic", backref=db.backref("predictions", cascade="all, delete-orphan"))
    reasons = db.relationship("PredictionReason", backref="prediction", cascade="all, delete-orphan")
    feedback = db.relationship("PredictionFeedback", backref="prediction", cascade="all, delete-orphan")


class PredictionReason(db.Model):
    __tablename__ = "prediction_reasons"

    id = db.Column(db.Integer, primary_key=True)
    prediction_id = db.Column(db.Integer, db.ForeignKey("predictions.id", ondelete="CASCADE"), nullable=False)
    signal = db.Column(db.String(40), nullable=False)  # recency_frequency, mark_weight, overdue, ...
    value = db.Column(db.Float, nullable=False)
    explanation = db.Column(db.String(255), nullable=False)


class BacktestResult(db.Model):
    __tablename__ = "backtest_results"

    id = db.Column(db.Integer, primary_key=True)
    run_id = db.Column(db.Integer, db.ForeignKey("prediction_runs.id", ondelete="CASCADE"), nullable=False)
    target_session_id = db.Column(db.Integer, db.ForeignKey("exam_sessions.id", ondelete="CASCADE"), nullable=False)
    k = db.Column(db.Integer, nullable=False)
    hit_rate = db.Column(db.Float, nullable=False)
    mark_coverage = db.Column(db.Float)
    baseline_hit_rate = db.Column(db.Float)

    target_session = db.relationship("ExamSession", backref="backtests")
