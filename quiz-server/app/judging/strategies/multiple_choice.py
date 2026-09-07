"""多选题判分，见 DESIGN §6.3。

默认部分给分：漏选按比例、错选直接 0 分；可用 judge_config 关闭部分给分或允许错选。
"""

from __future__ import annotations

from app.judging.base import JudgeResult
from app.judging.normalizer import normalize


class MultipleChoiceStrategy:
    type = "multiple_choice"

    def judge(
        self,
        *,
        payload: dict,
        answer: dict,
        config: dict,
        response: dict,
        max_score: float,
    ) -> JudgeResult:
        aliases = config.get("aliases")
        correct = {normalize(c, aliases=aliases) for c in (answer.get("correct") or [])}
        got = {normalize(c, aliases=aliases) for c in (response.get("choices") or [])}

        partial = bool(config.get("partial_credit", True))
        ratio = float(config.get("partial_ratio", 0.5))
        allow_extra = bool(config.get("allow_extra", False))

        missing = correct - got
        extra = got - correct

        if not extra and not missing:  # 全对
            score = max_score
        elif extra and not allow_extra:  # 有错选 → 0 分
            score = 0.0
        elif partial and correct:  # 只漏选：按比例给分
            score = max_score * ratio * (len(correct & got) / len(correct))
        else:
            score = 0.0

        is_correct = score >= max_score
        return JudgeResult(
            is_correct=is_correct,
            score=round(score, 4),
            max_score=max_score,
            detail={
                "missing": sorted(missing),
                "extra": sorted(extra),
                "rule": "partial" if partial else "all_or_nothing",
            },
            feedback=None,
        )
