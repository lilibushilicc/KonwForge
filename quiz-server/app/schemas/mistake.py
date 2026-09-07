"""错题本（M4）相关入参/出参，见 DESIGN §5.3。"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import ORMBase
from app.schemas.enums import QuestionType


class QuestionBriefOut(ORMBase):
    """错题列表里轻量展示题目信息。"""

    id: int
    code: str
    type: QuestionType
    stem: str
    difficulty: int
    category_id: int | None = None
    category_name: str | None = None
    tags: list[str] = Field(default_factory=list)


class MistakeOut(ORMBase):
    id: int
    question_id: int
    first_wrong_at: datetime
    last_wrong_at: datetime
    wrong_count: int = 1
    cleared_count: int = 0
    mastered: bool = False
    removed: bool = False
    note: str | None = None
    question: QuestionBriefOut


class MistakeUpdate(BaseModel):
    mastered: bool | None = None
    removed: bool | None = None
    note: str | None = Field(default=None, max_length=2000)


class MistakeListQuery(BaseModel):
    """列表筛选；由 api 层从 query 参数装配。"""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    keyword: str | None = None
    category_id: int | None = None
    types: list[QuestionType] | None = None
    mastered: bool | None = None
    removed: bool | None = False  # 默认只看未移除
    only_wrong: bool = False  # True 时只看 wrong_count>cleared_count（未掌握）
