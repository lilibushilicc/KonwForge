from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from .practice_session import PracticeSession
    from .question import Question
    from .session_item import SessionItem


class Attempt(Base):
    """作答明细，append-only：一次会话内改答、错题重做都可追溯。"""

    __tablename__ = "attempt"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("practice_session.id", ondelete="CASCADE"), nullable=False, index=True
    )
    item_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("session_item.id", ondelete="CASCADE"), nullable=False
    )
    question_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("question.id"), nullable=False, index=True
    )
    response: Mapped[dict] = mapped_column(JSON, nullable=False)
    is_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    score: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    max_score: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False, default=1)
    judge_detail: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    duration_sec: Mapped[int | None] = mapped_column(Integer, nullable=True)

    session: Mapped["PracticeSession"] = relationship("PracticeSession", back_populates="attempts")
    item: Mapped["SessionItem"] = relationship("SessionItem", back_populates="attempts")
    question: Mapped["Question"] = relationship("Question", back_populates="attempts")
