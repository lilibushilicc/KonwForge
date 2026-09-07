from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from .question import Question


class Mistake(Base):
    """错题本：一道题一条（UNIQUE question_id），removed 为软删。"""

    __tablename__ = "mistake"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    question_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("question.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    first_wrong_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    last_wrong_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    wrong_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    cleared_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    mastered: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    removed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    question: Mapped["Question"] = relationship("Question", back_populates="mistakes")
