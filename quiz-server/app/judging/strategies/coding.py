"""代码题判分，见 DESIGN §6.3。

沙箱默认关闭（settings.SANDBOX_ENABLED=False）：返回 need_manual=True、
is_correct=None，提示用户对照参考实现与复杂度自评，不算分。
沙箱接通（M5）后按用例通过率给分。
"""

from __future__ import annotations

from app.core.config import settings
from app.judging.base import JudgeResult


class CodingStrategy:
    type = "coding"

    def judge(
        self,
        *,
        payload: dict,
        answer: dict,
        config: dict,
        response: dict,
        max_score: float,
    ) -> JudgeResult:
        sandbox_on = bool(config.get("sandbox", False)) and settings.SANDBOX_ENABLED
        if not sandbox_on:
            return JudgeResult(
                is_correct=None,
                score=0.0,
                max_score=max_score,
                detail={"mode": "manual"},
                feedback="沙箱未启用，请对照参考实现与复杂度自评",
                need_manual=True,
            )

        # —— 沙箱路径（M5 接通）预留：按用例通过率给分 ——
        cases = [c for c in payload.get("testcases", []) if not c.get("hidden_visible", False)]
        # 占位：真实实现见 M5 的 app/services/sandbox.py
        passed = 0
        total = len(cases) or 1
        score = max_score * (passed / total)
        return JudgeResult(
            is_correct=(passed == total and total > 0),
            score=round(score, 4),
            max_score=max_score,
            detail={"mode": "sandbox", "passed": passed, "total": total},
            feedback=None,
        )
