from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.common import ORMBase
from app.schemas.enums import BatchAction, OrderBy, QuestionStatus, QuestionType


class QuestionStatOut(ORMBase):
    question_id: int
    attempt_count: int = 0
    wrong_count: int = 0
    last_attempt_at: datetime | None = None
    last_result: int | None = None
    mastery: int = 0
    streak: int = 0


class QuestionBase(BaseModel):
    type: QuestionType
    stem: str = Field(min_length=1)
    analysis: str | None = None
    difficulty: int = Field(default=3, ge=1, le=5)
    category_id: int | None = None
    tags: list[str] = Field(default_factory=list)
    payload: dict[str, Any] = Field(default_factory=dict)
    answer: dict[str, Any] = Field(default_factory=dict)
    judge_config: dict[str, Any] = Field(default_factory=dict)
    source: str | None = Field(default=None, max_length=128)

    @field_validator("tags")
    @classmethod
    def _strip_tags(cls, v: list[str]) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for t in v:
            t = t.strip()
            if t and t not in seen:
                seen.add(t)
                out.append(t)
        return out


class QuestionCreate(QuestionBase):
    pass


class QuestionUpdate(BaseModel):
    """局部更新；payload/answer/judge_config 任一变更都会让 version + 1。"""

    type: QuestionType | None = None
    stem: str | None = Field(default=None, min_length=1)
    analysis: str | None = None
    difficulty: int | None = Field(default=None, ge=1, le=5)
    category_id: int | None = None
    tags: list[str] | None = None
    payload: dict[str, Any] | None = None
    answer: dict[str, Any] | None = None
    judge_config: dict[str, Any] | None = None
    status: QuestionStatus | None = None
    source: str | None = Field(default=None, max_length=128)


class QuestionOut(ORMBase):
    id: int
    code: str
    type: QuestionType
    stem: str
    analysis: str | None = None
    difficulty: int
    category_id: int | None = None
    category_name: str | None = None
    tags: list[str] = Field(default_factory=list)
    payload: dict[str, Any] = Field(default_factory=dict)
    answer: dict[str, Any] = Field(default_factory=dict)
    judge_config: dict[str, Any] = Field(default_factory=dict)
    status: QuestionStatus
    source: str | None = None
    version: int
    created_at: datetime
    updated_at: datetime
    stat: QuestionStatOut | None = None


class QuestionListQuery(BaseModel):
    """题库筛选条件；由 api 层从 query 参数装配。"""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    keyword: str | None = None
    code: str | None = None
    types: list[QuestionType] | None = None
    category_id: int | None = None
    tag_ids: list[int] | None = None
    difficulties: list[int] | None = None
    status: QuestionStatus | None = None
    order_by: OrderBy = OrderBy.created_at
    desc: bool = True


class BatchRequest(BaseModel):
    action: BatchAction
    ids: list[int] = Field(min_length=1)
    payload: dict[str, Any] = Field(default_factory=dict)


class BatchResult(BaseModel):
    action: BatchAction
    affected: int
