"""判分 API，见 DESIGN §4.4。

- POST /judge/preview   客观题/全部题型即时判分，不写库（练习模式"做一题判一题"）
- POST /judge/essay/self 简答自评，返回是否需复习（落库随 M4 会话 / M5 错题本统一执行）
"""

from __future__ import annotations

from fastapi import APIRouter

from app.core.deps import DbSession
from app.judging.registry import judge as do_judge
from app.schemas.judge import (
    EssaySelfEvalOut,
    EssaySelfEvalRequest,
    JudgeRequest,
    JudgeResultOut,
)
from app.services import question_service

router = APIRouter(prefix="/judge", tags=["judge"])


@router.post("/preview", response_model=JudgeResultOut, summary="即时判分（不写库）")
def judge_preview(db: DbSession, req: JudgeRequest):
    q = question_service.get_question(db, req.question_id)
    result = do_judge(
        q.type,
        payload=q.payload or {},
        answer=q.answer or {},
        config=q.judge_config or {},
        response=req.response or {},
        max_score=req.max_score,
    )
    return JudgeResultOut(
        is_correct=result.is_correct,
        score=result.score,
        max_score=result.max_score,
        detail=result.detail,
        feedback=result.feedback,
        need_manual=result.need_manual,
    )


@router.post("/essay/self", response_model=EssaySelfEvalOut, summary="简答自评（不计分）")
def essay_self_eval(_db: DbSession, req: EssaySelfEvalRequest):
    # mastered → 无需复习；fuzzy / unknown → 需复习（错题本入库随 M4/M5 会话提交统一执行）
    need_review = req.level in {"fuzzy", "unknown"}
    return EssaySelfEvalOut(level=req.level, need_review=need_review)
