"""Debug Paper 8 Chemistry - find why only 21 questions detected."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from run import app
from app.extensions import db
from app.models import Paper
from app.services.extraction import extract_pages
from app.services.mcq_segmenter import _clean_lines, _BARE_NUMBER, _INLINE_Q, _is_bare_question_number

with app.app_context():
    p8 = db.session.get(Paper, 8)
    qp8 = next(f for f in p8.files if f.doc_type == 'qp')
    path8 = os.path.join(app.config['UPLOAD_FOLDER'], qp8.stored_filename)
    pages8 = extract_pages(path8)
    text8 = '\n'.join(pg['text'] for pg in pages8)
    lines8 = _clean_lines(text8)
    
    print(f"Total cleaned lines: {len(lines8)}")
    
    # Find where each question number appears
    expected = 1
    found_positions = []
    i = 0
    while i < len(lines8) and expected <= 40:
        line = lines8[i]
        m_inline = _INLINE_Q.match(line)
        if m_inline and int(m_inline[1]) == expected:
            found_positions.append((expected, i, 'inline', line[:60]))
            expected += 1
        elif _is_bare_question_number(lines8, i, expected):
            found_positions.append((expected, i, 'bare', line.strip()))
            expected += 1
        i += 1
    
    print(f"\nFound {len(found_positions)} question starts (expected 40):")
    for qnum, idx, fmt, text in found_positions:
        print(f"  Q{qnum:2d} @ line {idx:4d} [{fmt}]: {repr(text)}")
    
    if expected <= 40:
        print(f"\n--- MISSING: Q{expected} not found ---")
        # Show the region where Q21 and Q22 should be
        # Find Q21's position
        q21_pos = next((idx for qnum, idx, _, _ in found_positions if qnum == 21), None)
        if q21_pos:
            print(f"\nLines after Q21 (idx={q21_pos}):")
            for j in range(q21_pos, min(q21_pos + 40, len(lines8))):
                print(f"  [{j}] {repr(lines8[j][:90])}")
    
    # Also debug Paper 2 Q9
    print("\n\n=== Paper 2 Q9 debug ===")
    p2 = db.session.get(Paper, 2)
    qp2 = next(f for f in p2.files if f.doc_type == 'qp')
    path2 = os.path.join(app.config['UPLOAD_FOLDER'], qp2.stored_filename)
    pages2 = extract_pages(path2)
    text2 = '\n'.join(pg['text'] for pg in pages2)
    lines2 = _clean_lines(text2)
    
    # Find Q8, Q9, Q10 positions
    expected = 1
    q8_pos = q9_pos = q10_pos = None
    i = 0
    while i < len(lines2) and expected <= 10:
        line = lines2[i]
        m = _INLINE_Q.match(line)
        if m and int(m[1]) == expected:
            if expected == 8: q8_pos = i
            if expected == 9: q9_pos = i
            if expected == 10: q10_pos = i
            expected += 1
        elif _is_bare_question_number(lines2, i, expected):
            if expected == 8: q8_pos = i
            if expected == 9: q9_pos = i
            if expected == 10: q10_pos = i
            expected += 1
        i += 1
    
    print(f"Q8 at line {q8_pos}, Q9 at {q9_pos}, Q10 at {q10_pos}")
    if q9_pos:
        print(f"\nLines Q9 area:")
        for j in range(q9_pos, min(q9_pos + 20, len(lines2))):
            print(f"  [{j}] {repr(lines2[j][:90])}")

