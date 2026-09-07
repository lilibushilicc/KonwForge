from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from .attempt import Attempt
    from .practice_session import PracticeSession
    from .question import Question


class SessionItem(Base):
    """会话中的一道题（题号 = seq）。"""

    __tablename__ = "session_item"
    __table_args__ = (
        UniqueConstraint("session_id", "question_id", name="uq_item_session_question"),
        UniqueConstraint("session_id", "seq", name="uq_item_session_seq"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("practice_session.id", ondelete="CASCADE"), nullable=False
    )
    question_id: Mapped[int] = mapped_column(Integer, ForeignKey("question.id"), nullable=False)
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    score_weight: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=1)
    flagged: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    answered: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    score: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    spent_sec: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    session: Mapped["PracticeSession"] = relationship("PracticeSession", back_populates="items")
    question: Mapped["Question"] = relationship("Question", back_populates="session_items")
    attempts: Mapped[list["Attempt"]] = relationship(
        "Attempt", back_populates="item", cascade="all, delete-orphan"
    )
