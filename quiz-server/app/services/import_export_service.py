"""题库导入 / 导出。

导出支持 JSON（DESIGN §7 结构）与简化 CSV；导入按 JSON 批量校验写入。
CSV 导入暂不在 M2 范围（列存在多空/多答案歧义），见 M2 报告。
"""

import csv as csv_module
from io import StringIO

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.cache import invalidates_cache
from app.core.exceptions import ConflictError
from app.models.category import Category
from app.models.question import Question
from app.models.tag import Tag
from app.schemas.enums import QuestionStatus
from app.schemas.question import QuestionCreate
from app.utils.code_gen import next_code


def _serialize(q: Question) -> dict:
    return {
        "code": q.code,
        "type": q.type,
        "stem": q.stem,
        "analysis": q.analysis,
        "difficulty": q.difficulty,
        "category": q.category.name if q.category else None,
        "tags": [t.name for t in q.tags],
        "payload": q.payload or {},
        "answer": q.answer or {},
        "judge_config": q.judge_config or {},
        "source": q.source,
    }


def export_json(db: Session) -> dict:
    items = list(
        db.scalars(
            select(Question)
            .where(Question.status == QuestionStatus.active.value)
            .order_by(Question.created_at)
        )
    )
    from datetime import datetime

    return {
        "version": 1,
        "exported_at": datetime.now().isoformat(timespec="seconds"),
        "questions": [_serialize(q) for q in items],
    }


def _flatten_options(payload: dict) -> str:
    opts = payload.get("options") or []
    return " | ".join(f"{o.get('key', '')}. {o.get('text', '')}" for o in opts)


def _flatten_answer(qtype: str, answer: dict) -> str:
    if qtype == "single_choice":
        return str(answer.get("correct", ""))
    if qtype == "multiple_choice":
        return "|".join(answer.get("correct", []) or [])
    if qtype == "fill_blank":
        return " || ".join(
            "/".join(b.get("accepted", []) or []) for b in answer.get("blanks", []) or []
        )
    return ""


def export_csv(db: Session) -> str:
    items = list(
        db.scalars(
            select(Question)
            .where(Question.status == QuestionStatus.active.value)
            .order_by(Question.created_at)
        )
    )
    cols = [
        "code",
        "type",
        "stem",
        "analysis",
        "difficulty",
        "category",
        "tags",
        "options",
        "answer",
    ]
    buf = StringIO()
    writer = csv_module.DictWriter(buf, fieldnames=cols, extrasaction="ignore")
    writer.writeheader()
    for q in items:
        writer.writerow(
            {
                "code": q.code,
                "type": q.type,
                "stem": q.stem,
                "analysis": q.analysis or "",
                "difficulty": q.difficulty,
                "category": q.category.name if q.category else "",
                "tags": ";".join(t.name for t in q.tags),
                "options": _flatten_options(q.payload or {}),
                "answer": _flatten_answer(q.type, q.answer or {}),
            }
        )
    return buf.getvalue()


# --------------------------------------------------------------------------- #
# 导入
# --------------------------------------------------------------------------- #


def _resolve_category(db: Session, name: str | None) -> int | None:
    if not name:
        return None
    cat = db.scalar(select(Category).where(Category.name == name.strip()))
    return cat.id if cat else None


@invalidates_cache
def import_json(db: Session, items: list[dict], conflict: str = "skip") -> dict:
    """导入题目。conflict: skip（重复编号跳过）/ overwrite（按编号更新）/ rename（忽略编号新建）。"""
    total = len(items)
    created = updated = skipped = 0
    errors: list[dict] = []

    for idx, raw in enumerate(items, start=1):
        try:
            data = QuestionCreate(
                type=raw["type"], stem=raw["stem"], analysis=raw.get("analysis"), difficulty=raw.get("difficulty", 3), category_id=_resolve_category(db, raw.get("category")), tags=raw.get("tags") or [], payload=raw.get("payload") or {}, answer=raw.get("answer") or {}, judge_config=raw.get("judge_config") or {}, source=raw.get("source") or raw.get("code")
            )
        except Exception as exc:  # pydantic / 字段缺失
            errors.append({"row": idx, "reason": f"校验失败: {exc}"})
            continue

        existing = None
        code = raw.get("code")
        if code:
            existing = db.scalar(select(Question).where(Question.code == code))

        if existing and conflict == "skip":
            skipped += 1
            continue
        if existing and conflict == "overwrite":
            for f, v in data.model_dump(exclude={"tags"}).items():
                if f == "type":
                    setattr(existing, f, v.value)
                else:
                    setattr(existing, f, v)
            existing.tags = [get_or_create_tag(db, n) for n in data.tags]
            db.flush()
            updated += 1
            continue
        # rename / 无编号 / skip 但无冲突
        if existing and conflict == "rename":
            data_dict = data.model_dump(exclude={"tags"})
            q = Question(code=next_code(db, Question, "Q"), stat=None, **data_dict)
            q.stat = _make_stat()
            db.add(q)
            db.flush()
            q.tags = [get_or_create_tag(db, n) for n in data.tags]
            created += 1
            continue

        q = Question(code=code or next_code(db, Question, "Q"), **data.model_dump(exclude={"tags"}))
        q.stat = _make_stat()
        db.add(q)
        db.flush()
        q.tags = [get_or_create_tag(db, n) for n in data.tags]
        created += 1

    if errors and created == 0 and updated == 0 and skipped == 0:
        raise ConflictError("导入全部失败，已回滚")
    db.commit()
    return {
        "total": total,
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "errors": errors,
    }


def _make_stat():
    from app.models.question import QuestionStat

    return QuestionStat()


def get_or_create_tag(db: Session, name: str) -> Tag:
    name = name.strip()
    tag = db.scalar(select(Tag).where(Tag.name == name))
    if tag is None:
        tag = Tag(name=name)
        db.add(tag)
        db.flush()
    return tag
