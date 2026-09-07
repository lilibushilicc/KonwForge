"""文本归一化与相似度，见 DESIGN §6.2。

填空 / 简答共用：NFKC 全角→半角、可选去标点、可选大小写折叠、数值容差比较。
TF-IDF 余弦相似度用纯标准库实现（两文档语料），无需引入 sklearn。
"""

from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter

_PUNCT = re.compile(r"[\s，。、；：？！,.;:?!\"'`~()（）\[\]【】{}<>_—\-]+")
_WS = re.compile(r"\s+")


def apply_aliases(text: str, aliases: dict | None) -> str:
    """按题目 judge_config.aliases 做同义替换，如 'TCP/IP' → 'tcpip'。

    对原始文本做（替换后再归一化），键越长越先匹配以避免子串误吞。
    """
    if not aliases:
        return text
    s = text or ""
    for k in sorted(aliases, key=len, reverse=True):
        if k:
            s = s.replace(k, str(aliases[k]))
    return s


def normalize(
    text: str,
    *,
    case_sensitive: bool = False,
    ignore_punct: bool = True,
    aliases: dict | None = None,
) -> str:
    """归一化：NFKC + NBSP→空格 + 可选去标点 + 可选大小写折叠。"""
    s = unicodedata.normalize("NFKC", text or "")
    s = s.replace("\u00a0", " ")
    if aliases:
        s = apply_aliases(s, aliases)
    if not case_sensitive:
        s = s.casefold()
    if ignore_punct:
        s = _PUNCT.sub("", s)
    else:
        s = _WS.sub(" ", s).strip()
    return s


def numeric_equal(a: str, b: str, tol: float = 1e-6) -> bool:
    """数值相等比较，容差内即视为等；任一非数则 False。"""
    try:
        return abs(float(a) - float(b)) <= tol
    except (TypeError, ValueError):
        return False


def _tokenize(s: str) -> list[str]:
    """粗粒度分词：连续的中英数汉字与拉丁词各自成 token。"""
    if not s:
        return []
    # 拉丁/数字连续串切出，其余按单字符（适合中文）
    toks = re.findall(r"[A-Za-z0-9]+|[^\W\d A-Za-z]", unicodedata.normalize("NFKC", s))
    return [t.casefold() for t in toks if t and not t.isspace()]


def cosine_tfidf(text_a: str, text_b: str) -> float:
    """两文档 TF-IDF 余弦相似度，∈ [0, 1]（相同文本 → 1，完全不相交 → 0）。

    用平滑 IDF = log(1 + N/df)（N=2）：出现在两篇的词 df=2 仍得 log(1+1)>0，
    避免共享词权重归零导致"越像反而越低"的反直觉；只在一篇的词权重更高。
    """
    ta, tb = _tokenize(text_a), _tokenize(text_b)
    if not ta or not tb:
        return 0.0
    fa, fb = Counter(ta), Counter(tb)
    vocab = set(fa) | set(fb)
    n = 2  # 两篇文档
    vec_a, vec_b = {}, {}
    for term in vocab:
        df = (1 if term in fa else 0) + (1 if term in fb else 0)
        idf = math.log(1 + n / df) if df else 0.0
        vec_a[term] = fa.get(term, 0) * idf
        vec_b[term] = fb.get(term, 0) * idf
    dot = sum(vec_a[t] * vec_b[t] for t in vocab)
    na = math.sqrt(sum(v * v for v in vec_a.values()))
    nb = math.sqrt(sum(v * v for v in vec_b.values()))
    if na == 0 or nb == 0:
        return 0.0
    return max(0.0, min(1.0, dot / (na * nb)))
