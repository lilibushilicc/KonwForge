"""判分策略注册表，见 DESIGN §6.1。

import 本包即触发全部内置策略注册；新增题型只需写策略并在 strategies/__init__ 导入。
"""

from __future__ import annotations

from app.core.exceptions import UnsupportedQuestionType
from app.judging.base import JudgeResult, JudgeStrategy

_STRATEGIES: dict[str, JudgeStrategy] = {}


def register(strategy: JudgeStrategy) -> JudgeStrategy:
    """注册一个判分策略；重复注册以最后一次为准。"""
    _STRATEGIES[strategy.type] = strategy
    return strategy


def get_strategy(type_: str) -> JudgeStrategy:
    if type_ not in _STRATEGIES:
        raise UnsupportedQuestionType(type_)
    return _STRATEGIES[type_]


def judge(
    type_: str,
    *,
    payload: dict,
    answer: dict,
    config: dict | None = None,
    response: dict,
    max_score: float = 1.0,
) -> JudgeResult:
    """便捷入口：按题型取策略并判分。"""
    return get_strategy(type_).judge(
        payload=payload or {},
        answer=answer or {},
        config=config or {},
        response=response or {},
        max_score=max_score,
    )


# 导入即注册全部内置策略
from app.judging import strategies as _strategies  # noqa: F401

__all__ = ["JudgeResult", "JudgeStrategy", "get_strategy", "judge", "register"]
