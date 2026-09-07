"""错题本（M4）服务。读错题 + 软删/标记掌握/加备注。"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.mistake import Mistake
from app.models.question import Question
from app.schemas.mistake import MistakeListQuery, MistakeUpdate


def list_mistakes(db: Session, q: MistakeListQuery, page=1, page_size=50):
    """返回 (Mistake 列表, total)。结果带上 question 摘要。"""
    stmt = select(Mistake)
    if q.removed is not None:
        stmt = stmt.where(Mistake.removed == q.removed)
    else:
        stmt = stmt.where(Mistake.removed == False)  # 默认只看未移除
    if q.mastered is not None:
        stmt = stmt.where(Mistake.mastered == q.mastered)
    if q.only_wrong:
        stmt = stmt.where(Mistake.wrong_count > Mistake.cleared_count)

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0

    # 拉出题目做实过滤（keyword / 题型 / 分类）
    rows = db.scalars(
        stmt.order_by(Mistake.last_wrong_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    if q.keyword or q.types or q.category_id is not None:
        filtered = []
        for m in rows:
            qn = db.get(Question, m.question_id)
            if qn is None:
                continue
            if q.keyword and q.keyword not in (qn.stem or ""):
                continue
            if q.types:
                tset = {t.value if hasattr(t, "value") else t for t in q.types}
                if qn.type not in tset:
                    continue
            if q.category_id is not None and qn.category_id != q.category_id:
                continue
            filtered.append(m)
        return filtered, total
    return list(rows), total


def update_mistake(db: Session, question_id: int, data: MistakeUpdate) -> Mistake | None:
    m = db.scalar(select(Mistake).where(Mistake.question_id == question_id))
    if m is None:
        return None
    if data.mastered is not None:
        m.mastered = data.mastered
    if data.removed is not None:
        m.removed = data.removed
    if data.note is not None:
        m.note = data.note
    db.commit()
    db.refresh(m)
    return m


def count_active(db: Session) -> int:
    return db.scalar(select(func.count()).select_from(Mistake).where(Mistake.removed == False)) or 0
