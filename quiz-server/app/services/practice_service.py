"""练习会话引擎（M3）。

职责：
- 建会话：按筛选条件从题库抽题，生成 practice_session + session_item。
- 作答：即时判分（复用 judging.registry.judge），写 attempt，更新 session_item /
  question_stat，错题则 upsert mistake。
- 交卷：汇总正确数 / 分数 / 正确率。

所有写操作都在传入的 db 会话里提交，便于测试用同一事务。
"""

from __future__ import annotations

from typing import Optional

import random
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.judging.registry import judge as do_judge
from app.models.attempt import Attempt
from app.models.category import Category
from app.models.mistake import Mistake
from app.models.practice_session import PracticeSession
from app.models.question import Question, QuestionStat
from app.models.session_item import SessionItem
from app.schemas.enums import SessionMode, SessionStatus
from app.schemas.practice import (
    AnswerResult,
    AnswerSubmit,
    PracticeSessionCreate,
    PracticeSessionOut,
    QuestionPlayOut,
    SessionFilter,
    SessionItemOut,
    SessionSubmitResult,
)
from app.utils.code_gen import next_code


# 固定题型顺序：选择题（单选 → 多选）→ 填空题 → 简答题 → 代码题
TYPE_ORDER: dict[str, int] = {
    "single_choice": 0,
    "multiple_choice": 1,
    "fill_blank": 2,
    "essay": 3,
    "coding": 4,
}


def _order_by_type(questions: list[Question]) -> list[Question]:
    """按固定题型顺序 + id 稳定排序（不再随机打乱）。"""
    return sorted(questions, key=lambda q: (TYPE_ORDER.get(q.type, 99), q.id))


# --------------------------------------------------------------------------- #
# 选题
# --------------------------------------------------------------------------- #
def _expand_category_ids(db: Session, category_ids: list[int]) -> list[int]:
    """把选中的分类扩展为『自身 + 所有后代分类』。

    分类是多级树，题目只挂在叶子分类上；选父分类练题时应包含其下全部子分类的题目，
    否则选根分类（如「Python 知识点」）会匹配到 0 题。
    """
    if not category_ids:
        return category_ids
    rows = db.execute(select(Category.id, Category.parent_id)).all()
    children: dict[int | None, list[int]] = {}
    for cid, pid in rows:
        children.setdefault(pid, []).append(cid)
    result: set[int] = set()
    stack = list(category_ids)
    while stack:
        cur = stack.pop()
        if cur in result:
            continue
        result.add(cur)
        for child in children.get(cur, []):
            if child not in result:
                stack.append(child)
    return list(result)


def _build_query(db: Session, f: SessionFilter, base=None):
    q = base if base is not None else select(Question)
    q = q.where(Question.status == "active")
    if f.category_ids:
        expanded = _expand_category_ids(db, f.category_ids)
        q = q.where(Question.category_id.in_(expanded))
    if f.types:
        q = q.where(Question.type.in_([t.value if hasattr(t, "value") else t for t in f.types]))
    if f.difficulties:
        q = q.where(Question.difficulty.in_(f.difficulties))
    return q


def _pick_questions(db: Session, f: SessionFilter, count: int) -> list[Question]:
    stmt = _build_query(db, f)
    ids = db.scalars(stmt.with_only_columns(Question.id)).all()
    if not ids:
        return []
    if len(ids) > count:
        ids = random.sample(ids, count)
    questions = db.scalars(select(Question).where(Question.id.in_(ids))).all()
    # 固定题型顺序（选择题→填空题→简答题→代码题），同题型内按 id 稳定
    return _order_by_type(questions)


def _pick_category_questions(db: Session, f: SessionFilter) -> list[Question]:
    """分类练习：返回该分类下全部题目，按固定题型顺序排列（不抽样、不随机）。"""
    questions = db.scalars(_build_query(db, f)).all()
    return _order_by_type(questions)


def _pick_mistake_questions(db: Session, f: SessionFilter, count: int) -> list[Question]:
    """错题模式：从当前未移除的错题里抽题。"""
    mids = db.scalars(
        select(Mistake.question_id).where(Mistake.removed == False)
    ).all()
    if not mids:
        return []
    if len(mids) > count:
        mids = random.sample(mids, count)
    questions = db.scalars(select(Question).where(Question.id.in_(mids))).all()
    return _order_by_type(questions)


