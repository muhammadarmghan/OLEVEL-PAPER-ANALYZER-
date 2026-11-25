"""Trace the segmenter step by step for Paper 8."""
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

    questions = []
    current = None
    expected = 1
    past_q10 = False
    max_questions = 40

    i = 0
    while i < len(lines8):
        line = lines8[i]

        if past_q10 and _SECTION_END.search(line):
            print(f"SECTION_END at line {i}: {repr(line)}")
            break

        if expected > max_questions:
            if current is not None:
                opt = OPTION.match(line)
                if opt and opt[1] in LETTERS and opt[1] not in current["options"]:
                    if opt[1] != "A" or _is_option_a(lines8, i):
                        current["options"][opt[1]] = opt[2] or ""
                        current["open"] = opt[1]
                        i += 1
                        continue
                if current["open"] != "stem" and current["open"] in current["options"]:
                    if not OPTION.match(line) and not _BARE_NUMBER.match(line):
                        current["options"][current["open"]] = (
                            current["options"][current["open"]] + " " + line
                        ).strip()
                if len(current["options"]) == 4:
                    print(f"All 4 options done for Q{current['number']}, stopping")
                    break
            else:
                break
            i += 1
            continue

        q_num = None
        q_stem_start = None
        m_inline = _INLINE_Q.match(line)
        if m_inline and int(m_inline[1]) == expected:
            q_num = expected
            q_stem_start = m_inline[2]
        elif _is_bare_question_number(lines8, i, expected):
            q_num = expected
            q_stem_start = None

        if q_num is not None:
            if q_num > 10:
                past_q10 = True
            current = {
                "number": expected,
                "stem": ([q_stem_start] if q_stem_start else []),
                "options": {},
                "open": "stem",
            }
            questions.append(current)
            print(f"  Q{expected} started at line {i}: {repr(line[:60])}")
            expected += 1
            i += 1
            continue

        if current is None:
            i += 1
            continue

        opt = OPTION.match(line)
        if opt and opt[1] in LETTERS and opt[1] not in current["options"]:
            if opt[1] != "A" or _is_option_a(lines8, i):
                current["options"][opt[1]] = opt[2] or ""
                current["open"] = opt[1]
                i += 1
                continue

        if current["open"] == "stem":
            current["stem"].append(line)
        else:
            current["options"][current["open"]] = (
                current["options"][current["open"]] + " " + line
            ).strip()

        i += 1

    print(f"\nTotal questions found: {len(questions)}")
    for q in questions:
        print(f"  Q{q['number']:2d}: opts={list(q['options'].keys())} complete={len(q['options'])==4}")

