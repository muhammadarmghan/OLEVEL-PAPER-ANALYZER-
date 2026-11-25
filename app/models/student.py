"""Student features: 5 tables."""
from ..extensions import db
from .base import TimestampMixin, utcnow


class StudyPlan(TimestampMixin, db.Model):
    __tablename__ = "study_plans"
    __table_args__ = (db.UniqueConstraint("user_id", "name", name="uq_plan_user_name"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    exam_date = db.Column(db.Date)

    user = db.relationship("User", backref="study_plans")
    subject = db.relationship("Subject", backref="study_plans")
    items = db.relationship("StudyPlanItem", backref="plan", cascade="all, delete-orphan")


class StudyPlanItem(TimestampMixin, db.Model):
    __tablename__ = "study_plan_items"
    __table_args__ = (db.UniqueConstraint("plan_id", "topic_id", name="uq_item_plan_topic"),)

    id = db.Column(db.Integer, primary_key=True)
    plan_id = db.Column(db.Integer, db.ForeignKey("study_plans.id", ondelete="CASCADE"), nullable=False)
    topic_id = db.Column(db.Integer, db.ForeignKey("topics.id", ondelete="CASCADE"), nullable=False)
    planned_date = db.Column(db.Date)
    priority = db.Column(db.Integer, default=3, nullable=False)
    is_done = db.Column(db.Boolean, default=False, nullable=False)

    topic = db.relationship("Topic", backref=db.backref("plan_items", cascade="all, delete-orphan"))


class Bookmark(TimestampMixin, db.Model):
    __tablename__ = "bookmarks"
    __table_args__ = (db.UniqueConstraint("user_id", "question_id", name="uq_bookmark_user_question"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey("questions.id", ondelete="CASCADE"), nullable=False)
    note = db.Column(db.String(255))

    user = db.relationship("User", backref="bookmarks")
    question = db.relationship("Question", backref=db.backref("bookmarks", cascade="all, delete-orphan"))


class PredictionFeedback(TimestampMixin, db.Model):
    __tablename__ = "prediction_feedback"
    __table_args__ = (
        db.UniqueConstraint("prediction_id", "user_id", name="uq_feedback_prediction_user"),
        db.CheckConstraint("rating BETWEEN 1 AND 5", name="rating_range"),
    )

    id = db.Column(db.Integer, primary_key=True)
    prediction_id = db.Column(db.Integer, db.ForeignKey("predictions.id", ondelete="CASCADE"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.String(255))

    user = db.relationship("User", backref="prediction_feedback")


class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    message = db.Column(db.String(255), nullable=False)
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    user = db.relationship("User", backref="notifications")
