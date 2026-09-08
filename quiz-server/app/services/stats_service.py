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
    # ---- 基础计数：5 个 COUNT 合并成 1 条 SQL（跨区库省 4 次往返）----
    (total_questions, total_attempts, total_sessions, total_mistakes, active_mistakes) = (
        int(v)
        for v in db.execute(
            select(
                select(func.count()).select_from(Question).scalar_subquery(),
                select(func.count()).select_from(Attempt).scalar_subquery(),
                select(func.count()).select_from(PracticeSession).scalar_subquery(),
                select(func.count()).select_from(Mistake).scalar_subquery(),
                select(func.count())
                .select_from(Mistake)
                .where(Mistake.removed == False)  # noqa: E712
                .scalar_subquery(),
            )
        ).one()
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

    # ---- 按题型（数据库端 GROUP BY，替代逐行拉取 + python 聚合）----
    q_types = db.execute(
        select(
            Question.type,
            func.coalesce(func.sum(QuestionStat.attempt_count), 0),
            func.coalesce(func.sum(QuestionStat.wrong_count), 0),
        )
        .join(QuestionStat, QuestionStat.question_id == Question.id)
        .group_by(Question.type)
    ).all()
    by_type_list = []
    for t, att, wrong in q_types:
        att, wrong = int(att), int(wrong)
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

    # ---- 按分类：题目数 + 作答聚合合并成一条 GROUP BY（原为两条独立查询）----
    cat_map = {c.id: c.name for c in db.scalars(select(Category)).all()}
    qcount: dict[int, int] = defaultdict(int)
    cat_agg: dict[int, list[int]] = defaultdict(lambda: [0, 0])
    for cid, qcnt, att, wrong in db.execute(
        select(
            Question.category_id,
            func.count(Question.id),
            func.coalesce(func.sum(QuestionStat.attempt_count), 0),
            func.coalesce(func.sum(QuestionStat.wrong_count), 0),
        )
        .outerjoin(QuestionStat, QuestionStat.question_id == Question.id)
        .group_by(Question.category_id)
    ).all():
        qcount[cid or 0] = int(qcnt)
        cat_agg[cid or 0] = [int(att), int(wrong)]
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
