"""练习会话（M3）相关入参/出参，见 DESIGN §5。

数据流：建会话（按筛选抽题）→ 逐题作答（即时判分、写 attempt/stat/mistake）
→ 交卷（汇总分数/正确率）。出参刻意把题干与选项（payload）和答案（answer）
分离：未作答前前端只拿到题目，作答后才在 reveal 里返回答案与解析。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.common import ORMBase
from app.schemas.enums import QuestionType, SessionMode, SessionStatus


class SessionFilter(BaseModel):
    """抽题筛选条件。"""

    category_ids: list[int] = Field(default_factory=list)
    types: list[QuestionType] = Field(default_factory=list)
    difficulties: list[int] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class PracticeSessionCreate(BaseModel):
    mode: SessionMode = SessionMode.practice
    title: str | None = Field(default=None, max_length=128)
    count: int = Field(default=20, ge=1, le=200)
    duration_limit_sec: int | None = Field(default=None, gt=0)
    filter: SessionFilter = Field(default_factory=SessionFilter)


class QuestionPlayOut(ORMBase):
    """题干展示用，刻意不含 answer / analysis / judge_config。"""

    id: int
    code: str
    type: QuestionType
    stem: str
    difficulty: int
    category_id: int | None = None
    category_name: str | None = None
    tags: list[str] = Field(default_factory=list)
    payload: dict[str, Any] = Field(default_factory=dict)
    status: str
    source: str | None = None
    version: int
    created_at: datetime
    updated_at: datetime


class SessionItemOut(ORMBase):
    id: int
    session_id: int
    question_id: int
    seq: int
    score_weight: float = 1.0
    flagged: bool = False
    answered: bool = False
    is_correct: bool | None = None
    score: float | None = None
    spent_sec: int = 0
    question: QuestionPlayOut
    # 作答后揭示：答案 + 解析 + 判分细节
    reveal: dict[str, Any] | None = None


class PracticeSessionOut(ORMBase):
    id: int
    code: str
    title: str | None = None
    mode: SessionMode
    status: SessionStatus
    total_count: int = 0
    duration_limit_sec: int | None = None
    elapsed_sec: int = 0
    started_at: datetime | None = None
    last_active_at: datetime | None = None
    submitted_at: datetime | None = None
    score: float | None = None
    correct_count: int | None = None
    accuracy: float | None = None
    items: list[SessionItemOut] = Field(default_factory=list)


class PracticeSessionListItem(ORMBase):
    id: int
    code: str
    title: str | None = None
    mode: SessionMode
    status: SessionStatus
    total_count: int = 0
    correct_count: int | None = None
    accuracy: float | None = None
    started_at: datetime | None = None
    submitted_at: datetime | None = None


class AnswerSubmit(BaseModel):
    """一次作答。客观题只需 response；简答需带 self_eval 自评。"""

    item_id: int
    response: dict[str, Any] = Field(default_factory=dict)
    duration_sec: int | None = Field(default=None, ge=0)
    self_eval: str | None = Field(default=None, pattern="^(mastered|fuzzy|unknown)$")


class AnswerBatch(BaseModel):
    """整卷批量作答：一组作答一次性提交（考试模式交卷用）。"""

    items: list[AnswerSubmit] = Field(default_factory=list)


class AnswerResult(BaseModel):
    item_id: int
    is_correct: bool | None = None
    correct: bool = False
    score: float = 0.0
    max_score: float = 1.0
    judge_detail: dict[str, Any] = Field(default_factory=dict)
    need_manual: bool = False
    feedback: str | None = None
    reveal: dict[str, Any] = Field(default_factory=dict)
    progress: dict[str, Any] = Field(default_factory=dict)


class SessionSubmitResult(BaseModel):
    id: int
    status: SessionStatus
    score: float | None = None
    correct_count: int = 0
    accuracy: float | None = None
    total_count: int = 0
    elapsed_sec: int = 0


class SessionPatch(BaseModel):
    """暂停/恢复、累加用时。"""

    status: SessionStatus | None = None
    elapsed_sec: int | None = Field(default=None, ge=0)
