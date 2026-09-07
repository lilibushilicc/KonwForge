"""题目 / 分类 / 标签的业务编排，事务边界在这一层。"""

from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import ConflictError, NotFoundError
from app.models.category import Category
from app.models.question import Question, QuestionStat
from app.models.tag import Tag, question_tag
from app.schemas.enums import BatchAction, QuestionStatus
from app.schemas.question import (
    BatchRequest,
    QuestionCreate,
    QuestionListQuery,
    QuestionUpdate,
)
from app.utils.code_gen import next_code

# --------------------------------------------------------------------------- #
# 查询
# --------------------------------------------------------------------------- #


def _apply_filters(stmt, q: QuestionListQuery, db: Session):
    if q.keyword:
        kw = f"%{q.keyword}%"
        stmt = stmt.where(or_(Question.stem.like(kw), Question.code.like(kw)))
    if q.code:
        stmt = stmt.where(Question.code == q.code)
    if q.types:
        stmt = stmt.where(Question.type.in_([t.value for t in q.types]))
    if q.difficulties:
        stmt = stmt.where(Question.difficulty.in_(q.difficulties))
    if q.status:
        stmt = stmt.where(Question.status == q.status.value)
    else:
        # 默认只看有效题，archived 需显式指定
        stmt = stmt.where(Question.status == QuestionStatus.active.value)
    if q.category_id:
        ids = collect_category_ids(db, q.category_id)
        stmt = stmt.where(Question.category_id.in_(ids))
    if q.tag_ids:
        # 需同时含全部标签（AND 语义）
        for tid in q.tag_ids:
            stmt = stmt.where(Question.tags.any(Tag.id == tid))

    return stmt


def list_questions(
    db: Session, q: QuestionListQuery, offset: int, limit: int
) -> tuple[list[Question], int]:
    total = db.scalar(_apply_filters(select(func.count(Question.id)), q, db)) or 0

    order_col = {
        "created_at": Question.created_at,
        "updated_at": Question.updated_at,
        "difficulty": Question.difficulty,
        "code": Question.code,
    }[q.order_by.value]
    stmt = _apply_filters(
        select(Question).options(selectinload(Question.tags), selectinload(Question.stat)), q, db
    )
    stmt = stmt.order_by(order_col.desc() if q.desc else order_col.asc())
    items = list(db.scalars(stmt.offset(offset).limit(limit)).unique())
    return items, total


def get_question(db: Session, question_id: int) -> Question:
    q = db.get(Question, question_id)
    if q is None:
        raise NotFoundError(f"题目 {question_id} 不存在")
    return q


def get_question_by_code(db: Session, code: str) -> Question:
    q = db.scalar(select(Question).where(Question.code == code))
    if q is None:
        raise NotFoundError(f"题目 {code} 不存在")
    return q


# --------------------------------------------------------------------------- #
# 写入
# --------------------------------------------------------------------------- #


def _sync_tags(db: Session, question: Question, names: list[str] | None) -> None:
    if names is None:
        return
    tags = [get_or_create_tag(db, n) for n in names]
    question.tags = tags


def create_question(db: Session, data: QuestionCreate) -> Question:
    if data.category_id is not None and db.get(Category, data.category_id) is None:
        raise NotFoundError(f"分类 {data.category_id} 不存在")

    question = Question(
        code=next_code(db, Question, "Q"),
        type=data.type.value,
        stem=data.stem,
        analysis=data.analysis,
        difficulty=data.difficulty,
        category_id=data.category_id,
        payload=data.payload,
        answer=data.answer,
        judge_config=data.judge_config,
        status=QuestionStatus.active.value,
        source=data.source,
        version=1,
        stat=QuestionStat(),
    )
    db.add(question)
    db.flush()
    _sync_tags(db, question, data.tags)
    db.commit()
    db.refresh(question)
    return question


def update_question(db: Session, question_id: int, data: QuestionUpdate) -> Question:
    question = get_question(db, question_id)

    payload_fields = {"payload", "answer", "judge_config", "type", "stem"}
    changed = data.model_dump(exclude_unset=True, exclude={"tags"})
    touches_payload = bool(payload_fields & changed.keys())

    if "category_id" in changed and changed["category_id"] is not None:
        if db.get(Category, changed["category_id"]) is None:
            raise NotFoundError(f"分类 {changed['category_id']} 不存在")

    for field, value in changed.items():
        if field == "status" and value is not None or field == "type" and value is not None:
            setattr(question, field, value.value)
        else:
            setattr(question, field, value)

    if touches_payload:
        question.version += 1

    _sync_tags(db, question, data.tags)
    db.commit()
    db.refresh(question)
    return question


def soft_delete_question(db: Session, question_id: int) -> None:
    question = get_question(db, question_id)
    question.status = QuestionStatus.archived.value
    db.commit()


def hard_delete_question(db: Session, question_id: int) -> None:
    question = get_question(db, question_id)
    db.delete(question)
    db.commit()


