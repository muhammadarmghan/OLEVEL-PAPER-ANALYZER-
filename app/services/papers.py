"""Helpers shared by the upload form and the papers blueprint."""
import hashlib
import os

from flask import current_app
from werkzeug.utils import secure_filename

from ..extensions import db
from ..models import ExamSession, Paper, PaperFile, PaperComponent, PaperVariant, Subject, UploadBatch


def resolve_target(parsed):
    """Find the subject and paper component a parsed file name refers to, or raise ValueError."""
    subject = Subject.query.filter_by(code=parsed.subject_code).first()
    if subject is None:
        raise ValueError(f"Unknown subject code {parsed.subject_code}. Add the subject in the admin area first.")
    component = PaperComponent.query.filter_by(subject_id=subject.id, paper_number=parsed.paper_number).first()
    if component is None:
        raise ValueError(f"{subject.name} has no Paper {parsed.paper_number} defined.")
    return subject, component


def existing_paper(parsed):
    subject, component = resolve_target(parsed)
    variant = PaperVariant.query.filter_by(component_id=component.id, variant_number=parsed.variant_number).first()
    session = ExamSession.query.filter_by(board_id=subject.qualification.board_id, year=parsed.year,
                                          series_code=parsed.series_code).first()
    if variant and session:
        return Paper.query.filter_by(variant_id=variant.id, session_id=session.id).first()
    return None


def _get_or_create(model, **kw):
    obj = model.query.filter_by(**kw).first()
    if obj is None:
        obj = model(**kw)
        db.session.add(obj)
        db.session.flush()
    return obj


def _store(storage, paper, parsed) -> PaperFile:
    data = storage.read()
    storage.seek(0)
    sha = hashlib.sha256(data).hexdigest()
    stored = f"{sha[:16]}_{secure_filename(storage.filename)}"
    os.makedirs(current_app.config["UPLOAD_FOLDER"], exist_ok=True)
    with open(os.path.join(current_app.config["UPLOAD_FOLDER"], stored), "wb") as fh:
        fh.write(data)
    paper_file = PaperFile(paper=paper, doc_type=parsed.doc_type, original_filename=storage.filename,
                           stored_filename=stored, sha256=sha, size_bytes=len(data))
    db.session.add(paper_file)  # backrefs no longer cascade into the session automatically
    return paper_file


def create_paper(qp_storage, qp_parsed, ms_storage, ms_parsed, user) -> Paper:
    subject, component = resolve_target(qp_parsed)
    session = _get_or_create(ExamSession, board_id=subject.qualification.board_id,
                             year=qp_parsed.year, series_code=qp_parsed.series_code)
    variant = _get_or_create(PaperVariant, component_id=component.id, variant_number=qp_parsed.variant_number)
    batch = UploadBatch(uploaded_by=user.id, note=qp_parsed.reference)
    paper = Paper(session=session, variant=variant, batch=batch, uploaded_by=user.id,
                  total_marks=component.total_marks, status="uploaded")
    db.session.add(paper)
    _store(qp_storage, paper, qp_parsed)
    if ms_storage:
        _store(ms_storage, paper, ms_parsed)
    db.session.commit()
    return paper


def file_sha256(storage) -> str:
    data = storage.read()
    storage.seek(0)
    return hashlib.sha256(data).hexdigest()
