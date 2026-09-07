from datetime import datetime

from sqlalchemy import JSON, DateTime, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class PracticeSession(Base):
    """练习会话。elapsed_sec 为服务端权威累计用时（客户端暂停时上报累加）。"""

    __tablename__ = "practice_session"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    title: Mapped[str | None] = mapped_column(String(128), nullable=True)
    mode: Mapped[str] = mapped_column(String(16), nullable=False)  # practice|exam|mistake
    status: Mapped[str] = mapped_column(
        String(16), nullable=False
    )  # active|paused|submitted|abandoned
    total_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duration_limit_sec: Mapped[int | None] = mapped_column(Integer, nullable=True)
    elapsed_sec: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    question_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    filter_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_active_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    score: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    correct_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    accuracy: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)

    items: Mapped[list["SessionItem"]] = relationship(
        "SessionItem",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="SessionItem.seq",
    )
    attempts: Mapped[list["Attempt"]] = relationship(
        "Attempt", back_populates="session", cascade="all, delete-orphan"
    )
