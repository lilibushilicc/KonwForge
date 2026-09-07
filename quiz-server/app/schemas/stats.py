"""统计（M5）聚合出参，见 DESIGN §5.4。

全部为只读聚合，不写库。数据来源：question_stat（掌握度/作答）、attempt（活动）、
mistake（错题）、practice_session（会话）。前端用这些字段渲染总览卡与各类图表。
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class StatsSummary(BaseModel):
    total_questions: int = 0
    total_attempts: int = 0
    total_sessions: int = 0
    total_mistakes: int = 0  # 历史错题（含已移除）
    active_mistakes: int = 0  # 当前仍未移除
    overall_accuracy: float | None = None
    avg_mastery: float | None = None
    mastered_count: int = 0  # mastery>=4
    learning_count: int = 0  # 1<=mastery<4
    new_count: int = 0  # mastery==0


class TypeAccuracy(BaseModel):
    type: str
    label: str
    attempted: int = 0
    correct: int = 0
    accuracy: float = 0.0


class CategoryAccuracy(BaseModel):
    category_id: int
    name: str
    question_count: int = 0
    attempted: int = 0
    correct: int = 0
    accuracy: float = 0.0


class MasteryBucket(BaseModel):
    level: int  # 0..5
    count: int = 0


class DailyActivity(BaseModel):
    date: str  # YYYY-MM-DD
    attempts: int = 0
    correct: int = 0


class StatsOut(BaseModel):
    summary: StatsSummary
    by_type: list[TypeAccuracy] = Field(default_factory=list)
    by_category: list[CategoryAccuracy] = Field(default_factory=list)
    mastery: list[MasteryBucket] = Field(default_factory=list)
    daily: list[DailyActivity] = Field(default_factory=list)
