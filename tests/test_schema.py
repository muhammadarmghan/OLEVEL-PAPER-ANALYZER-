import pytest
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import (
    ALL_MODELS,
    ExamBoard,
    ExamSession,
    Paper,
    PaperComponent,
    PaperVariant,
    Qualification,
    Question,
    QuestionOption,
    QuestionTopic,
    QuestionType,
    Role,
    Subject,
    SyllabusVersion,
    Topic,
    Unit,
    User,
)


def build_chain():
    """Create one complete path: board -> subject -> paper -> question -> topic."""
    board = ExamBoard(name="Cambridge", short_code="CAIE")
    qual = Qualification(board=board, name="O Level")
    subject = Subject(qualification=qual, code="5054", name="Physics")
    component = PaperComponent(subject=subject, paper_number=1, question_style="mcq", total_marks=40)
    variant = PaperVariant(component=component, variant_number=2)
    session = ExamSession(board=board, year=2021, series_code="s")
    paper = Paper(session=session, variant=variant, total_marks=40)
    qtype = QuestionType(code="mcq", name="Multiple choice")
    question = Question(paper=paper, question_type=qtype, number=1, text="Which unit measures force?", marks=1)
    question.options = [
        QuestionOption(label="A", text="joule"),
        QuestionOption(label="B", text="newton", is_correct=True),
    ]
    version = SyllabusVersion(subject=subject, version_label="2023-2025", valid_from_year=2023)
    unit = Unit(syllabus_version=version, number=1, title="Motion, forces and energy")
    topic = Topic(unit=unit, code="1.5", title="Forces")
    link = QuestionTopic(question=question, topic=topic, confidence=0.9, assigned_by="rule")
    db.session.add_all([board, link])
    db.session.commit()
    return paper, question, topic


def test_minimum_table_count(app):
    assert len(db.metadata.tables) >= 40


def test_model_registry_covers_every_table(app):
    registered = {m.__tablename__ for m in ALL_MODELS}
    assert registered | {"question_command_words"} == set(db.metadata.tables)


def test_no_standalone_tables(app):
    tables = db.metadata.tables.values()
    referenced = {fk.column.table.name for t in tables for fk in t.foreign_keys}
    standalone = [t.name for t in tables if not t.foreign_keys and t.name not in referenced]
    assert standalone == []


def test_relationship_chain_navigates_end_to_end(app):
    _, question, _ = build_chain()
    topic = question.topic_links[0].topic
    assert topic.unit.syllabus_version.subject.code == "5054"
    assert topic.unit.syllabus_version.subject.qualification.board.short_code == "CAIE"
    assert question.paper.session.label == "May/Jun 2021"
    assert [o.label for o in question.options if o.is_correct] == ["B"]


def test_many_to_many_user_roles(app):
    user = User(username="sara", email="sara@example.com")
    user.set_password("s3cret-pass")
    user.roles.append(Role(name="student"))
    db.session.add(user)
    db.session.commit()
    assert user.has_role("student")
    assert user.check_password("s3cret-pass")
    assert not user.check_password("wrong")
    assert user.roles[0].users == [user]


def test_deleting_paper_cascades_to_questions_and_options(app):
    paper, _, _ = build_chain()
    db.session.delete(paper)
    db.session.commit()
    assert Question.query.count() == 0
    assert QuestionOption.query.count() == 0
    assert QuestionTopic.query.count() == 0


def test_duplicate_paper_rejected(app):
    paper, _, _ = build_chain()
    db.session.add(Paper(session_id=paper.session_id, variant_id=paper.variant_id))
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_confidence_check_constraint(app):
    _, question, topic = build_chain()
    other = Topic(unit=topic.unit, code="1.6", title="Energy")
    db.session.add(QuestionTopic(question=question, topic=other, confidence=1.5))
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()
