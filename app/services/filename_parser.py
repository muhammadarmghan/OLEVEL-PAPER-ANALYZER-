"""Parse Cambridge-style file names such as 5054_s21_qp_12.pdf."""
import re
from dataclasses import dataclass

SERIES_LABELS = {"m": "Feb/Mar", "s": "May/Jun", "w": "Oct/Nov"}

PATTERN = re.compile(
    r"^(?P<code>\d{4})_(?P<series>[msw])(?P<yy>\d{2})_(?P<doc>qp|ms)_(?P<paper>\d)(?P<variant>\d)\.pdf$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ParsedName:
    subject_code: str
    series_code: str      # m / s / w
    year: int             # 4-digit
    doc_type: str         # qp / ms
    paper_number: int
    variant_number: int

    @property
    def session_label(self) -> str:
        return f"{SERIES_LABELS[self.series_code]} {self.year}"

    @property
    def reference(self) -> str:
        return f"{self.subject_code}_{self.series_code}{self.year % 100:02d}_{self.doc_type}_{self.paper_number}{self.variant_number}"


def parse_filename(filename: str) -> ParsedName:
    """Return the parsed parts or raise ValueError with a student-friendly message."""
    match = PATTERN.match(filename.strip())
    if not match:
        raise ValueError(
            "File name must look like 5054_s21_qp_12.pdf "
            "(subject code, session+year, qp or ms, paper+variant)."
        )
    return ParsedName(
        subject_code=match["code"],
        series_code=match["series"].lower(),
        year=2000 + int(match["yy"]),
        doc_type=match["doc"].lower(),
        paper_number=int(match["paper"]),
        variant_number=int(match["variant"]),
    )
