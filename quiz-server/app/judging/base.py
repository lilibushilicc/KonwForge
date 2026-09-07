"""判分核心抽象，见 DESIGN §6.1。

判分是纯函数式、无副作用、无 DB 依赖的状态机：
输入 (payload, answer, judge_config, response, max_score) → 输出 JudgeResult。
这让策略可被单测直接覆盖，且 /judge/preview 与会话提交时的权威复核共用同一套逻辑。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class JudgeResult:
    is_correct: bool | None  # 主观题为 None
    score: float
    max_score: float
    detail: dict = field(default_factory=dict)
    feedback: str | None = None
    need_manual: bool = False


class JudgeStrategy(Protocol):
    """题型判分策略。新增题型只需实现该协议并在 registry 注册。"""

    type: str

    def judge(
        self,
        *,
        payload: dict,
        answer: dict,
        config: dict,
        response: dict,
        max_score: float,
    ) -> JudgeResult: ...
