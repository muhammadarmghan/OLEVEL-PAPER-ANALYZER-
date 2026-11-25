import os

from flask import Blueprint, abort, current_app, flash, g, jsonify, redirect, render_template, request, url_for

from ..auth_utils import login_required, role_required
from ..extensions import db
from ..forms.papers import UploadForm
from ..models import Paper
from ..services.filename_parser import parse_filename
from ..services.papers import create_paper
from ..services.pipeline import submit_paper

bp = Blueprint("papers", __name__, url_prefix="/papers")


@bp.route("/")
def index():
    subject_id = request.args.get("subject", type=int)
    year = request.args.get("year", type=int)
    session_code = request.args.get("session", type=str)
    paper_number = request.args.get("paper_number", type=int)
    board_id = request.args.get("board", type=int)
    search_q = request.args.get("q", type=str, default="").strip()
    page = request.args.get("page", 1, type=int)

    from ..models import ExamBoard, ExamSession, PaperComponent, PaperVariant, Subject as SubjModel

    query = db.select(Paper).join(ExamSession, Paper.session_id == ExamSession.id).join(PaperVariant, Paper.variant_id == PaperVariant.id).join(PaperComponent, PaperVariant.component_id == PaperComponent.id)

    if subject_id:
        query = query.filter(PaperComponent.subject_id == subject_id)
    if year:
        query = query.filter(ExamSession.year == year)
    if session_code:
        query = query.filter(ExamSession.series_code == session_code)
    if paper_number:
        query = query.filter(PaperComponent.paper_number == paper_number)
    if board_id:
        query = query.filter(ExamSession.board_id == board_id)
    if search_q:
        query = query.join(SubjModel, PaperComponent.subject_id == SubjModel.id).filter(
            SubjModel.name.ilike(f"%{search_q}%") | SubjModel.code.ilike(f"%{search_q}%")
        )

    pagination = db.paginate(query.order_by(Paper.id.desc()), page=page, per_page=15, error_out=False)

    boards = ExamBoard.query.order_by(ExamBoard.name).all()
    subjects = SubjModel.query.order_by(SubjModel.name).all()
    years = [y[0] for y in db.session.query(ExamSession.year).distinct().order_by(ExamSession.year.desc()).all()]

    return render_template(
        "papers/list.html",
        pagination=pagination,
        boards=boards,
        subjects=subjects,
        years=years,
        selected_subject=subject_id,
        selected_year=year,
        selected_session=session_code,
        selected_paper=paper_number,
        selected_board=board_id,
        search_query=search_q,
    )


@bp.route("/<int:paper_id>/download/<doc_type>")
def download(paper_id, doc_type):
    from flask import send_from_directory
    paper = db.get_or_404(Paper, paper_id)
    file_record = next((f for f in paper.files if f.doc_type == doc_type), None)
    if not file_record:
        abort(404)
    upload_dir = current_app.config["UPLOAD_FOLDER"]
    return send_from_directory(
        upload_dir,
        file_record.stored_filename,
        as_attachment=True,
        download_name=file_record.original_filename
    )


@bp.route("/<int:paper_id>/view/<doc_type>")
def view_pdf(paper_id, doc_type):
    from flask import send_from_directory
    paper = db.get_or_404(Paper, paper_id)
    file_record = next((f for f in paper.files if f.doc_type == doc_type), None)
    if not file_record:
        abort(404)
    upload_dir = current_app.config["UPLOAD_FOLDER"]
    return send_from_directory(
        upload_dir,
        file_record.stored_filename,
        as_attachment=False,
        mimetype="application/pdf"
    )



@bp.route("/upload", methods=["GET", "POST"])
@role_required("contributor", "admin")
def upload():
    form = UploadForm()
    if form.validate_on_submit():
        qp = parse_filename(form.qp_file.data.filename)
        ms_storage = form.ms_file.data or None
        ms = parse_filename(ms_storage.filename) if ms_storage else None
        paper = create_paper(form.qp_file.data, qp, ms_storage, ms, g.user)
        submit_paper(current_app._get_current_object(), paper.id)
        flash("Upload received. Processing has started.", "success")
        return redirect(url_for("papers.detail", paper_id=paper.id))  # Post-Redirect-Get
    return render_template("papers/upload.html", form=form)


@bp.route("/<int:paper_id>")
def detail(paper_id):
    paper = db.get_or_404(Paper, paper_id)
    questions = sorted(paper.questions, key=lambda q: q.number)
    return render_template("papers/detail.html", paper=paper, questions=questions)


@bp.route("/<int:paper_id>/status")
def status(paper_id):
    paper = db.get_or_404(Paper, paper_id)
    run = paper.extraction_runs[-1] if paper.extraction_runs else None
    return jsonify(paper=paper.status, run=run.status if run else None,
                   questions_found=run.questions_found if run else 0, error=run.error_message if run else None)


@bp.route("/<int:paper_id>/reprocess", methods=["POST"])
@role_required("contributor", "admin")
def reprocess(paper_id):
    paper = db.get_or_404(Paper, paper_id)
    submit_paper(current_app._get_current_object(), paper.id)
    flash("Re-processing started.", "info")
    return redirect(url_for("papers.detail", paper_id=paper.id))


@bp.route("/<int:paper_id>/delete", methods=["POST"])
@role_required("contributor", "admin")
def delete(paper_id):
    paper = db.get_or_404(Paper, paper_id)
    if not g.user.has_role("admin") and paper.uploaded_by != g.user.id:
        abort(403)
    for f in paper.files:
        path = os.path.join(current_app.config["UPLOAD_FOLDER"], f.stored_filename)
        if os.path.exists(path):
            os.remove(path)
    db.session.delete(paper)
    db.session.commit()
    flash("Paper deleted.", "info")
    return redirect(url_for("papers.index"))
