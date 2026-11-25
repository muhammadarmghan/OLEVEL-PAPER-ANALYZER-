"""Debug exactly why Chemistry Paper 8 stops at Q21."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from run import app
from app.extensions import db
from app.models import Paper
from app.services.extraction import extract_pages
from app.services.mcq_segmenter import _clean_lines, _BARE_NUMBER, _INLINE_Q, _is_bare_question_number, OPTION, LETTERS, _is_option_a, _SECTION_END

with app.app_context():
    p8 = db.session.get(Paper, 8)
    qp8 = next(f for f in p8.files if f.doc_type == 'qp')
    path8 = os.path.join(app.config['UPLOAD_FOLDER'], qp8.stored_filename)
    pages8 = extract_pages(path8)
    text8 = '\n'.join(pg['text'] for pg in pages8)
    lines8 = _clean_lines(text8)

    # Find Q21 position from debug_papers2 output: line 365
    # Look at lines around 365
    print("Lines 355-420 (around Q21-Q22 boundary):")
    for j in range(355, min(420, len(lines8))):
        line = lines8[j]
        m_inline = _INLINE_Q.match(line)
        bare = _BARE_NUMBER.match(line)
        sec_end = _SECTION_END.search(line)
        note = ""
        if m_inline: note = f"INLINE_Q num={m_inline[1]}"
        elif bare: note = f"BARE_NUM={bare[1]}"
        elif sec_end: note = f"SECTION_END!"
        print(f"  [{j:4d}] {repr(line[:80]):85s} {note}")

