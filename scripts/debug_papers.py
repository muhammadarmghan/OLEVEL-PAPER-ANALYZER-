"""Debug Paper 8 (Chemistry) text to understand its format."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from run import app
from app.extensions import db
from app.models import Paper
from app.services.extraction import extract_pages
from app.services.mcq_segmenter import _clean_lines

with app.app_context():
    # Check paper 2 Q40 area
    p2 = db.session.get(Paper, 2)
    qp2 = next(f for f in p2.files if f.doc_type == 'qp')
    path2 = os.path.join(app.config['UPLOAD_FOLDER'], qp2.stored_filename)
    pages2 = extract_pages(path2)
    text2 = '\n'.join(pg['text'] for pg in pages2)
    lines2 = _clean_lines(text2)
    # Find where Q40 is in the lines
    q40_idx = None
    for i, ln in enumerate(lines2):
        if ln.strip() == '40':
            q40_idx = i
    print(f"Paper 2: Q40 at line index {q40_idx}")
    if q40_idx:
        print("Lines around Q40:")
        for j in range(q40_idx, min(q40_idx+15, len(lines2))):
            print(f"  [{j}] {repr(lines2[j])}")

    print()

    # Check paper 8 (Chemistry)
    p8 = db.session.get(Paper, 8)
    qp8 = next(f for f in p8.files if f.doc_type == 'qp')
    path8 = os.path.join(app.config['UPLOAD_FOLDER'], qp8.stored_filename)
    pages8 = extract_pages(path8)
    text8 = '\n'.join(pg['text'] for pg in pages8)
    lines8 = _clean_lines(text8)
    print(f"Paper 8: total cleaned lines = {len(lines8)}")
    print("First 60 lines of Chemistry paper:")
    for i, ln in enumerate(lines8[:60]):
        print(f"  [{i:3d}] {repr(ln[:90])}")

