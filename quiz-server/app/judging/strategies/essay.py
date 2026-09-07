"""简答题判分，见 DESIGN §6.3。

默认不自动给分，返回 need_manual=True、is_correct=None：
- ref_score = max_score * (0.6 * 关键词覆盖率 + 0.4 * TF-IDF 余弦相似度)  仅作「参考分」
- 前端据此展示参考答案 + 评分要点 + 关键词命中高亮 + 三档自评

schema 兼容：
- answer.reference 或 answer.reference_answer 均视为参考答案
- answer.keywords 既支持 ["tcp"] 也支持 [{"word":"tcp","weight":2}]（DESIGN §3.3 原版）
"""

from __future__ import annotations

from app.judging.base import JudgeResult
from app.judging.normalizer import cosine_tfidf, normalize


def _reference(answer: dict) -> str:
    return str(answer.get("reference") or answer.get("reference_answer") or "")


def _keywords(answer: dict) -> list[tuple[str, float]]:
    out: list[tuple[str, float]] = []
    for k in answer.get("keywords") or []:
        if isinstance(k, str):
            out.append((k, 1.0))
        elif isinstance(k, dict):
            out.append((str(k.get("word", "")), float(k.get("weight", 1.0))))
    return [(w, wt) for w, wt in out if w]


class EssayStrategy:
    type = "essay"

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
        text = str(response.get("text") or "")
        reference = _reference(answer)
        kws = _keywords(answer)

        kw_hit, kw_total = 0.0, 0.0
        norm_text = normalize(text, aliases=aliases)
        hits: list[dict] = []
        for word, wt in kws:
            kw_total += wt
            hit = bool(word) and normalize(word, aliases=aliases) in norm_text
            if hit:
                kw_hit += wt
            hits.append({"word": word, "weight": wt, "hit": hit})

        coverage = (kw_hit / kw_total) if kw_total else 0.0
        sim = cosine_tfidf(text, reference)
        ref_score = max_score * (0.6 * coverage + 0.4 * sim)

        return JudgeResult(
            is_correct=None,
            score=round(ref_score, 2),
            max_score=max_score,
            detail={
                "coverage": round(coverage, 4),
                "similarity": round(sim, 4),
                "reference": reference,
                "rubric": answer.get("rubric"),
                "keyword_hits": hits,
            },
            feedback="参考分仅供参考，请对照要点自评",
            need_manual=True,
        )
