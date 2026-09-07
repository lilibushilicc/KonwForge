from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from .attempt import Attempt
    from .mistake import Mistake
    from .session_item import SessionItem

from .category import Category
from .tag import Tag, question_tag


class Question(Base, TimestampMixin):
    """题目主表：公共列（可检索/可索引） + JSON 载荷（题型专属）。

    payload / answer / judge_config 三列让新增题型不必改表，
    具体结构见 DESIGN §3.3 与 app/question_types/defs/*.py。
    """

    __tablename__ = "question"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    stem: Mapped[str] = mapped_column(Text, nullable=False)
    analysis: Mapped[str | None] = mapped_column(Text, nullable=True)
    difficulty: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=3, index=True)
    category_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("category.id", ondelete="SET NULL"), nullable=True, index=True
    )
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    answer: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    judge_config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active", index=True)
    source: Mapped[str | None] = mapped_column(String(128), nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    category: Mapped[Optional["Category"]] = relationship("Category", back_populates="questions")
    tags: Mapped[list["Tag"]] = relationship(
        "Tag", secondary=question_tag, back_populates="questions"
    )
    stat: Mapped[Optional["QuestionStat"]] = relationship(
        "QuestionStat",
        back_populates="question",
        uselist=False,
        cascade="all, delete-orphan",
    )
    mistakes: Mapped[list["Mistake"]] = relationship(
        "Mistake", back_populates="question", cascade="all, delete-orphan"
    )
    session_items: Mapped[list["SessionItem"]] = relationship(
        "SessionItem", back_populates="question", cascade="all, delete-orphan"
    )
    attempts: Mapped[list["Attempt"]] = relationship(
        "Attempt", back_populates="question", cascade="all, delete-orphan"
    )


class QuestionStat(Base):
    """题目冗余统计：掌握度 / SRS 调度 / 错题重做排序。"""

    __tablename__ = "question_stat"

    question_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("question.id", ondelete="CASCADE"), primary_key=True
    )
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    wrong_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_result: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)  # 0 错 / 1 对
    mastery: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    streak: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    question: Mapped["Question"] = relationship("Question", back_populates="stat")
