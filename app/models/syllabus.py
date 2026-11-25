"""Syllabus content: 5 tables."""
from ..extensions import db
from .base import TimestampMixin


class Unit(TimestampMixin, db.Model):
    __tablename__ = "units"
    __table_args__ = (db.UniqueConstraint("syllabus_version_id", "number", name="uq_unit_version_number"),)

    id = db.Column(db.Integer, primary_key=True)
    syllabus_version_id = db.Column(
        db.Integer, db.ForeignKey("syllabus_versions.id", ondelete="CASCADE"), nullable=False
    )
    number = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(150), nullable=False)

    topics = db.relationship("Topic", backref="unit", cascade="all, delete-orphan")


class Topic(TimestampMixin, db.Model):
    __tablename__ = "topics"
    __table_args__ = (db.UniqueConstraint("unit_id", "code", name="uq_topic_unit_code"),)

    id = db.Column(db.Integer, primary_key=True)
    unit_id = db.Column(db.Integer, db.ForeignKey("units.id", ondelete="CASCADE"), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey("topics.id", ondelete="SET NULL"))
    code = db.Column(db.String(20), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    display_order = db.Column(db.Integer, default=0, nullable=False)

    children = db.relationship("Topic", backref=db.backref("parent", remote_side="Topic.id"))
    keywords = db.relationship("TopicKeyword", backref="topic", cascade="all, delete-orphan")
    objectives = db.relationship("LearningObjective", backref="topic", cascade="all, delete-orphan")


class TopicKeyword(TimestampMixin, db.Model):
    __tablename__ = "topic_keywords"
    __table_args__ = (db.UniqueConstraint("topic_id", "keyword", name="uq_keyword_topic_keyword"),)

    id = db.Column(db.Integer, primary_key=True)
    topic_id = db.Column(db.Integer, db.ForeignKey("topics.id", ondelete="CASCADE"), nullable=False)
    keyword = db.Column(db.String(80), nullable=False)
    weight = db.Column(db.Float, default=1.0, nullable=False)


class TopicPrerequisite(db.Model):
    """Self-referential many-to-many: which topics should be learned first."""

    __tablename__ = "topic_prerequisites"
    __table_args__ = (db.CheckConstraint("topic_id <> prerequisite_id", name="not_self"),)

    topic_id = db.Column(db.Integer, db.ForeignKey("topics.id", ondelete="CASCADE"), primary_key=True)
    prerequisite_id = db.Column(db.Integer, db.ForeignKey("topics.id", ondelete="CASCADE"), primary_key=True)

    topic = db.relationship(
        "Topic", foreign_keys=[topic_id], backref=db.backref("prerequisite_links", cascade="all, delete-orphan")
    )
    prerequisite = db.relationship("Topic", foreign_keys=[prerequisite_id])


class LearningObjective(TimestampMixin, db.Model):
    __tablename__ = "learning_objectives"
    __table_args__ = (db.UniqueConstraint("topic_id", "code", name="uq_objective_topic_code"),)

    id = db.Column(db.Integer, primary_key=True)
    topic_id = db.Column(db.Integer, db.ForeignKey("topics.id", ondelete="CASCADE"), nullable=False)
    code = db.Column(db.String(20), nullable=False)
    text = db.Column(db.Text, nullable=False)
