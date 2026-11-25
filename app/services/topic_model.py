"""Bridge between the syllabus tables and the TopicClassifier."""
from ..extensions import db
from ..models import Paper, PaperComponent, PaperVariant, Question, QuestionTopic, Subject
from .classifier import TopicClassifier

MIN_LABELLED = 150  # train the supervised model only after this many human labels


def current_topics(subject: Subject):
    """All topics of the subject's current (or newest) syllabus version."""
    versions = sorted(subject.syllabus_versions, key=lambda v: (v.is_current, v.valid_from_year), reverse=True)
    if not versions:
        return []
    return [t for unit in sorted(versions[0].units, key=lambda u: u.number)
            for t in sorted(unit.topics, key=lambda t: t.display_order)]


def question_text(question: Question) -> str:
    return " ".join([question.text, *[o.text for o in question.options]])


def build_classifier(subject: Subject):
    topics = current_topics(subject)
    if not topics:
        return None
    data = [{
        "id": t.id,
        "text": " ".join([t.title, t.description or "", *[o.text for o in t.objectives], *[k.keyword for k in t.keywords]]),
        "keywords": {k.keyword: k.weight for k in t.keywords},
    } for t in topics]
    clf = TopicClassifier(data)
    rows = (db.session.query(Question, QuestionTopic.topic_id)
            .join(QuestionTopic, QuestionTopic.question_id == Question.id)
            .join(Paper, Question.paper_id == Paper.id)
            .join(PaperVariant, Paper.variant_id == PaperVariant.id)
            .join(PaperComponent, PaperVariant.component_id == PaperComponent.id)
            .filter(PaperComponent.subject_id == subject.id, QuestionTopic.assigned_by == "human",
                    QuestionTopic.topic_id.in_([t.id for t in topics])).all())
    if len(rows) >= MIN_LABELLED and len({tid for _, tid in rows}) >= 2:
        clf.fit([question_text(q) for q, _ in rows], [tid for _, tid in rows])
    return clf
