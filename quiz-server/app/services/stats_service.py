"""统计（M5）聚合服务。全部只读，从 question_stat / attempt / mistake / session 聚合。"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.attempt import Attempt
from app.models.category import Category
from app.models.mistake import Mistake
from app.models.practice_session import PracticeSession
from app.models.question import Question, QuestionStat
from app.schemas.stats import (
    CategoryAccuracy,
    DailyActivity,
    MasteryBucket,
    StatsOut,
    StatsSummary,
    TypeAccuracy,
)

_TYPE_LABELS = {
    "single_choice": "单选",
    "multiple_choice": "多选",
    "fill_blank": "填空",
    "coding": "代码",
    "essay": "简答",
}


def get_stats(db: Session) -> StatsOut:
    # ---- 基础计数 ----
    total_questions = db.scalar(select(func.count()).select_from(Question)) or 0
    total_attempts = db.scalar(select(func.count()).select_from(Attempt)) or 0
    total_sessions = db.scalar(select(func.count()).select_from(PracticeSession)) or 0
    total_mistakes = db.scalar(select(func.count()).select_from(Mistake)) or 0
    active_mistakes = (
        db.scalar(select(func.count()).select_from(Mistake).where(Mistake.removed == False)) or 0
    )

    # ---- question_stat 聚合 ----
    stats = db.scalars(select(QuestionStat)).all()
    attempted = sum(s.attempt_count for s in stats)
    correct_sum = sum(s.attempt_count - s.wrong_count for s in stats)
    overall_accuracy = round(correct_sum / attempted * 100, 2) if attempted else None
    avg_mastery = round(sum(s.mastery for s in stats) / len(stats), 2) if stats else None
    mastered = sum(1 for s in stats if s.mastery >= 4)
    learning = sum(1 for s in stats if 1 <= s.mastery < 4)
    new = sum(1 for s in stats if s.mastery == 0)

    summary = StatsSummary(
        total_questions=total_questions,
        total_attempts=total_attempts,
        total_sessions=total_sessions,
        total_mistakes=total_mistakes,
        active_mistakes=active_mistakes,
        overall_accuracy=overall_accuracy,
        avg_mastery=avg_mastery,
        mastered_count=mastered,
        learning_count=learning,
        new_count=new,
    )

    # ---- 按题型（基于 stat 的 attempt/wrong）----
    q_types = db.execute(
        select(
            Question.type,
            func.coalesce(QuestionStat.attempt_count, 0),
            func.coalesce(QuestionStat.wrong_count, 0),
        ).join(QuestionStat, QuestionStat.question_id == Question.id)
    ).all()
    agg_type = defaultdict(lambda: [0, 0])
    for qtype, att, wrong in q_types:
        agg_type[qtype][0] += att or 0
        agg_type[qtype][1] += wrong or 0
    by_type_list = []
    for t, (att, wrong) in agg_type.items():
        corr = att - wrong
        by_type_list.append(
            TypeAccuracy(
                type=t,
                label=_TYPE_LABELS.get(t, t),
                attempted=att,
                correct=corr,
                accuracy=round(corr / att * 100, 2) if att else 0.0,
            )
        )
    by_type_list.sort(key=lambda x: x.type)

    # ---- 按分类 ----
    cat_map = {c.id: c.name for c in db.scalars(select(Category)).all()}
    qcount = defaultdict(int)
    for (cid,) in db.execute(select(Question.category_id)).all():
        qcount[cid or 0] += 1
    cat_agg = defaultdict(lambda: [0, 0])
    for cid, att, wrong in db.execute(
        select(
            Question.category_id,
            func.coalesce(QuestionStat.attempt_count, 0),
            func.coalesce(QuestionStat.wrong_count, 0),
        ).join(QuestionStat, QuestionStat.question_id == Question.id)
    ).all():
        cat_agg[cid or 0][0] += att or 0
        cat_agg[cid or 0][1] += wrong or 0
    by_category = []
    for cid, (att, wrong) in cat_agg.items():
        corr = att - wrong
        by_category.append(
            CategoryAccuracy(
                category_id=cid,
                name=cat_map.get(cid, "未分类"),
                question_count=qcount.get(cid, 0),
                attempted=att,
                correct=corr,
                accuracy=round(corr / att * 100, 2) if att else 0.0,
            )
        )
    by_category.sort(key=lambda x: -x.attempted)

    # ---- 掌握度分桶 ----
    bucket = defaultdict(int)
    for s in stats:
        bucket[min(5, max(0, s.mastery))] += 1
    mastery = [MasteryBucket(level=l, count=bucket.get(l, 0)) for l in range(6)]

    # ---- 近 30 天活动 ----
    today = date.today()
    start = today - timedelta(days=29)
    rows = db.execute(
        select(Attempt.submitted_at, Attempt.is_correct).where(
            Attempt.submitted_at >= datetime(start.year, start.month, start.day)
        )
    ).all()
    day_map = defaultdict(lambda: [0, 0])
    for r, ic in rows:
        d = r.date().isoformat()
        day_map[d][0] += 1
        if ic is True:
            day_map[d][1] += 1
    daily = []
    for i in range(30):
        d = (start + timedelta(days=i)).isoformat()
        daily.append(
            DailyActivity(
                date=d, attempts=day_map.get(d, [0, 0])[0], correct=day_map.get(d, [0, 0])[1]
            )
        )

    return StatsOut(
        summary=summary,
        by_type=by_type_list,
        by_category=by_category,
        mastery=mastery,
        daily=daily,
    )
