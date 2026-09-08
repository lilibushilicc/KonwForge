"""错题本 API（M4），见 DESIGN §5.3。

- GET    /mistakes              列表（带题目摘要、筛选）
- PATCH  /mistakes/{question_id} 标记掌握 / 软删 / 加备注
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.deps import DbSession, Paging
from app.models.mistake import Mistake
from app.models.question import Question
from app.schemas.enums import QuestionType
from app.schemas.mistake import (
    MistakeListQuery,
    MistakeOut,
    MistakeUpdate,
    QuestionBriefOut,
)
from app.services import mistake_service

router = APIRouter(prefix="/mistakes", tags=["mistakes"])


def _to_out(m: Mistake, q: Question) -> MistakeOut:
    return MistakeOut(
        id=m.id,
        question_id=m.question_id,
        first_wrong_at=m.first_wrong_at,
        last_wrong_at=m.last_wrong_at,
        wrong_count=m.wrong_count,
        cleared_count=m.cleared_count,
        mastered=m.mastered,
        removed=m.removed,
        note=m.note,
        question=QuestionBriefOut(
            id=q.id,
            code=q.code,
            type=q.type,
            stem=q.stem,
            difficulty=q.difficulty,
            category_id=q.category_id,
            category_name=q.category.name if q.category else None,
            tags=[t.name for t in q.tags],
        ),
    )


@router.get("", response_model=list[MistakeOut], summary="错题列表")
def list_(
    db: DbSession,
    paging: Paging,
    keyword: str | None = None,
    category_id: int | None = None,
    type: str | None = Query(default=None, description="题型筛选"),
    mastered: bool | None = None,
    removed: bool | None = None,
    only_wrong: bool = False,
):
    query = MistakeListQuery(
        keyword=keyword,
        category_id=category_id,
        types=[QuestionType(type)] if type else None,
        mastered=mastered,
        removed=removed,
        only_wrong=only_wrong,
    )
    rows, _ = mistake_service.list_mistakes(db, query, page=paging.page, page_size=paging.limit)
    # 批量预取题目（含 category/tags），替代逐题 db.get + 懒加载
    # （每页 50 题原是 150 次往返：50 get + 50 category + 50 tags）
    qids = {m.question_id for m in rows}
    qmap: dict[int, Question] = {}
    if qids:
        qmap = {
            q.id: q
            for q in db.scalars(
                select(Question)
                .options(selectinload(Question.category), selectinload(Question.tags))
                .where(Question.id.in_(qids))
            )
            .unique()
            .all()
        }
    out = []
    for m in rows:
        q = qmap.get(m.question_id)
        if q is None:
            continue
        out.append(_to_out(m, q))
    return out


@router.patch("/{question_id}", response_model=MistakeOut, summary="标记掌握 / 软删 / 备注")
def update(db: DbSession, question_id: int, body: MistakeUpdate):
    m = mistake_service.update_mistake(db, question_id, body)
    if m is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "错题不存在")
    q = db.get(Question, m.question_id)
    return _to_out(m, q)  # type: ignore[arg-type]
