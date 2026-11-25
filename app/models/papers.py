"""Papers and ingestion: 8 tables."""
from ..extensions import db
from .base import TimestampMixin, utcnow


class UploadBatch(TimestampMixin, db.Model):
    __tablename__ = "upload_batches"

    id = db.Column(db.Integer, primary_key=True)
    uploaded_by = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    note = db.Column(db.String(255))
    status = db.Column(db.String(20), default="open", nullable=False)

    papers = db.relationship("Paper", backref="batch")
    uploader = db.relationship("User", backref="upload_batches")


class Paper(TimestampMixin, db.Model):
    """One question paper: a paper variant sat in one exam session."""

    __tablename__ = "papers"
    __table_args__ = (db.UniqueConstraint("session_id", "variant_id", name="uq_paper_session_variant"),)

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey("exam_sessions.id", ondelete="CASCADE"), nullable=False)
    variant_id = db.Column(db.Integer, db.ForeignKey("paper_variants.id", ondelete="CASCADE"), nullable=False)
    batch_id = db.Column(db.Integer, db.ForeignKey("upload_batches.id", ondelete="SET NULL"))
    uploaded_by = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    total_marks = db.Column(db.Integer)
    status = db.Column(db.String(20), default="uploaded", nullable=False)

    files = db.relationship("PaperFile", backref="paper", cascade="all, delete-orphan")
    sections = db.relationship("PaperSection", backref="paper", cascade="all, delete-orphan")
    extraction_runs = db.relationship("ExtractionRun", backref="paper", cascade="all, delete-orphan")
    reviews = db.relationship("PaperReview", backref="paper", cascade="all, delete-orphan")
    questions = db.relationship("Question", backref="paper", cascade="all, delete-orphan")
    mark_scheme = db.relationship("MarkScheme", uselist=False, backref="paper", cascade="all, delete-orphan")
    uploader = db.relationship("User", backref="uploaded_papers")


class PaperFile(TimestampMixin, db.Model):
    __tablename__ = "paper_files"
    __table_args__ = (
        db.CheckConstraint("doc_type IN ('qp','ms','er')", name="doc_type_valid"),
    )

    id = db.Column(db.Integer, primary_key=True)
    paper_id = db.Column(db.Integer, db.ForeignKey("papers.id", ondelete="CASCADE"), nullable=False)
    doc_type = db.Column(db.String(2), nullable=False)  # qp / ms / er
    original_filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), nullable=False)
    sha256 = db.Column(db.String(64), unique=True, nullable=False)
    size_bytes = db.Column(db.Integer)
    page_count = db.Column(db.Integer)

    pages = db.relationship("PaperPage", backref="file", cascade="all, delete-orphan")


class PaperPage(TimestampMixin, db.Model):
    __tablename__ = "paper_pages"
    __table_args__ = (db.UniqueConstraint("file_id", "page_number", name="uq_page_file_number"),)

    id = db.Column(db.Integer, primary_key=True)
    file_id = db.Column(db.Integer, db.ForeignKey("paper_files.id", ondelete="CASCADE"), nullable=False)
    page_number = db.Column(db.Integer, nullable=False)
    text = db.Column(db.Text)
    image_path = db.Column(db.String(255))
    ocr_confidence = db.Column(db.Float)


class PaperSection(TimestampMixin, db.Model):
    __tablename__ = "paper_sections"

    id = db.Column(db.Integer, primary_key=True)
    paper_id = db.Column(db.Integer, db.ForeignKey("papers.id", ondelete="CASCADE"), nullable=False)
    label = db.Column(db.String(20), nullable=False)
    title = db.Column(db.String(120))
    marks = db.Column(db.Integer)
    start_page = db.Column(db.Integer)
    end_page = db.Column(db.Integer)

    questions = db.relationship("Question", backref="section")


class ExtractionRun(db.Model):
    __tablename__ = "extraction_runs"

    id = db.Column(db.Integer, primary_key=True)
    paper_id = db.Column(db.Integer, db.ForeignKey("papers.id", ondelete="CASCADE"), nullable=False)
    status = db.Column(db.String(20), default="queued", nullable=False)  # queued/running/done/failed
    method = db.Column(db.String(30))  # text_layer / ocr
    started_at = db.Column(db.DateTime)
    finished_at = db.Column(db.DateTime)
    questions_found = db.Column(db.Integer, default=0)
    error_message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    questions = db.relationship("Question", backref="extraction_run")


class PaperReview(db.Model):
    __tablename__ = "paper_reviews"

    id = db.Column(db.Integer, primary_key=True)
    paper_id = db.Column(db.Integer, db.ForeignKey("papers.id", ondelete="CASCADE"), nullable=False)
    reviewer_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    status = db.Column(db.String(20), default="pending", nullable=False)  # pending/approved/rejected
    comments = db.Column(db.Text)
    reviewed_at = db.Column(db.DateTime)

    reviewer = db.relationship("User", backref="paper_reviews")


class MarkScheme(TimestampMixin, db.Model):
    __tablename__ = "mark_schemes"

    id = db.Column(db.Integer, primary_key=True)
    paper_id = db.Column(
        db.Integer, db.ForeignKey("papers.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    file_id = db.Column(db.Integer, db.ForeignKey("paper_files.id", ondelete="SET NULL"))
    parsed_at = db.Column(db.DateTime)
    notes = db.Column(db.Text)

    file = db.relationship("PaperFile")
