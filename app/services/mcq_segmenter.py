"""Split the text of a multiple-choice question paper into numbered questions.

PDF text extraction often places the question number on one line and the
question text on the next line(s).  Options A-D may also appear as bare
letters with the option text on the following line.

Supported formats:
  Format A (inline):  "1 Which quantities are both vectors?"
  Format B (bare num): "1" on its own line, text on next line(s)
  Format C (bare opt): "A" on its own line, option text on next line(s)

The segmenter stops *starting* new questions once max_questions questions
have been accumulated, but continues collecting options for the last
question. It also stops when it detects an appendix section (Periodic Table,
Data Sheet, etc.) to avoid false positives.
"""
import re

# ---------------------------------------------------------------------------
# Noise patterns – lines matching these are removed before segmentation
# ---------------------------------------------------------------------------
NOISE = [re.compile(p, re.IGNORECASE) for p in (
    r"^©\s*UCLES",
    r"^\[?\s*Turn over\s*\]?$",
    r"^\d{4}/\d{2}/[A-Z]/[A-Z]/\d{2}",
    r"^\d{4}/\d+/[MOSW]/\d{2}",
    r"^BLANK PAGE$",
    r"^\*?\d{8,}\*?$",
    r"^Permission to reproduce",
    r"^DO NOT WRITE",
    r"^\d+\s*hours?(?:\s+\d+\s*minutes?)?.*$",
    r"^INSTRUCTIONS.*$",
    r"^INFORMATION.*$",
    r"^You must answer on.*$",
    r"^You will need:.*$",
    r"^Write in soft pencil.*$",
    r"^There are (?:thirty|forty|\d+) questions.*$",
    r"^The total mark for this paper.*$",
    r"^Answer all questions\.*$",
    r"^Each correct answer will score.*$",
    r"^No marks will be given.*$",
    r"^Do not use an erasable pen.*$",
    r"^Read the instructions on the Answer Sheet.*$",
    r"^READ THESE INSTRUCTIONS.*$",
    r"^Electronic calculators may be used.*$",
    r"^Any rough working.*$",
    r"^Choose the one you consider correct.*$",
    r"^Write your name.*$",
    r"^Do not use staples.*$",
    r"^This document consists.*$",
    r"^This document has \d+ pages.*$",
    r"^Additional Materials.*$",
    r"^Multiple Choice Answer Sheet.*$",
    r"^Soft clean eraser.*$",
    r"^Soft pencil.*$",
    r"^Cambridge Assessment.*$",
    r"^Cambridge Ordinary Level$",
    r"^Cambridge O Level$",
    r"^PHYSICS$",
    r"^CHEMISTRY$",
    r"^BIOLOGY$",
    r"^\d{4}/\d+$",           # paper codes like 5054/11
    r"^Paper \d+ Multiple Choice.*$",
    r"^May/June \d{4}$",
    r"^Oct(?:ober)?/Nov(?:ember)? \d{4}$",
    r"^Mar(?:ch)? \d{4}$",
    r"^February/March \d{4}$",
    r"^IB\d+ \d{2}_\d+.*$",   # Cambridge batch codes like IB19 06_5054_11/3RP
    r"^unless this has been done.*$",
    r"^answers A, B, C and D.*$",
    r"^For each question there are four possible answers.*$",
    r"^Follow the instructions on the multiple choice.*$",
    r"^spaces provided unless.*$",
    r"^Do not use correction fluid.*$",
    r"^You may use a calculator.*$",
    r"^\u00b7$",   # bullet points
    r"^\uf0b7$",   # private-use bullet
    r"^\x00+$",    # null bytes
    # Periodic Table / data sheet markers
    r"^The Periodic Table",
    r"^Periodic Table",
    r"^Group$",
    r"^Period$",
    r"^Key$",
    r"^relative atomic mass$",
    r"^proton number$",
    r"^atomic number$",
    r"^Data Sheet",
    r"^Formula Sheet",
)]

# A line that is PURELY a 1-or-2-digit number (optionally surrounded by space).
_BARE_NUMBER = re.compile(r"^\s*(\d{1,2})\s*$")
# A line that starts with a 1-or-2-digit number followed by at least one space
# and then at least one non-space character.
_INLINE_Q = re.compile(r"^(\d{1,2})\s+(\S.*)")
# Option line: single letter A-D optionally followed by text (may be bare)
OPTION = re.compile(r"^([A-D])(?:\s+(.*))?$")
LETTERS = "ABCD"

# Sentinel: if we see these *at the start* of a line after Q10, the question
# body has ended.  Anchored to ^ so "Periodic Table" inside a question stem
# (e.g. "… are in Group I or Group VII of the Periodic Table.") does NOT fire.
_SECTION_END = re.compile(
    r"^(?:The Periodic Table|Periodic Table of|Data Sheet|Formula Sheet)",
    re.IGNORECASE,
)


def _clean_lines(text: str) -> list[str]:
    out = []
    for raw in text.splitlines():
        line = re.sub(r"\s+", " ", raw).strip()
        if line and not any(p.search(line) for p in NOISE):
            out.append(line)
    return out


