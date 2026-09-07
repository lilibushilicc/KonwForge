
from pydantic import BaseModel, Field

from app.schemas.common import ORMBase


class TagCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    color: str | None = Field(default=None, max_length=16)


class TagUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=64)
    color: str | None = Field(default=None, max_length=16)


class TagOut(ORMBase):
    id: int
    name: str
    color: str | None = None
    question_count: int = 0
