from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class ORMBase(BaseModel):
    """允许从 ORM 对象直接构造（Pydantic v2 用 from_attributes）。"""

    model_config = ConfigDict(from_attributes=True)


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int


class OkResponse(BaseModel):
    """无返回体的操作（删除等）统一回 ok。"""

    ok: bool = True
