from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField, FileRequired
from wtforms import SubmitField, ValidationError

from ..models import PaperFile
from ..services.filename_parser import parse_filename
from ..services.papers import existing_paper, file_sha256, resolve_target


def _parse(field, expected_type):
    try:
        parsed = parse_filename(field.data.filename)
    except ValueError as exc:
        raise ValidationError(str(exc))
    if parsed.doc_type != expected_type:
        raise ValidationError(f"Expected a '{expected_type}' file but got '{parsed.doc_type}'.")
    return parsed


class UploadForm(FlaskForm):
    qp_file = FileField("Question paper (PDF)", validators=[FileRequired(), FileAllowed(["pdf"], "PDF files only.")])
    ms_file = FileField("Mark scheme (PDF, optional)", validators=[FileAllowed(["pdf"], "PDF files only.")])
    submit = SubmitField("Upload and process")

    def validate_qp_file(self, field):
        parsed = _parse(field, "qp")
        try:
            resolve_target(parsed)
        except ValueError as exc:
            raise ValidationError(str(exc))
        if existing_paper(parsed):
            raise ValidationError(f"{parsed.reference} has already been uploaded.")
        if PaperFile.query.filter_by(sha256=file_sha256(field.data)).first():
            raise ValidationError("This exact file was already uploaded under another name.")

    def validate_ms_file(self, field):
        if not field.data:
            return
        parsed = _parse(field, "ms")
        try:
            qp = parse_filename(self.qp_file.data.filename)
        except (ValueError, AttributeError):
            return  # the qp_file error is reported on its own field
        same = (qp.subject_code, qp.series_code, qp.year, qp.paper_number, qp.variant_number)
        if same != (parsed.subject_code, parsed.series_code, parsed.year, parsed.paper_number, parsed.variant_number):
            raise ValidationError("The mark scheme must belong to the same paper as the question paper.")
