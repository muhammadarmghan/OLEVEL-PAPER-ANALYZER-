"""Text-layer PDF extraction with PyMuPDF (fitz) and file hashing."""
import hashlib

import pymupdf  # PyMuPDF


def sha256_file(path: str, chunk: int = 1 << 20) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        while block := fh.read(chunk):
            digest.update(block)
    return digest.hexdigest()


def extract_pages(path: str) -> list[dict]:
    """Return [{'page_number': 1, 'text': '...', 'has_text': True}, ...]."""
    pages = []
    with pymupdf.open(path) as doc:
        for index, page in enumerate(doc, start=1):
            text = page.get_text("text") or ""
            pages.append({"page_number": index, "text": text, "has_text": len(text.strip()) > 20})
    return pages


def needs_ocr(pages: list[dict], min_ratio: float = 0.5) -> bool:
    """True when too few pages have a text layer (scanned paper)."""
    if not pages:
        return True
    return sum(p["has_text"] for p in pages) / len(pages) < min_ratio
