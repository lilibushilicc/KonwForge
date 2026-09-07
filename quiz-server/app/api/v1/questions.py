from typing import Annotated

from fastapi import APIRouter, Query

from app.core.deps import DbSession, Paging
from app.schemas.common import OkResponse, Page
from app.schemas.enums import OrderBy, QuestionStatus, QuestionType
from app.schemas.question import (
    BatchRequest,
    BatchResult,
    QuestionCreate,
    QuestionListQuery,
    QuestionOut,
    QuestionUpdate,
)
from app.services import question_service

router = APIRouter(prefix="/questions", tags=["questions"])


@router.get("", response_model=Page[QuestionOut], summary="题目分页列表")
def list_questions(
    db: DbSession,
    paging: Paging,
    keyword: Annotated[str | None, Query(description="编号或题干模糊匹配")] = None,
    code: Annotated[str | None, Query(description="按唯一编号精确查询")] = None,
    type: Annotated[list[QuestionType] | None, Query(description="题型，可多选")] = None,
    category_id: Annotated[int | None, Query(description="分类 id，含全部子分类")] = None,
    tag_ids: Annotated[list[int] | None, Query(description="标签 id，需同时命中")] = None,
    difficulty: Annotated[list[int] | None, Query(description="难度 1..5，可多选")] = None,
    status: Annotated[QuestionStatus | None, Query(description="默认 active")] = None,
    order_by: Annotated[OrderBy, Query()] = OrderBy.created_at,
    desc: Annotated[bool, Query()] = True,
):
    query = QuestionListQuery(
        keyword=keyword,
        code=code,
        types=type,
        category_id=category_id,
        tag_ids=tag_ids,
        difficulties=difficulty,
        status=status,
        order_by=order_by,
        desc=desc,
    )
    items, total = question_service.list_questions(db, query, paging.offset, paging.limit)
    return Page[QuestionOut](
        items=[to_out(q) for q in items],
        total=total,
        page=paging.page,
        page_size=paging.page_size,
    )


@router.post("", response_model=QuestionOut, status_code=201, summary="新建题目")
def create_question(db: DbSession, data: QuestionCreate):
    return to_out(question_service.create_question(db, data))


@router.get("/{question_id}", response_model=QuestionOut, summary="题目详情")
def get_question(db: DbSession, question_id: int):
    return to_out(question_service.get_question(db, question_id))


@router.patch("/{question_id}", response_model=QuestionOut, summary="局部更新题目")
def update_question(db: DbSession, question_id: int, data: QuestionUpdate):
    return to_out(question_service.update_question(db, question_id, data))


@router.delete("/{question_id}", response_model=OkResponse, summary="软删除（归档）")
def delete_question(db: DbSession, question_id: int):
    question_service.soft_delete_question(db, question_id)
    return OkResponse()


@router.delete("/{question_id}/hard", response_model=OkResponse, summary="物理删除（级联作答记录）")
def hard_delete_question(db: DbSession, question_id: int):
    question_service.hard_delete_question(db, question_id)
    return OkResponse()


@router.post("/batch", response_model=BatchResult, summary="批量操作")
def batch_update(db: DbSession, req: BatchRequest):
    affected = question_service.batch_update(db, req)
    return BatchResult(action=req.action, affected=affected)


def to_out(q) -> QuestionOut:
    """ORM → 出参：补上分类名、标签名与统计。"""
    return QuestionOut(
        id=q.id,
        code=q.code,
        type=q.type,
        stem=q.stem,
        analysis=q.analysis,
        difficulty=q.difficulty,
        category_id=q.category_id,
        category_name=q.category.name if q.category else None,
        tags=[t.name for t in q.tags],
        payload=q.payload or {},
        answer=q.answer or {},
        judge_config=q.judge_config or {},
        status=q.status,
        source=q.source,
        version=q.version,
        created_at=q.created_at,
        updated_at=q.updated_at,
        stat=q.stat,
    )