def create_session(db: Session, data: PracticeSessionCreate) -> PracticeSession:
    if data.mode == SessionMode.mistake:
        questions = _pick_mistake_questions(db, data.filter, data.count)
    elif data.mode == SessionMode.category:
        questions = _pick_category_questions(db, data.filter)
    else:
        questions = _pick_questions(db, data.filter, data.count)

    session = PracticeSession(
        code=next_code(db, PracticeSession, "S"),
        title=data.title,
        mode=data.mode.value,
        status=SessionStatus.active.value,
        total_count=len(questions),
        duration_limit_sec=data.duration_limit_sec,
        question_ids=[q.id for q in questions],
        filter_snapshot=data.filter.model_dump(),
        started_at=datetime.now(),
        last_active_at=datetime.now(),
    )
    db.add(session)
    db.flush()
    for seq, q in enumerate(questions, start=1):
        db.add(SessionItem(session_id=session.id, question_id=q.id, seq=seq, score_weight=1.0))
    db.commit()
    db.refresh(session)
    return session


# --------------------------------------------------------------------------- #
# 作答
# --------------------------------------------------------------------------- #
def _resolve_correct(type_: str, result, submit: AnswerSubmit) -> tuple[bool, Optional[bool]]:
    """返回 (correct_bool, is_correct_for_stat)。

    客观题直接用判分结果；简答(need_manual)则用 self_eval 决定：
    mastered → 正确，fuzzy/unknown → 错误。
    """
    if result.need_manual:
        level = submit.self_eval or "unknown"
        correct = level == "mastered"
        return correct, correct
    is_correct = bool(result.is_correct)
    return is_correct, is_correct


def _grade_item(db: Session, session: PracticeSession, submit: AnswerSubmit) -> AnswerResult:
    """单题判分 + 写库（attempt/stat/mistake），但不提交事务。

    提交交由调用方统一处理，便于批量作答时单事务一次性落库。
    """
    item = db.scalar(
        select(SessionItem).where(
            SessionItem.id == submit.item_id, SessionItem.session_id == session.id
        )
    )
    if item is None:
        raise ValueError("item 不属于该会话")
    question = db.get(Question, item.question_id)
    if question is None:
        raise ValueError("题目不存在")

    result = do_judge(
        question.type,
        payload=question.payload or {},
        answer=question.answer or {},
        config=question.judge_config or {},
        response=submit.response or {},
        max_score=1.0,
    )

    correct, is_correct = _resolve_correct(question.type, result, submit)

    # 1) attempt（append-only）
    attempt = Attempt(
        session_id=session.id,
        item_id=item.id,
        question_id=question.id,
        response=submit.response or {},
        is_correct=is_correct,
        score=result.score if not result.need_manual else (1.0 if correct else 0.0),
        max_score=1.0,
        judge_detail=result.detail,
        duration_sec=submit.duration_sec,
    )
    db.add(attempt)

    # 2) session_item
    item.answered = True
    item.is_correct = is_correct
    item.score = attempt.score
    if submit.duration_sec:
        item.spent_sec += submit.duration_sec
    db.flush()

    # 3) question_stat
    _update_stat(db, question, is_correct)

    # 4) mistake：错则 upsert；对则累计 cleared
    _update_mistake(db, question.id, is_correct)

    # 5) session 活跃时间
    session.last_active_at = datetime.now()

    return AnswerResult(
        item_id=item.id,
        is_correct=is_correct,
        correct=correct,
        score=attempt.score,
        max_score=1.0,
        judge_detail=result.detail,
        need_manual=result.need_manual,
        feedback=result.feedback,
        reveal={
            "answer": question.answer,
            "analysis": question.analysis,
            "judge_detail": result.detail,
        },
        progress={},
    )


def answer_item(db: Session, session: PracticeSession, submit: AnswerSubmit) -> AnswerResult:
    r = _grade_item(db, session, submit)
    db.commit()

    # 进度
    items = db.scalars(select(SessionItem).where(SessionItem.session_id == session.id)).all()
    answered = sum(1 for i in items if i.answered)
    correct_count = sum(1 for i in items if i.is_correct is True)
    r.progress = {
        "answered": answered,
        "total": len(items),
        "correct_count": correct_count,
    }
    return r


def answer_batch(
    db: Session, session: PracticeSession, submits: list[AnswerSubmit]
) -> list[dict]:
    """整卷批量作答：逐题判分，单事务提交。返回每题结果摘要。"""
    results: list[dict] = []
    for sub in submits:
        try:
            r = _grade_item(db, session, sub)
            results.append(
                {
                    "item_id": r.item_id,
                    "ok": True,
                    "is_correct": r.is_correct,
                    "correct": r.correct,
                }
            )
        except ValueError as e:
            results.append({"item_id": sub.item_id, "ok": False, "error": str(e)})
    db.commit()
    return results


def _update_stat(db: Session, question: Question, is_correct: Optional[bool]) -> None:
    stat = db.scalar(select(QuestionStat).where(QuestionStat.question_id == question.id))
    if stat is None:
        stat = QuestionStat(question_id=question.id)
        db.add(stat)
        db.flush()
    stat.attempt_count += 1
    if is_correct is False:
        stat.wrong_count += 1
    stat.last_attempt_at = datetime.now()
    stat.last_result = 1 if is_correct else 0
    if is_correct:
        stat.streak += 1
        stat.mastery = min(5, stat.mastery + 1)
    else:
        stat.streak = 0
        stat.mastery = max(0, stat.mastery - 1)


