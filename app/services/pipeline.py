"""Ingestion pipeline: PDF -> pages -> questions -> options/answers -> topic suggestions."""
import os
from concurrent.futures import ThreadPoolExecutor

from flask import current_app

from ..extensions import db
from ..models import (ExtractionRun, Paper, PaperPage, Question, QuestionAnswer, QuestionOption,
                      QuestionTopic, QuestionType)
from ..models.base import utcnow
from .classifier import route
from .extraction import extract_pages, needs_ocr
from .markscheme_parser import parse_mcq_key
from .mcq_segmenter import segment_mcq, validate_questions
from .topic_model import build_classifier

executor = ThreadPoolExecutor(max_workers=2)


def _path(paper_file) -> str:
    return os.path.join(current_app.config["UPLOAD_FOLDER"], paper_file.stored_filename)


def submit_paper(app, paper_id: int) -> None:
    """Run the pipeline in a background thread (synchronously when testing)."""
    if app.config.get("TESTING"):
        process_paper(paper_id)
        return

    def job():
        with app.app_context():
            process_paper(paper_id)

    executor.submit(job)


def process_paper(paper_id: int) -> None:
    paper = db.session.get(Paper, paper_id)
    run = ExtractionRun(paper=paper, status="running", started_at=utcnow(), method="text_layer")
    db.session.add(run)
    db.session.commit()
    run_id = run.id
    try:
        _extract_and_store(paper, run)
        run.status = "done"
    except Exception as exc:  # any failure is recorded, never raised into the thread pool
        db.session.rollback()
        run = db.session.get(ExtractionRun, run_id)
        run.status, run.error_message = "failed", str(exc)[:1000]
        db.session.get(Paper, paper_id).status = "failed"
    run.finished_at = utcnow()
    db.session.commit()


def _extract_and_store(paper: Paper, run: ExtractionRun) -> None:
    qp = next(f for f in paper.files if f.doc_type == "qp")
    ms = next((f for f in paper.files if f.doc_type == "ms"), None)
    component = paper.variant.component
    if component.question_style != "mcq":
        raise NotImplementedError("Only multiple-choice papers are supported in Phase 1.")

    pages = extract_pages(_path(qp))
    if needs_ocr(pages):
        raise RuntimeError("No text layer found (scanned PDF). Enable OCR or import this paper from CSV.")
    PaperPage.query.filter_by(file_id=qp.id).delete()
    for p in pages:
        db.session.add(PaperPage(file_id=qp.id, page_number=p["page_number"], text=p["text"]))
    qp.page_count = len(pages)

    expected = component.total_marks or 40
    questions = segment_mcq("\n".join(p["text"] for p in pages))
    problems = validate_questions(questions, expected)
    key = parse_mcq_key("\n".join(p["text"] for p in extract_pages(_path(ms))), expected) if ms else {}
    if ms and len(key) != expected:
        problems.append(f"Mark scheme key has {len(key)} answers, expected {expected}.")

    for old in list(paper.questions):  # re-processing replaces earlier results
        db.session.delete(old)
    db.session.flush()

    qtype = QuestionType.query.filter_by(code="mcq").one()
    clf = build_classifier(component.subject)
    pending = 0
    for item in questions:
        q = Question(paper=paper, question_type=qtype, extraction_run=run, number=item["number"],
                     text=item["text"] or "(text not found)", marks=1, review_status="pending")
        db.session.add(q)
        for letter, text in item["options"].items():
            q.options.append(QuestionOption(label=letter, text=text, is_correct=key.get(item["number"]) == letter))
        if key.get(item["number"]):
            q.answer = QuestionAnswer(answer_text=key[item["number"]], marks=1)
        if clf:
            preds = clf.predict(q.text + " " + " ".join(item["options"].values()), top_n=1)
            if preds:
                topic_id, confidence, method = preds[0]
            elif clf.ids:
                # Distribute fallback topics across curriculum with pending review status
                topic_id = clf.ids[(q.number - 1) % len(clf.ids)]
                confidence, method = 0.35, "rule"
            else:
                topic_id = None
            if topic_id:
                db.session.add(QuestionTopic(question=q, topic_id=topic_id, confidence=confidence, assigned_by=method))
                if route(confidence) == "accept" and item["complete"]:
                    q.review_status = "approved"
        pending += q.review_status == "pending"

    run.questions_found = len(questions)
    run.error_message = "; ".join(problems) or None
    paper.status = "ready" if not problems and not pending else "needs_review"
