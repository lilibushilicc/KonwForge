"""判分相关入参/出参 schema，见 DESIGN §4.4。"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class JudgeRequest(BaseModel):
    """/judge/preview 入参：按题目 id 即时判分（不写库）。"""

    question_id: int
    response: dict[str, Any] = Field(default_factory=dict)
    max_score: float = 1.0


class JudgeResultOut(BaseModel):
    is_correct: bool | None = None
    score: float
    max_score: float
    detail: dict[str, Any] = Field(default_factory=dict)
    feedback: str | None = None
    need_manual: bool = False


class EssaySelfEvalRequest(BaseModel):
    """简答自评：记录但不计入分数。"""

    question_id: int
    response: dict[str, Any] = Field(default_factory=dict)
    level: str = Field(pattern="^(mastered|fuzzy|unknown)$")


class EssaySelfEvalOut(BaseModel):
    level: str
    need_review: bool  # unknown / fuzzy → 需复习（入错题本由 M5 落库）
