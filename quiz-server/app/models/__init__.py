"""ORM 模型汇总导入，Alembic 与 init_db 依赖此处保证 metadata 完整。"""

from app.db.base import Base
from app.models.attempt import Attempt
from app.models.category import Category
from app.models.mistake import Mistake
from app.models.practice_session import PracticeSession
from app.models.question import Question, QuestionStat
from app.models.session_item import SessionItem
from app.models.tag import Tag, question_tag

__all__ = [
    "Attempt",
    "Base",
    "Category",
    "Mistake",
    "PracticeSession",
    "Question",
    "QuestionStat",
    "SessionItem",
    "Tag",
    "question_tag",
]
