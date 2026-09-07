from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from .question import Question


class Category(Base, TimestampMixin):
    """多级分类树。"""

    __tablename__ = "category"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    parent_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("category.id", ondelete="SET NULL"), nullable=True
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    parent: Mapped[Optional["Category"]] = relationship(
        "Category", remote_side="Category.id", back_populates="children"
    )
    # 不用 delete-orphan：删除父分类时子分类上提一级（与 DDL 的 ON DELETE SET NULL 一致）
    children: Mapped[list["Category"]] = relationship("Category", back_populates="parent")
    questions: Mapped[list["Question"]] = relationship("Question", back_populates="category")
