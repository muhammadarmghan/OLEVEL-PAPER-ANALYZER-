"""Exam framework: 8 tables (board > qualification > subject > components/variants)."""
from ..extensions import db
from .base import TimestampMixin

SERIES_LABELS = {"m": "Feb/Mar", "s": "May/Jun", "w": "Oct/Nov"}


class ExamBoard(TimestampMixin, db.Model):
    __tablename__ = "exam_boards"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    short_code = db.Column(db.String(20), unique=True, nullable=False)
    website = db.Column(db.String(255))

    qualifications = db.relationship("Qualification", backref="board", cascade="all, delete-orphan")
    sessions = db.relationship("ExamSession", backref="board", cascade="all, delete-orphan")


class Qualification(TimestampMixin, db.Model):
    __tablename__ = "qualifications"
    __table_args__ = (db.UniqueConstraint("board_id", "name", name="uq_qualification_board_name"),)

    id = db.Column(db.Integer, primary_key=True)
    board_id = db.Column(db.Integer, db.ForeignKey("exam_boards.id", ondelete="CASCADE"), nullable=False)
    name = db.Column(db.String(80), nullable=False)  # e.g. "O Level"

    subjects = db.relationship("Subject", backref="qualification", cascade="all, delete-orphan")


class Subject(TimestampMixin, db.Model):
    __tablename__ = "subjects"
    __table_args__ = (db.UniqueConstraint("qualification_id", "code", name="uq_subject_qualification_code"),)

    id = db.Column(db.Integer, primary_key=True)
    qualification_id = db.Column(
        db.Integer, db.ForeignKey("qualifications.id", ondelete="CASCADE"), nullable=False
    )
    code = db.Column(db.String(10), nullable=False)  # syllabus code, e.g. "5054"
    name = db.Column(db.String(120), nullable=False)

    syllabus_versions = db.relationship("SyllabusVersion", backref="subject", cascade="all, delete-orphan")
    components = db.relationship("PaperComponent", backref="subject", cascade="all, delete-orphan")
    grade_thresholds = db.relationship("GradeThreshold", backref="subject", cascade="all, delete-orphan")


class SyllabusVersion(TimestampMixin, db.Model):
    __tablename__ = "syllabus_versions"
    __table_args__ = (db.UniqueConstraint("subject_id", "version_label", name="uq_syllabus_subject_label"),)

    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)
    version_label = db.Column(db.String(40), nullable=False)  # e.g. "2023-2025"
    valid_from_year = db.Column(db.Integer, nullable=False)
    valid_to_year = db.Column(db.Integer)
    is_current = db.Column(db.Boolean, default=False, nullable=False)

    units = db.relationship("Unit", backref="syllabus_version", cascade="all, delete-orphan")


class ExamSession(TimestampMixin, db.Model):
    __tablename__ = "exam_sessions"
    __table_args__ = (
        db.UniqueConstraint("board_id", "year", "series_code", name="uq_session_board_year_series"),
        db.CheckConstraint("series_code IN ('m','s','w')", name="series_code_valid"),
    )

    id = db.Column(db.Integer, primary_key=True)
    board_id = db.Column(db.Integer, db.ForeignKey("exam_boards.id", ondelete="CASCADE"), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    series_code = db.Column(db.String(1), nullable=False)  # m / s / w

    papers = db.relationship("Paper", backref="session")
    grade_thresholds = db.relationship("GradeThreshold", backref="session")

    @property
    def label(self) -> str:
        return f"{SERIES_LABELS[self.series_code]} {self.year}"


class PaperComponent(TimestampMixin, db.Model):
    """A paper number within a subject, e.g. Paper 1 (multiple choice)."""

    __tablename__ = "paper_components"
    __table_args__ = (db.UniqueConstraint("subject_id", "paper_number", name="uq_component_subject_number"),)

    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)
    paper_number = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String(80))
    question_style = db.Column(db.String(20), nullable=False, default="mcq")  # mcq / structured / essay
    total_marks = db.Column(db.Integer)
    duration_minutes = db.Column(db.Integer)

    variants = db.relationship("PaperVariant", backref="component", cascade="all, delete-orphan")


class PaperVariant(TimestampMixin, db.Model):
    __tablename__ = "paper_variants"
    __table_args__ = (db.UniqueConstraint("component_id", "variant_number", name="uq_variant_component_number"),)

    id = db.Column(db.Integer, primary_key=True)
    component_id = db.Column(
        db.Integer, db.ForeignKey("paper_components.id", ondelete="CASCADE"), nullable=False
    )
    variant_number = db.Column(db.Integer, nullable=False)

    papers = db.relationship("Paper", backref="variant")


class GradeThreshold(TimestampMixin, db.Model):
    __tablename__ = "grade_thresholds"
    __table_args__ = (
        db.UniqueConstraint("subject_id", "session_id", "grade", name="uq_threshold_subject_session_grade"),
    )

    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)
    session_id = db.Column(db.Integer, db.ForeignKey("exam_sessions.id", ondelete="CASCADE"), nullable=False)
    grade = db.Column(db.String(2), nullable=False)  # A*, A, B, ...
    min_marks = db.Column(db.Integer, nullable=False)
