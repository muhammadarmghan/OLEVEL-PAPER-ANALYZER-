"""Importing this package registers every model with SQLAlchemy.

ALL_MODELS is the registry the generic admin CRUD blueprint iterates over.
"""
from .analytics import BacktestResult, Prediction, PredictionReason, PredictionRun, TopicStat
from .exam import (
    ExamBoard,
    ExamSession,
    GradeThreshold,
    PaperComponent,
    PaperVariant,
    Qualification,
    Subject,
    SyllabusVersion,
)
from .identity import Role, School, User, UserProfile, UserRole
from .papers import (
    ExtractionRun,
    MarkScheme,
    Paper,
    PaperFile,
    PaperPage,
    PaperReview,
    PaperSection,
    UploadBatch,
)
from .questions import (
    CommandWord,
    Question,
    QuestionAnswer,
    QuestionFlag,
    QuestionOption,
    QuestionPart,
    QuestionSimilarity,
    QuestionTopic,
    QuestionType,
    question_command_words,
)
from .student import Bookmark, Notification, PredictionFeedback, StudyPlan, StudyPlanItem
from .syllabus import LearningObjective, Topic, TopicKeyword, TopicPrerequisite, Unit
from .system import AppSetting, AuditLog

ALL_MODELS = [
    # identity (5)
    School, Role, User, UserRole, UserProfile,
    # exam framework (8)
    ExamBoard, Qualification, Subject, SyllabusVersion, ExamSession,
    PaperComponent, PaperVariant, GradeThreshold,
    # syllabus (5)
    Unit, Topic, TopicKeyword, TopicPrerequisite, LearningObjective,
    # papers (8)
    UploadBatch, Paper, PaperFile, PaperPage, PaperSection, ExtractionRun, PaperReview, MarkScheme,
    # questions (9 + 1 association table)
    QuestionType, CommandWord, Question, QuestionPart, QuestionOption, QuestionAnswer,
    QuestionTopic, QuestionSimilarity, QuestionFlag,
    # analytics (5)
    TopicStat, PredictionRun, Prediction, PredictionReason, BacktestResult,
    # student (5)
    StudyPlan, StudyPlanItem, Bookmark, PredictionFeedback, Notification,
    # system (2)
    AuditLog, AppSetting,
]

ASSOCIATION_TABLES = [question_command_words]