def _update_mistake(db: Session, question_id: int, is_correct: Optional[bool]) -> None:
    m = db.scalar(select(Mistake).where(Mistake.question_id == question_id))
    if is_correct is False:
        if m is None:
            m = Mistake(question_id=question_id)
            db.add(m)
            db.flush()
        else:
            m.wrong_count += 1
            m.last_wrong_at = datetime.now()
    elif is_correct is True:
        if m is not None and not m.removed:
            m.cleared_count += 1
            if m.cleared_count >= 2:  # 连续/累计两次做对 → 视为已掌握
                m.mastered = True


# --------------------------------------------------------------------------- #
# 交卷
# --------------------------------------------------------------------------- #
def submit_session(db: Session, session: PracticeSession) -> SessionSubmitResult:
    items = db.scalars(select(SessionItem).where(SessionItem.session_id == session.id)).all()
    total = len(items)
    correct = sum(1 for i in items if i.is_correct is True)
    score = round(sum((i.score or 0) for i in items), 2)
    accuracy = round(correct / total * 100, 2) if total else None

    session.status = SessionStatus.submitted.value
    session.submitted_at = datetime.now()
    session.correct_count = correct
    session.score = score
    session.accuracy = accuracy
    db.commit()
    db.refresh(session)

    return SessionSubmitResult(
        id=session.id,
        status=session.status,
        score=score,
        correct_count=correct,
        accuracy=accuracy,
        total_count=total,
        elapsed_sec=session.elapsed_sec,
    )


def list_sessions(
    db: Session, *, mode=None, status=None, page=1, page_size=20
) -> tuple[list[PracticeSession], int]:
    stmt = select(PracticeSession)
    if mode:
        stmt = stmt.where(PracticeSession.mode == mode.value)
    if status:
        stmt = stmt.where(PracticeSession.status == status.value)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.scalars(
        stmt.order_by(PracticeSession.started_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return list(rows), total or 0


def get_session(db: Session, session_id: int) -> PracticeSession | None:
    return db.get(PracticeSession, session_id)


# --------------------------------------------------------------------------- #
# 序列化（ORM → 出参，处理嵌套 question / reveal）
# --------------------------------------------------------------------------- #
def _to_play_out(q: Question) -> QuestionPlayOut:
    return QuestionPlayOut(
        id=q.id,
        code=q.code,
        type=q.type,
        stem=q.stem,
        difficulty=q.difficulty,
        category_id=q.category_id,
        category_name=q.category.name if q.category else None,
        tags=[t.name for t in q.tags],
        payload=q.payload or {},
        status=q.status,
        source=q.source,
        version=q.version,
        created_at=q.created_at,
        updated_at=q.updated_at,
    )


def build_session_out(db: Session, session: PracticeSession) -> PracticeSessionOut:
    items = db.scalars(
        select(SessionItem).where(SessionItem.session_id == session.id).order_by(SessionItem.seq)
    ).all()
    out_items: list[SessionItemOut] = []
    for it in items:
        q = db.get(Question, it.question_id)
        reveal = None
        if it.answered:
            attempt = db.scalars(
                select(Attempt).where(Attempt.item_id == it.id).order_by(Attempt.id.desc()).limit(1)
            ).first()
            reveal = {
                "answer": q.answer if q else None,
                "analysis": q.analysis if q else None,
                "judge_detail": attempt.judge_detail if attempt else None,
            }
        out_items.append(
            SessionItemOut(
                id=it.id,
                session_id=it.session_id,
                question_id=it.question_id,
                seq=it.seq,
                score_weight=float(it.score_weight),
                flagged=it.flagged,
                answered=it.answered,
                is_correct=it.is_correct,
                score=it.score,
                spent_sec=it.spent_sec,
                question=_to_play_out(q) if q else None,  # type: ignore[arg-type]
                reveal=reveal,
            )
        )
    return PracticeSessionOut(
        id=session.id,
        code=session.code,
        title=session.title,
        mode=session.mode,
        status=session.status,
        total_count=session.total_count,
        duration_limit_sec=session.duration_limit_sec,
        elapsed_sec=session.elapsed_sec,
        started_at=session.started_at,
        last_active_at=session.last_active_at,
        submitted_at=session.submitted_at,
        score=session.score,
        correct_count=session.correct_count,
        accuracy=session.accuracy,
        items=out_items,
    )


def patch_session(db: Session, session: PracticeSession, *, status=None, elapsed_sec=None):
    if status is not None:
        session.status = status.value
    if elapsed_sec is not None:
        session.elapsed_sec = elapsed_sec
    session.last_active_at = datetime.now()
    db.commit()
    db.refresh(session)
    return session
