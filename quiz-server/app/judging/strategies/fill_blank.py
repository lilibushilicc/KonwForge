"""填空题判分，见 DESIGN §6.3。

逐空独立判分，分值 = max_score / 空数；
judge_config.ordered=False 时支持「乱序匹配」：用二分图最大匹配，
避免"空1的答案填到空2"被误判为全错。
"""

from __future__ import annotations

import re

from app.judging.base import JudgeResult
from app.judging.normalizer import normalize, numeric_equal


def match_blank(spec: dict, user_text: str, aliases: dict | None = None) -> bool:
    """单空是否匹配：正则优先，其次数值容差，最后归一化字符串相等。"""
    if spec.get("regex"):
        flags = 0 if spec.get("case_sensitive") else re.IGNORECASE
        try:
            return bool(re.fullmatch(spec["regex"], (user_text or "").strip(), flags))
        except re.error:
            return False

    cs = bool(spec.get("case_sensitive", False))
    tol = spec.get("numeric_tolerance")
    for cand in spec.get("accepted") or []:
        if tol and numeric_equal(user_text or "", cand, float(tol)):
            return True
        if normalize(user_text or "", case_sensitive=cs, aliases=aliases) == normalize(
            cand or "", case_sensitive=cs, aliases=aliases
        ):
            return True
    return False


def _bipartite_match(specs: list[dict], user_texts: list[str], aliases: dict | None) -> list[int]:
    """返回 specs[i] 匹配到的 user_texts 索引，未匹配为 -1。

    增广路（匈牙利算法）求最大匹配，保证总体命中数最大。
    """
    n, m = len(specs), len(user_texts)
    match_to_spec = [-1] * m  # user_text j → spec idx

    def try_match(i: int, seen: list[bool]) -> bool:
        for j in range(m):
            if seen[j]:
                continue
            if match_blank(specs[i], user_texts[j], aliases):
                seen[j] = True
                if match_to_spec[j] == -1 or try_match(match_to_spec[j], seen):
                    match_to_spec[j] = i
                    return True
        return False

    for i in range(n):
        try_match(i, [False] * m)

    spec_to_user = [-1] * n
    for j, si in enumerate(match_to_spec):
        if si != -1:
            spec_to_user[si] = j
    return spec_to_user


class FillBlankStrategy:
    type = "fill_blank"

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
        # answer.blanks 为权威；payload.blanks 仅用于空数提示
        ans_blanks = answer.get("blanks") or payload.get("blanks") or []
        if not ans_blanks:
            return JudgeResult(
                is_correct=False,
                score=0.0,
                max_score=max_score,
                detail={"error": "no_blanks"},
                feedback="题目未配置空",
            )

        ordered = bool(config.get("ordered", True))
        # response.blanks 形如 {1: "...", 2: "..."} 或 {"1": "..."}
        resp_blanks: dict = response.get("blanks") or {}
        # 规范化为按空 id 升序的用户答案列表
        user_by_id: dict[str | int, str] = {}
        for k, v in resp_blanks.items():
            user_by_id[k] = "" if v is None else str(v)

        if ordered:
            per: list[dict] = []
            for i, b in enumerate(ans_blanks):
                bid = b.get("id")
                # 缺 id 时按位置兜底（题库转换器生成的空常不带 id）
                key = bid if bid is not None else (i + 1)
                key = key if key in user_by_id else str(key)
                ut = user_by_id.get(key, "")
                per.append({"id": bid, "ok": match_blank(b, ut, aliases), "user": ut})
        else:
            # 乱序匹配：把每个空 spec 与全部用户答案做二分匹配
            # 取用户答案的有序集合用于匹配
            ut_list = list(user_by_id.values())
            assign = _bipartite_match(ans_blanks, ut_list, aliases)
            per = []
            for idx, b in enumerate(ans_blanks):
                j = assign[idx]
                ut = ut_list[j] if j != -1 else ""
                per.append({"id": b.get("id"), "ok": j != -1, "user": ut})

        per_score = max_score / len(ans_blanks)
        hit = sum(1 for p in per if p["ok"])
        score = round(per_score * hit, 4)
        is_correct = hit == len(ans_blanks)
        return JudgeResult(
            is_correct=is_correct,
            score=score,
            max_score=max_score,
            detail={"per_blank": per, "ordered": ordered, "hit": hit, "total": len(ans_blanks)},
            feedback=None,
        )
