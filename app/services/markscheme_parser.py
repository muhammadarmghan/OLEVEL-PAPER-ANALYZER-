"""Read the answer key of a multiple-choice mark scheme."""
import re

KEY = re.compile(r"(?<!\d)(\d{1,2})\s+([A-D])(?=\s|$)")


def parse_mcq_key(text: str, expected: int = 40) -> dict[int, str]:
    """Return {1: 'B', 2: 'D', ...}. Only accepts answers in strict 1..N order,
    so stray numbers in headers or footers cannot corrupt the key."""
    answers, wanted = {}, 1
    for match in KEY.finditer(text):
        if int(match[1]) == wanted:
            answers[wanted] = match[2]
            wanted += 1
            if wanted > expected:
                break
    return answers
