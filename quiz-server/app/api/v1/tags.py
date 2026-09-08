from fastapi import APIRouter

from app.core import cache
from app.core.deps import DbSession
from app.schemas.common import OkResponse
from app.schemas.tag import TagCreate, TagOut, TagUpdate
from app.services import question_service

router = APIRouter(prefix="/tags", tags=["tags"])


@router.get("", response_model=list[TagOut], summary="标签列表（含题目引用数）")
@cache.cached("tags")
def list_tags(db: DbSession):
    tags = question_service.list_tags(db)
    counts = question_service.tag_question_counts(db)
    return [
        TagOut(id=t.id, name=t.name, color=t.color, question_count=counts.get(t.id, 0))
        for t in tags
    ]


@router.post("", response_model=TagOut, status_code=201, summary="新建标签")
def create_tag(db: DbSession, data: TagCreate):
    tag = question_service.create_tag(db, **data.model_dump())
    return TagOut(id=tag.id, name=tag.name, color=tag.color, question_count=0)


@router.patch("/{tag_id}", response_model=TagOut, summary="更新标签（重命名 / 颜色）")
def update_tag(db: DbSession, tag_id: int, data: TagUpdate):
    tag = question_service.update_tag(db, tag_id, **data.model_dump(exclude_unset=True))
    counts = question_service.tag_question_counts(db)
    return TagOut(id=tag.id, name=tag.name, color=tag.color, question_count=counts.get(tag.id, 0))


@router.delete("/{tag_id}", response_model=OkResponse, summary="删除标签")
def delete_tag(db: DbSession, tag_id: int):
    question_service.delete_tag(db, tag_id)
    return OkResponse()