def batch_update(db: Session, req: BatchRequest) -> int:
    """批量操作返回受影响行数。"""
    if req.action == BatchAction.delete:
        rows = (
            db.query(Question)
            .filter(Question.id.in_(req.ids))
            .update({Question.status: QuestionStatus.archived.value}, synchronize_session=False)
        )
    elif req.action == BatchAction.set_category:
        cid = req.payload.get("category_id")
        if cid is not None and db.get(Category, cid) is None:
            raise NotFoundError(f"分类 {cid} 不存在")
        rows = (
            db.query(Question)
            .filter(Question.id.in_(req.ids))
            .update({Question.category_id: cid}, synchronize_session=False)
        )
    elif req.action == BatchAction.set_difficulty:
        difficulty = int(req.payload.get("difficulty", 3))
        if not 1 <= difficulty <= 5:
            raise ConflictError("difficulty 必须在 1..5 之间")
        rows = (
            db.query(Question)
            .filter(Question.id.in_(req.ids))
            .update({Question.difficulty: difficulty}, synchronize_session=False)
        )
    elif req.action == BatchAction.add_tags:
        names: list[str] = list(req.payload.get("tags") or [])
        if not names:
            return 0
        tags = [get_or_create_tag(db, n) for n in names]
        questions = list(db.scalars(select(Question).where(Question.id.in_(req.ids))))
        for q in questions:
            existing = {t.name for t in q.tags}
            q.tags.extend(t for t in tags if t.name not in existing)
        rows = len(questions)
    else:  # pragma: no cover - 枚举穷尽
        raise ConflictError(f"不支持的批量操作 {req.action}")

    db.commit()
    return rows


# --------------------------------------------------------------------------- #
# 分类 / 标签
# --------------------------------------------------------------------------- #


def collect_category_ids(db: Session, root_id: int) -> list[int]:
    """取某分类及其全部子孙 id（题库筛选「含子分类」）。"""
    ids: list[int] = []
    stack = [root_id]
    while stack:
        cur = stack.pop()
        if cur in ids:
            continue
        ids.append(cur)
        children = db.scalars(select(Category.id).where(Category.parent_id == cur)).all()
        stack.extend(children)
    return ids


def list_categories(db: Session) -> list[Category]:
    return list(db.scalars(select(Category).order_by(Category.sort_order, Category.id)))


def create_category(db: Session, **data: Any) -> Category:
    parent_id = data.get("parent_id")
    if parent_id is not None and db.get(Category, parent_id) is None:
        raise NotFoundError(f"父分类 {parent_id} 不存在")
    category = Category(**data)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def update_category(db: Session, category_id: int, **data: Any) -> Category:
    category = db.get(Category, category_id)
    if category is None:
        raise NotFoundError(f"分类 {category_id} 不存在")
    new_parent = data.get("parent_id")
    if new_parent is not None:
        if db.get(Category, new_parent) is None:
            raise NotFoundError(f"父分类 {new_parent} 不存在")
        if new_parent == category_id or new_parent in collect_category_ids(db, category_id):
            raise ConflictError("不能把分类挂到自己的子孙下")
    for k, v in data.items():
        setattr(category, k, v)
    db.commit()
    db.refresh(category)
    return category


def delete_category(db: Session, category_id: int) -> None:
    """删除分类：子分类提升一级，题目 category_id 置空。"""
    category = db.get(Category, category_id)
    if category is None:
        raise NotFoundError(f"分类 {category_id} 不存在")
    grandparent = category.parent_id
    for child in category.children:
        child.parent_id = grandparent
    db.flush()
    db.query(Question).filter(Question.category_id == category_id).update(
        {Question.category_id: None}, synchronize_session=False
    )
    db.delete(category)
    db.commit()


def list_tags(db: Session) -> list[Tag]:
    return list(db.scalars(select(Tag).order_by(Tag.name)))


def tag_question_counts(db: Session) -> dict[int, int]:
    """每个标签当前挂着的题目数（active + archived），用于设置页展示。"""
    rows = db.execute(
        select(question_tag.c.tag_id, func.count())
        .select_from(question_tag)
        .group_by(question_tag.c.tag_id)
    ).all()
    return {tag_id: count for tag_id, count in rows}


def get_or_create_tag(db: Session, name: str, color: str | None = None) -> Tag:
    name = name.strip()
    tag = db.scalar(select(Tag).where(Tag.name == name))
    if tag is None:
        tag = Tag(name=name, color=color)
        db.add(tag)
        db.flush()
    return tag


def create_tag(db: Session, **data: Any) -> Tag:
    if db.scalar(select(Tag).where(Tag.name == data["name"])) is not None:
        raise ConflictError(f"标签 {data['name']} 已存在")
    tag = Tag(**data)
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return tag


def update_tag(db: Session, tag_id: int, **data: Any) -> Tag:
    tag = db.get(Tag, tag_id)
    if tag is None:
        raise NotFoundError(f"标签 {tag_id} 不存在")
    new_name = data.get("name")
    if new_name is not None and new_name != tag.name:
        if db.scalar(select(Tag).where(Tag.name == new_name)) is not None:
            raise ConflictError(f"标签 {new_name} 已存在")
        tag.name = new_name
    if "color" in data:
        tag.color = data["color"]
    db.commit()
    db.refresh(tag)
    return tag


def delete_tag(db: Session, tag_id: int) -> None:
    tag = db.get(Tag, tag_id)
    if tag is None:
        raise NotFoundError(f"标签 {tag_id} 不存在")
    db.delete(tag)  # question_tag 由级联清理
    db.commit()
