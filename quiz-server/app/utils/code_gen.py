"""业务编号生成：Q-2026-000123 / S-2026-000001。

同一前缀取当前最大序号 + 1，删除后序号不复用（足够个人量级，且不依赖数据库序列）。
"""

from datetime import datetime
from typing import TypeVar

from sqlalchemy import desc, func
from sqlalchemy.orm import Session

M = TypeVar("M")


def next_code(db: Session, model: type[M], prefix: str, column: str = "code") -> str:
    year = datetime.now().year
    pattern = f"{prefix}-{year}-%"
    col = getattr(model, column)
    last = db.query(col).filter(col.like(pattern)).order_by(desc(col)).limit(1).scalar()
    seq = 1
    if last:
        try:
            seq = int(str(last).rsplit("-", 1)[-1]) + 1
        except ValueError:
            seq = 1
    return f"{prefix}-{year}-{seq:06d}"


def total_by_prefix(db: Session, model: type[M], prefix: str, column: str = "code") -> int:
    """用于统计：某个前缀下已生成多少个编号。"""
    col = getattr(model, column)
    return db.query(func.count(col)).filter(col.like(f"{prefix}-%")).scalar() or 0
