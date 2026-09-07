"""练习会话 API（M3），见 DESIGN §5。

路由约定：
- POST   /practice/sessions            建会话（按筛选抽题）
- GET    /practice/sessions            列表
- GET    /practice/sessions/{id}       详情（含逐题）
- PATCH  /practice/sessions/{id}       暂停/恢复/累加用时
- POST   /practice/sessions/{id}/answer  逐题作答（即时判分 + 写库）
- POST   /practice/sessions/{id}/submit 交卷（汇总）
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.core.deps import DbSession, Paging
from app.schemas.practice import (
    AnswerBatch,
    AnswerResult,
    AnswerSubmit,
    PracticeSessionCreate,
    PracticeSessionListItem,
    PracticeSessionOut,
    SessionPatch,
    SessionSubmitResult,
)
from app.services import practice_service

router = APIRouter(prefix="/practice", tags=["practice"])


def _get(db, sid: int) -> PracticeSessionOut:  # type: ignore[name-defined]
    sess = practice_service.get_session(db, sid)
    if sess is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "会话不存在")
    return sess


@router.post("/sessions", response_model=PracticeSessionOut, summary="建练习会话")
def create(db: DbSession, body: PracticeSessionCreate):
    sess = practice_service.create_session(db, body)
    return practice_service.build_session_out(db, sess)


@router.get("/sessions", summary="会话列表")
def list_(db: DbSession, paging: Paging, mode: str | None = None, status: str | None = None):
    from app.schemas.enums import SessionMode, SessionStatus

    m = SessionMode(mode) if mode else None
    s = SessionStatus(status) if status else None
    rows, total = practice_service.list_sessions(
        db, mode=m, status=s, page=paging.page, page_size=paging.limit
    )
    items = [PracticeSessionListItem.model_validate(r) for r in rows]
    return {"items": items, "total": total, "page": paging.page, "page_size": paging.limit}


@router.get("/sessions/{session_id}", response_model=PracticeSessionOut, summary="会话详情")
def detail(db: DbSession, session_id: int):
    sess = _get(db, session_id)
    return practice_service.build_session_out(db, sess)


@router.patch(
    "/sessions/{session_id}", response_model=PracticeSessionOut, summary="暂停/恢复/累加用时"
)
def patch_(db: DbSession, session_id: int, body: SessionPatch):
    sess = _get(db, session_id)
    from app.schemas.enums import SessionStatus

    st = SessionStatus(body.status) if body.status else None
    sess = practice_service.patch_session(db, sess, status=st, elapsed_sec=body.elapsed_sec)
    return practice_service.build_session_out(db, sess)


@router.post(
    "/sessions/{session_id}/answer", response_model=AnswerResult, summary="逐题作答（即时判分）"
)
def answer(db: DbSession, session_id: int, body: AnswerSubmit):
    sess = _get(db, session_id)
    if sess.status not in ("active", "paused"):
        raise HTTPException(status.HTTP_409_CONFLICT, "会话已结束，无法作答")
    try:
        return practice_service.answer_item(db, sess, body)
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))


@router.post(
    "/sessions/{session_id}/answer-batch", summary="整卷批量作答（考试模式交卷）"
)
def answer_batch(db: DbSession, session_id: int, body: AnswerBatch):
    sess = _get(db, session_id)
    if sess.status not in ("active", "paused"):
        raise HTTPException(status.HTTP_409_CONFLICT, "会话已结束，无法作答")
    return {"results": practice_service.answer_batch(db, sess, body.items)}


@router.post("/sessions/{session_id}/submit", response_model=SessionSubmitResult, summary="交卷")
def submit(db: DbSession, session_id: int):
    sess = _get(db, session_id)
    if sess.status == "submitted":
        raise HTTPException(status.HTTP_409_CONFLICT, "已交卷")
    return practice_service.submit_session(db, sess)