def _is_option_a(lines: list[str], idx: int, window: int = 15) -> bool:
    """Return True if the 'A' (or 'A text') line at *idx* is really option A.

    Heuristic: B, C, or D (bare or inline) must appear within the next
    *window* lines before another 'A' line does.  Works for both:
      - "A acceleration and length"  (inline)
      - "A" followed by "acceleration and length"  (bare-letter format)
    """
    for ln in lines[idx + 1: idx + 1 + window]:
        if re.match(r"^[B-D](\s|$)", ln):
            return True
        if re.match(r"^A(\s|$)", ln):
            return False
    return False


def _is_bare_question_number(lines: list[str], idx: int, expected: int) -> bool:
    """Return True when lines[idx] is a bare question number equal to *expected*.

    Distinguish question numbers from page numbers:
    - A page number is typically preceded by or followed by another bare number.
    - A question number is followed by meaningful text content.
    """
    m = _BARE_NUMBER.match(lines[idx])
    if not m or int(m[1]) != expected:
        return False
    # Peek forward: the next line must exist and must not be another bare number
    # (two consecutive bare numbers means: page-number then question-number)
    if idx + 1 >= len(lines):
        return False
    next_line = lines[idx + 1]
    next_bare = _BARE_NUMBER.match(next_line)
    if next_bare:
        # e.g. "2\n1\n..." — first is a page number, second is Q1
        return False
    # Must have actual text content on the next line
    return bool(next_line.strip())


def segment_mcq(text: str, max_questions: int = 40) -> list[dict]:
    """Return a list of dicts with keys: number, text, options, complete.

    Handles PDFs where:
    - question numbers may be inline or on their own line
    - option letters A-D may be inline or on their own line (bare)
    - diagrams / tables create gaps in the option text flow

    Key behaviour:
    - Stops *starting* new questions once max_questions have been found, but
      continues reading options for the last question (Q40 stays complete).
    - Breaks early when a Periodic Table / Data Sheet section is detected after
      Q10 to avoid appendix content being misread as questions.
    """
    lines = _clean_lines(text)
    questions: list[dict] = []
    current: dict | None = None
    expected = 1
    past_q10 = False

    i = 0
    while i < len(lines):
        line = lines[i]

        # Detect appendix sections only after Q10
        if past_q10 and _SECTION_END.search(line):
            break

        # Once all expected questions have been started, only accumulate
        # options/stem for the last one — do NOT start new questions.
        if expected > max_questions:
            if current is not None:
                opt = OPTION.match(line)
                if opt and opt[1] in LETTERS and opt[1] not in current["options"]:
                    if opt[1] != "A" or _is_option_a(lines, i):
                        current["options"][opt[1]] = opt[2] or ""
                        current["open"] = opt[1]
                        i += 1
                        continue
                    # bare option A — could not confirm, skip for now
                # Continuation text for current option or bare option text
                if current["open"] != "stem" and current["open"] in current["options"]:
                    # Bare-letter option: the text is on the next line
                    if not OPTION.match(line) and not _BARE_NUMBER.match(line):
                        current["options"][current["open"]] = (
                            current["options"][current["open"]] + " " + line
                        ).strip()
                # Stop once all 4 options are collected
                if len(current["options"]) == 4:
                    break
            else:
                break
            i += 1
            continue

        # ---- Detect the start of a new question ----
        q_num = None
        q_stem_start = None

        # Format A: "1  Which quantities are both vectors?"
        m_inline = _INLINE_Q.match(line)
        if m_inline and int(m_inline[1]) == expected:
            q_num = expected
            q_stem_start = m_inline[2]

        # Format B: bare number "1" followed by text on the next line
        elif _is_bare_question_number(lines, i, expected):
            q_num = expected
            q_stem_start = None   # text will be picked up in stem mode on next iteration

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
            expected += 1
            i += 1
            continue

        # ---- Accumulate into the current question ----
        if current is None:
            i += 1
            continue

        opt = OPTION.match(line)
        if opt and opt[1] in LETTERS and opt[1] not in current["options"]:
            if opt[1] != "A" or _is_option_a(lines, i):
                current["options"][opt[1]] = opt[2] or ""
                current["open"] = opt[1]
                i += 1
                continue

        # Continuation of stem or last option
        if current["open"] == "stem":
            current["stem"].append(line)
        else:
            # Append continuation text to the currently open option
            current["options"][current["open"]] = (
                current["options"][current["open"]] + " " + line
            ).strip()

        i += 1

    return [
        {
            "number": q["number"],
            "text":   " ".join(s for s in q["stem"] if s).strip(),
            "options": q["options"],
            "complete": len(q["options"]) == 4,
        }
        for q in questions
    ]


def validate_questions(questions: list[dict], expected_count: int = 40) -> list[str]:
    """Human-readable problems; an empty list means the paper looks correct."""
    problems: list[str] = []
    if len(questions) != expected_count:
        problems.append(f"Found {len(questions)} questions, expected {expected_count}.")
    problems += [
        f"Question {q['number']} has {len(q['options'])} options."
        for q in questions
        if not q["complete"]
    ]
    return problems
