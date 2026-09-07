from fastapi import APIRouter

from app.core.deps import DbSession
from app.schemas.category import CategoryCreate, CategoryOut, CategoryUpdate
from app.schemas.common import OkResponse
from app.services import question_service

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=list[CategoryOut], summary="分类树（扁平，含 parent_id）")
def list_categories(db: DbSession):
    return question_service.list_categories(db)


@router.post("", response_model=CategoryOut, status_code=201, summary="新建分类")
def create_category(db: DbSession, data: CategoryCreate):
    return question_service.create_category(db, **data.model_dump())


@router.patch("/{category_id}", response_model=CategoryOut, summary="更新分类")
def update_category(db: DbSession, category_id: int, data: CategoryUpdate):
    payload = data.model_dump(exclude_unset=True)
    return question_service.update_category(db, category_id, **payload)


@router.delete("/{category_id}", response_model=OkResponse, summary="删除分类（子分类上提一级）")
def delete_category(db: DbSession, category_id: int):
    question_service.delete_category(db, category_id)
    return OkResponse()
