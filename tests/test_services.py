"""Unit tests for the pure pipeline modules (no database needed)."""
import os
import random
import tempfile
from datetime import date

import pymupdf
import pytest

from app.services.classifier import TopicClassifier, route
from app.services.extraction import extract_pages, needs_ocr, sha256_file
from app.services.filename_parser import parse_filename
from app.services.markscheme_parser import parse_mcq_key
from app.services.mcq_segmenter import segment_mcq, validate_questions
from app.services.scoring import backtest, compute_signals, explain, score_topics, tune_weights
from app.services.study_plan import schedule_topics

SAMPLE = """5054/12/M/J/21
© UCLES 2021
1 Which quantity is a vector?
A mass
B speed
C time
D weight
2 A student measures the length of a wire with a ruler.
A ruler is accurate to 1 mm.
What is the best estimate of the length?
A 12.3 cm
B 12.34 cm
C 12.345 cm
D
12.3456 cm
[Turn over
BLANK PAGE
3 A car accelerates from rest to 20 m/s in 5.0 s.
What is the acceleration?
A 0.25 m/s2
B 4.0 m/s2
C 15 m/s2
D 100 m/s2
"""


def test_filename_parser():
    p = parse_filename("5054_s21_qp_12.pdf")
    assert (p.subject_code, p.year, p.series_code, p.paper_number, p.variant_number) == ("5054", 2021, "s", 1, 2)
    assert p.session_label == "May/Jun 2021" and p.reference == "5054_s21_qp_12"
    for bad in ("physics.pdf", "5054_x21_qp_12.pdf", "5054_s21_qp_1.pdf"):
        with pytest.raises(ValueError):
            parse_filename(bad)


def test_mcq_segmenter_handles_noise_and_stem_text_starting_with_a():
    qs = segment_mcq(SAMPLE)
    assert [q["number"] for q in qs] == [1, 2, 3]
    assert qs[1]["text"].startswith("A student measures") and "ruler is accurate" in qs[1]["text"]
    assert qs[1]["options"]["D"] == "12.3456 cm" and all(q["complete"] for q in qs)
    assert validate_questions(qs, 3) == [] and "expected 40" in validate_questions(qs)[0]


def test_mark_scheme_key_ignores_stray_numbers():
    ms = "Question Answer Marks\n1 B 1\n2 D 1\n3 B 1\nPage 2 of 4\n"
    assert parse_mcq_key(ms, 3) == {1: "B", 2: "D", 3: "B"}


def test_pdf_extraction_round_trip():
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "t.pdf")
        doc = pymupdf.open()
        doc.new_page().insert_text((72, 72), "1 Which unit measures force? " * 3)
        doc.save(path)
        doc.close()
        pages = extract_pages(path)
        assert pages[0]["has_text"] and not needs_ocr(pages) and len(sha256_file(path)) == 64


TOPICS = [
    {"id": 1, "text": "Motion speed velocity acceleration distance time graphs", "keywords": {"acceleration": 1.0, "velocity": 1.0}},
    {"id": 2, "text": "Electric circuits current voltage resistance resistor", "keywords": {"current": 1.0, "resistor": 1.0, "voltage": 1.0}},
    {"id": 3, "text": "Radioactivity alpha beta gamma half-life decay", "keywords": {"half-life": 1.0, "alpha": 1.0, "gamma": 1.0}},
]


def test_classifier_rules_then_trained_model():
    clf = TopicClassifier(TOPICS)
    top = clf.predict("A car accelerates from rest. Calculate its acceleration and final velocity.")
    assert top[0][0] == 1 and top[0][1] > 0.5
    assert clf.predict("The current through the resistor is 2 A when the voltage is 6 V")[0][0] == 2
    assert (route(0.8), route(0.5), route(0.1)) == ("accept", "review", "flag")
    clf.fit(["speed of a train", "velocity time graph", "current in a wire", "voltage across a lamp",
             "alpha particle emission", "half-life of a sample"] * 5, [1, 1, 2, 2, 3, 3] * 5)
    assert clf.predict("the gamma ray source decays")[0][0] == 3


def _synthetic_history(n_sessions=12, n_topics=8):
    random.seed(4)
    history = {}
    for tid in range(1, n_topics + 1):
        p = 0.9 if tid <= 3 else 0.3
        history[tid] = ([1 if random.random() < p else 0 for _ in range(n_sessions)], [0.0] * n_sessions)
    for s in range(n_sessions):
        present = [t for t in history if history[t][0][s]] or [1]
        for t in present:
            history[t][1][s] = 1 / len(present)
    return history


def test_scoring_tiers_and_backtest():
    history = _synthetic_history()
    ranked = score_topics({t: (a[:8], sh[:8]) for t, (a, sh) in history.items()})
    assert len(ranked) == 8 and ranked[0].tier == "very_likely" and ranked[-1].tier == "lower"
    assert len(explain(ranked[0], 8)) == 4
    rows = backtest(history, k=3)
    assert len(rows) == 8 and all(0 <= r["hit_rate"] <= 1 for r in rows)
    best, _ = tune_weights(history, k=3, step=0.25)
    assert abs(sum(best.values()) - 1) < 1e-9
    sig = compute_signals([1, 0, 1, 0, 0], [0.2, 0, 0.2, 0, 0])
    assert sig["sessions_since_last"] == 2 and sig["appearances"] == 2


def test_study_schedule_leaves_revision_days():
    plan = schedule_topics([10, 11, 12, 13], date(2026, 11, 1), date(2026, 11, 21), revision_days=2)
    assert plan[0][1] == date(2026, 11, 1) and plan[-1][1] < date(2026, 11, 20)
