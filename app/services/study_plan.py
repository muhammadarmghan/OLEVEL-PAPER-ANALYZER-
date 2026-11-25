"""Spread the highest-priority topics evenly between today and the exam."""
from datetime import date, timedelta


def schedule_topics(topic_ids_by_priority, start: date, exam: date, revision_days: int = 2):
    """Return [(topic_id, planned_date)]. The last `revision_days` stay free for revision."""
    study_days = max((exam - start).days - revision_days, 1)
    n = len(topic_ids_by_priority)
    return [(tid, start + timedelta(days=(i * study_days) // n)) for i, tid in enumerate(topic_ids_by_priority)]
