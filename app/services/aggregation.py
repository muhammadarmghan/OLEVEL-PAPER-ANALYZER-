"""Database -> per-topic, per-session history; yearly topic statistics."""
from collections import defaultdict
from dataclasses import dataclass

from ..extensions import db
from ..models import (ExamSession, Paper, PaperComponent, PaperVariant, Question, QuestionTopic,
                      Subject, TopicStat)
from .topic_model import current_topics

SERIES_ORDER = {"m": 0, "s": 1, "w": 2}  # Feb/Mar, May/Jun, Oct/Nov within a year


@dataclass
class History:
    sessions: list        # ExamSession objects, oldest -> newest
    topic_ids: list
    appeared: dict        # topic_id -> [0/1 per session]
    marks: dict           # topic_id -> [marks attributed per session]
    totals: list          # total attributed marks per session

    def for_scoring(self) -> dict:
        return {t: (self.appeared[t], [m / tot if tot else 0.0 for m, tot in zip(self.marks[t], self.totals)])
                for t in self.topic_ids}


def build_history(subject_id: int) -> History:
    subject = db.session.get(Subject, subject_id)
    topic_ids = [t.id for t in current_topics(subject)]
    rows = (db.session.query(Question.id, Question.marks, QuestionTopic.topic_id, QuestionTopic.confidence, ExamSession)
            .join(QuestionTopic, QuestionTopic.question_id == Question.id)
            .join(Paper, Question.paper_id == Paper.id)
            .join(PaperVariant, Paper.variant_id == PaperVariant.id)
            .join(PaperComponent, PaperVariant.component_id == PaperComponent.id)
            .join(ExamSession, Paper.session_id == ExamSession.id)
            .filter(PaperComponent.subject_id == subject_id, Question.review_status == "approved",
                    QuestionTopic.topic_id.in_(topic_ids)).all())

    per_question = defaultdict(lambda: {"marks": 1, "session": None, "links": []})
    for qid, marks, topic_id, confidence, session in rows:
        entry = per_question[qid]
        entry.update(marks=marks or 1, session=session)
        entry["links"].append((topic_id, confidence or 1.0))

    unique = {e["session"].id: e["session"] for e in per_question.values()}
    sessions = sorted(unique.values(), key=lambda s: (s.year, SERIES_ORDER[s.series_code]))
    index = {s.id: i for i, s in enumerate(sessions)}
    appeared = {t: [0] * len(sessions) for t in topic_ids}
    marks = {t: [0.0] * len(sessions) for t in topic_ids}
    totals = [0.0] * len(sessions)
    for e in per_question.values():
        i = index[e["session"].id]
        total_conf = sum(c for _, c in e["links"]) or 1.0
        totals[i] += e["marks"]
        for topic_id, conf in e["links"]:   # a question shared by several topics splits its marks
            appeared[topic_id][i] = 1
            marks[topic_id][i] += e["marks"] * conf / total_conf
    return History(sessions, topic_ids, appeared, marks, totals)


def recompute_topic_stats(subject_id: int) -> int:
    """Rebuild topic_stats for the subject. Returns the number of years covered."""
    h = build_history(subject_id)
    TopicStat.query.filter(TopicStat.topic_id.in_(h.topic_ids)).delete(synchronize_session=False)
    years = sorted({s.year for s in h.sessions})
    for topic_id in h.topic_ids:
        for year in years:
            idx = [i for i, s in enumerate(h.sessions) if s.year == year]
            topic_marks = sum(h.marks[topic_id][i] for i in idx)
            year_total = sum(h.totals[i] for i in idx)
            seen = [i for i in range(idx[-1] + 1) if h.appeared[topic_id][i]]
            db.session.add(TopicStat(
                topic_id=topic_id, exam_year=year,
                appearances=sum(h.appeared[topic_id][i] for i in idx),
                total_marks=round(topic_marks),
                mark_share=topic_marks / year_total if year_total else 0.0,
                sessions_since_last=idx[-1] - seen[-1] if seen else None))
    db.session.commit()
    return len(years)
