"""Questions: 9 model tables + 1 association table."""
from ..extensions import db
from .base import TimestampMixin, utcnow

# Plain association table (many-to-many, no extra columns).
question_command_words = db.Table(
    "question_command_words",
    db.Column("question_id", db.Integer, db.ForeignKey("questions.id", ondelete="CASCADE"), primary_key=True),
    db.Column("command_word_id", db.Integer, db.ForeignKey("command_words.id", ondelete="CASCADE"), primary_key=True),
)


class QuestionType(TimestampMixin, db.Model):
    __tablename__ = "question_types"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)  # mcq / structured / essay / numerical
    name = db.Column(db.String(60), nullable=False)

    questions = db.relationship("Question", backref="question_type")


class CommandWord(TimestampMixin, db.Model):
    __tablename__ = "command_words"

    id = db.Column(db.Integer, primary_key=True)
    word = db.Column(db.String(40), unique=True, nullable=False)  # describe, explain, calculate...
    meaning = db.Column(db.String(255))


class Question(TimestampMixin, db.Model):
    __tablename__ = "questions"
    __table_args__ = (
        db.UniqueConstraint("paper_id", "number", name="uq_question_paper_number"),
        db.CheckConstraint("marks IS NULL OR marks >= 0", name="marks_non_negative"),
    )

    id = db.Column(db.Integer, primary_key=True)
    paper_id = db.Column(db.Integer, db.ForeignKey("papers.id", ondelete="CASCADE"), nullable=False)
    section_id = db.Column(db.Integer, db.ForeignKey("paper_sections.id", ondelete="SET NULL"))
    question_type_id = db.Column(db.Integer, db.ForeignKey("question_types.id"), nullable=False)
    extraction_run_id = db.Column(db.Integer, db.ForeignKey("extraction_runs.id", ondelete="SET NULL"))
    number = db.Column(db.Integer, nullable=False)
    text = db.Column(db.Text, nullable=False)
    marks = db.Column(db.Integer)
    page_number = db.Column(db.Integer)
    image_path = db.Column(db.String(255))
    review_status = db.Column(db.String(20), default="pending", nullable=False)

    parts = db.relationship("QuestionPart", backref="question", cascade="all, delete-orphan")
    options = db.relationship("QuestionOption", backref="question", cascade="all, delete-orphan")
    answer = db.relationship("QuestionAnswer", uselist=False, backref="question", cascade="all, delete-orphan")
    command_words = db.relationship("CommandWord", secondary=question_command_words, backref="questions")
    flags = db.relationship("QuestionFlag", backref="question", cascade="all, delete-orphan")


class QuestionPart(TimestampMixin, db.Model):
    __tablename__ = "question_parts"
    __table_args__ = (db.UniqueConstraint("question_id", "label", name="uq_part_question_label"),)

    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey("questions.id", ondelete="CASCADE"), nullable=False)
    label = db.Column(db.String(10), nullable=False)  # (a), (i), ...
    text = db.Column(db.Text, nullable=False)
    marks = db.Column(db.Integer)
    display_order = db.Column(db.Integer, default=0, nullable=False)


class QuestionOption(TimestampMixin, db.Model):
    __tablename__ = "question_options"
    __table_args__ = (db.UniqueConstraint("question_id", "label", name="uq_option_question_label"),)

    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey("questions.id", ondelete="CASCADE"), nullable=False)
    label = db.Column(db.String(2), nullable=False)  # A-D
    text = db.Column(db.Text, nullable=False)
    is_correct = db.Column(db.Boolean, default=False, nullable=False)


class QuestionAnswer(TimestampMixin, db.Model):
    __tablename__ = "question_answers"

    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(
        db.Integer, db.ForeignKey("questions.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    answer_text = db.Column(db.Text)
    marking_points = db.Column(db.Text)
    marks = db.Column(db.Integer)


class QuestionTopic(db.Model):
    """Question <-> topic mapping with a confidence score (association object)."""

    __tablename__ = "question_topics"
    __table_args__ = (
        db.CheckConstraint("confidence >= 0 AND confidence <= 1", name="confidence_range"),
        db.CheckConstraint("assigned_by IN ('rule','model','human')", name="assigned_by_valid"),
    )

    question_id = db.Column(db.Integer, db.ForeignKey("questions.id", ondelete="CASCADE"), primary_key=True)
    topic_id = db.Column(db.Integer, db.ForeignKey("topics.id", ondelete="CASCADE"), primary_key=True)
    confidence = db.Column(db.Float, default=1.0, nullable=False)
    assigned_by = db.Column(db.String(10), default="rule", nullable=False)
    reviewed_by = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    question = db.relationship("Question", backref=db.backref("topic_links", cascade="all, delete-orphan"))
    topic = db.relationship("Topic", backref=db.backref("question_links", cascade="all, delete-orphan"))
    reviewer = db.relationship("User")


class QuestionSimilarity(db.Model):
    __tablename__ = "question_similarity"
    __table_args__ = (
        db.UniqueConstraint("question_id", "similar_question_id", name="uq_similarity_pair"),
        db.CheckConstraint("question_id < similar_question_id", name="ordered_pair"),
    )

    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey("questions.id", ondelete="CASCADE"), nullable=False)
    similar_question_id = db.Column(db.Integer, db.ForeignKey("questions.id", ondelete="CASCADE"), nullable=False)
    score = db.Column(db.Float, nullable=False)
    method = db.Column(db.String(30), default="tfidf", nullable=False)

    question = db.relationship(
        "Question", foreign_keys=[question_id], backref=db.backref("similarity_links", cascade="all, delete-orphan")
    )
    similar_question = db.relationship("Question", foreign_keys=[similar_question_id])


class QuestionFlag(db.Model):
    __tablename__ = "question_flags"

    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey("questions.id", ondelete="CASCADE"), nullable=False)
    flagged_by = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    reason = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(20), default="open", nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    flagged_by_user = db.relationship("User", backref="question_flags")
