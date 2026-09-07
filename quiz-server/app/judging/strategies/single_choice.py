"""单选题判分，见 DESIGN §6.3。"""

from __future__ import annotations

from app.judging.base import JudgeResult
from app.judging.normalizer import normalize


class SingleChoiceStrategy:
    type = "single_choice"

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
        correct = answer.get("correct")
        got = response.get("choice")
        ok = normalize(got or "", aliases=aliases) == normalize(correct or "", aliases=aliases)
        score = max_score if ok else 0.0
        return JudgeResult(
            is_correct=ok,
            score=score,
            max_score=max_score,
            detail={"correct": correct, "got": got},
            feedback=None,
        )
