"""Quick test of the segmenter on all papers."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from run import app
from app.extensions import db
from app.models import Paper
from app.services.extraction import extract_pages
from app.services.mcq_segmenter import segment_mcq, validate_questions

with app.app_context():
    papers = Paper.query.all()
    for p in papers:
        qp = next((f for f in p.files if f.doc_type == 'qp'), None)
        if not qp:
            print(f"Paper {p.id}: no QP file")
            continue
        path = os.path.join(app.config['UPLOAD_FOLDER'], qp.stored_filename)
        pages = extract_pages(path)
        text = '\n'.join(pg['text'] for pg in pages)
        qs = segment_mcq(text)
        problems = validate_questions(qs)
        icon = "OK" if not problems else "FAIL"
        print(f"[{icon}] Paper {p.id}: {len(qs)} questions | {problems if problems else 'no problems'}")
        if qs:
            q1 = qs[0]
            print(f"       Q1: {q1['text'][:70]!r} | opts={list(q1['options'].keys())}")
            if len(qs) >= 40:
                q40 = qs[39]
                print(f"       Q40: {q40['text'][:70]!r} | opts={list(q40['options'].keys())}")
            if len(qs) > 40:
                q41 = qs[40]
                print(f"       Q41 (should not exist): {q41['text'][:70]!r}")

