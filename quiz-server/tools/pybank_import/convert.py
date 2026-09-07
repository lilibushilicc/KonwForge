"""Python知识点题库 MD -> quiz 系统导入 JSON / 规范化 MD 的离线转换器。

用法（纯标准库，任意 python3 可跑）:
    python convert.py <题库.md> [out_dir]

产物（out_dir 默认 ./out）:
    import.json    可直接 POST /api/v1/questions/import?conflict=skip
    lint.txt       解析告警清单 + 统计
    normalized.md  统一 21 章标题/题号/答案块的规范副本

映射约定:
   一、单选题 -> single_choice        二、多选题 -> multiple_choice
   三、填空题 -> fill_blank           四、判断题 -> single_choice(正确/错误)
   五、简答题 -> essay                六、代码题 -> coding
难度统一 3；tag: Python题库(+判断题->单选)；source: Python知识点题库。

兼容的答案区写法（同库内三种混排）:
   1) 全引用:   > **答案：X** / > 解析：...
   2) HTML:     <details> ... **答案：X** ... **解析：** ... </details>
   3) 内容在 ** 外: > **答案：** X
   代码 fence 引用/裸排均可；fence 内空行与 '>' 前缀按引用标记正确处理。
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# --------------------------------------------------------------------------- #
# 常量
# --------------------------------------------------------------------------- #
SRC_DIR = {
    "一、单选题": "single_choice",
    "二、多选题": "multiple_choice",
    "三、填空题": "fill_blank",
    "四、判断题": "judge",
    "五、简答题": "essay",
    "六、代码题": "coding",
}
SECTION_LABEL = {  # 规范文档中的小节名（六题型固定顺序）
    "single_choice": "一、单选题",
    "multiple_choice": "二、多选题",
    "fill_blank": "三、填空题",
    "judge": "四、判断题",
    "essay": "五、简答题",
    "coding": "六、代码题",
}
INLINE_TYPES = ("single_choice", "multiple_choice", "fill_blank", "judge")
TAG_PY = "Python题库"
TAG_JUDGE = "判断题->单选"
SOURCE = "Python知识点题库"

RE_CH_HEAD = re.compile(r"^第\s*(?:([一二三四五六七八九十百]+)|(\d+))\s*章\s*[:：]?\s*(.*)$")
RE_Q_MARK = re.compile(r"^\*\*(\d+)\s*[.、．)]\s*(.*?)\*\*\s*$")
RE_SECTION = re.compile(r"^###\s+(.+)$")
RE_OPTION = re.compile(r"^([A-H])[.、．]\s*(.*)$")
RE_ULINE = re.compile(r"_{4,}")  # 仅把 >=4 的下划线连续段视作填空位（避免 __dunder__ 误判）
RE_HEAD_KIND = re.compile(r"^\*\*(参考答案|答案|解析)[:：]?\s*(.*?)\*\*(.*)$")
RE_PLAIN_KIND = re.compile(r"^(解析)[:：]\s*(.*)$")
RE_JUDGE_TOK = re.compile(r"(正确|错误|√|×|✓|✗|对|错|true|false|T|F)", re.IGNORECASE)
HTML_TAGS = ("<details", "</details>", "<summary")

CN_NUM = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}


def cn_to_arabic(s: str) -> int:
    if s in CN_NUM:
        return CN_NUM[s]
    total = 0
    if "十" in s:
        a, _, b = s.partition("十")
        total += CN_NUM.get(a, 1) * 10
        total += CN_NUM.get(b, 0)
    return total


def slug(text: str) -> str:
    """类 GitHub 锚点：小写、空格转 -、剔除标点。"""
    t = text.lower()
    t = re.sub(r"[^\w\u4e00-\u9fff\s-]", "", t)
    return t.replace(" ", "-")


def is_fence_line(l: str) -> bool:
    return l.lstrip().startswith("```") or l.lstrip().startswith("~~~")


# --------------------------------------------------------------------------- #
# 行级结构扫描：章节 / 小节 / 题目块
# --------------------------------------------------------------------------- #
class Item:
    __slots__ = ("body", "ch", "ch_title", "no", "qtype", "section")

    def __init__(self, ch: int, ch_title: str, section: str, qtype: str, no: int):
        self.ch = ch
        self.ch_title = ch_title
        self.section = section
        self.qtype = qtype
        self.body: list[str] = []
        self.no = no


def scan(lines: list[str]) -> tuple[list[dict], list[str]]:
    warnings: list[str] = []
    chapters: list[dict] = []
    cur: dict | None = None  # {"no","title","sections":{type:[Item]}, "order":[...]}
    cur_sec_type: str | None = None
    cur_qno = 0
    cur_item: Item | None = None
    fence = False  # 全局 fence：避免把代码内容误判为标题/题号

    def close_item():
        nonlocal cur_item
        if cur_item is not None and cur is not None:
            cur["sections"].setdefault(cur_item.qtype, []).append(cur_item)
        cur_item = None

    for raw in lines:
        line = raw.rstrip()

        if fence:
            if is_fence_line(line):
                fence = False
            if cur_item is not None:
                cur_item.body.append(line)
            continue

        if is_fence_line(line):
            fence = True
            if cur_item is not None:
                cur_item.body.append(line)
            continue

        if line.startswith("## "):  # 新章节
            close_item()
            title_raw = line[3:].strip()
            m = RE_CH_HEAD.match(title_raw)
            if m:
                num = cn_to_arabic(m.group(1)) if m.group(1) else int(m.group(2))
                title = f"第 {num} 章 {m.group(3).strip()}"
            else:
                warnings.append(f"[章节标题未识别] {title_raw}")
                title = title_raw
            cur = {"no": len(chapters) + 1, "title": title, "sections": {}, "order": []}
            chapters.append(cur)
            cur_sec_type = None
            continue

        if line.startswith("### "):  # 新小节（题型）
            close_item()
            label = line[4:].strip()
            qt = SRC_DIR.get(label)
            if qt is None:
                warnings.append(f"[小节未识别] {label}")
                cur_sec_type = None
                continue
            cur_sec_type = qt
            cur_qno = 0
            if cur is not None and qt not in cur["order"]:
                cur["order"].append(qt)
            continue

        if line.strip() == "---":
            close_item()  # 章节/题目间的分隔线
            continue

        if not line.strip():
            if cur_item is not None:
                cur_item.body.append("")  # 保留段落空行
            continue

        # 题目标记
        m = RE_Q_MARK.match(line)
        if m:
            close_item()
            if cur is None or cur_sec_type is None:
                if cur is None:
                    continue  # 卷首说明区，直接忽略
                warnings.append(f"[游离题目标记] {line[:40]}")
                continue
            cur_qno += 1
            cur_item = Item(cur["no"], cur["title"], cur_sec_type, cur_sec_type, cur_qno)
            cur_item.body.append(m.group(2).strip())
            continue

        if cur_item is not None:
            cur_item.body.append(line)
        elif cur is None:
            continue  # 卷首标题/说明区：首个章节标题前的内容一律忽略
        elif line.startswith("#"):
            continue  # 一级大标题（第1-7章 / 第8-14章 分隔行）
        else:
            warnings.append(f"[正文游离行] {line[:40]}")
    close_item()
    return chapters, warnings


# --------------------------------------------------------------------------- #
# 题目块 -> 结构化
# --------------------------------------------------------------------------- #
def pop_quote(l: str) -> tuple[bool, str]:
    """去掉行首引用符（> / > ），返回 (是否引用, 去引后的行)。"""
    if not l.startswith(">"):
        return False, l
    s = l[1:]
    s = s.removeprefix(" ")
    return True, s


def parse_body(item: Item, warnings: list[str]) -> dict:
    """统一状态机解析题目块：题干 / 选项 / 答案(fence/文本) / 解析。"""
    ctx = f"第{item.ch}章·{item.section}·第{item.no}题"
    qtype = item.qtype
    inline = qtype in INLINE_TYPES

    state = "stem"  # stem | answer | analysis
    fence_open = False
    fence_q = False
    fence_cur: list[str] = []

    stem_paras: list[str] = []
    stem_code: list[str] = []
    options: list[dict] = []
    inline_ans = ""
    ans_text: list[str] = []
    code_buf: list[str] = []
    analysis: list[str] = []

    def is_html(l: str) -> bool:
        t = l.lstrip()
        return t.startswith(HTML_TAGS) or t.startswith("<summary")

    def flush_fence():
        nonlocal fence_open, fence_cur
        fence_open = False
        content = "\n".join(fence_cur).strip("\n")
        fence_cur = []
        if state == "stem":
            stem_code.append(content)
        elif state == "answer":
            code_buf.append(content)
        else:
            analysis.extend(["```", content, "```"])

    for raw in item.body:
        if fence_open:
            l = raw
            if fence_q:
                _, l = pop_quote(l)
            if is_fence_line(l):
                flush_fence()
            else:
                fence_cur.append(l)
            continue

        q, l = pop_quote(raw)
        if is_html(l) or is_html(raw):
            continue
        if is_fence_line(l):
            fence_open = True
            fence_q = q
            fence_cur = []
            if state == "analysis":
                analysis.append(l)
            continue

        hm = RE_HEAD_KIND.match(l)
        if hm:
            kind, inner, tail = hm.group(1), hm.group(2).strip(), hm.group(3).strip()
            if kind in ("答案", "参考答案"):
                if inline:
                    state = "answer"
                    inline_ans = inner or tail
                    if inner and tail:
                        analysis.append(tail)  # 内联答案后同行的尾巴按解析处理
                else:  # essay / coding：内容在下方文本或 fence 里
                    state = "answer"
                    if tail:
                        ans_text.append(tail)
            else:  # 解析
                state = "analysis"
                if inner:
                    analysis.append(inner)
                if tail:
                    analysis.append(tail)
            continue

        pm = RE_PLAIN_KIND.match(l)
        if pm and state != "stem":
            state = "analysis"
            if pm.group(2).strip():
                analysis.append(pm.group(2).strip())
            continue

        # 普通行
        if state == "stem":
            om = RE_OPTION.match(l)
            if om and item.qtype in ("single_choice", "multiple_choice"):
                options.append({"key": om.group(1), "text": om.group(2).strip()})
                continue
            if l.strip():
                stem_paras.append(l.strip())
        elif state == "answer":
            if not l.strip():
                ans_text.append("")
            elif inline:
                # 内联题型答案区一般只有解析行；异常文本归入解析防丢
                analysis.append(l.strip())
            else:
                ans_text.append(l.strip())
        else:  # analysis
            if l.strip():
                analysis.append(l.strip())

    if fence_open:  # 未闭合 fence，尽量保留
        fence_open = False
        content = "\n".join(fence_cur)
        if state == "answer":
            code_buf.append(content)
        elif state == "stem":
            stem_code.append(content)
        warnings.append(f"[未闭合代码块] {ctx}")

    return {
        "ch": item.ch,
        "ch_title": item.ch_title,
        "type": qtype,
        "stem": "\n".join(stem_paras).strip(),
        "analysis": "\n".join(analysis).strip() or None,
        "options_raw": options,
        "inline_ans": inline_ans.strip(),
        "answer_text": "\n".join(ans_text).strip("\n"),
        "reference_code": "\n\n".join(code_buf).strip("\n"),
        "stem_code": "\n".join(stem_code).strip("\n") or None,
        "judge": qtype == "judge",
    }


def to_import_records(items: list[Item], warnings: list[str]) -> tuple[list[dict], dict]:
    """Item -> quiz 导入 JSON 行（含类型映射与 payload/answer 结构）。"""
    out: list[dict] = []
    stats = {
        "single_choice": 0,
        "multiple_choice": 0,
        "fill_blank": 0,
        "judge": 0,
        "essay": 0,
        "coding": 0,
    }
    code_seq = 0

    for it in items:
        ctx = f"第{it.ch}章·{it.section}·第{it.no}题"
        rec = parse_body(it, warnings)
        qtype = rec["type"]
        stats[qtype] += 1
        code_seq += 1

        payload: dict = {}
        answer: dict = {}
        real_type = qtype
        tags = [TAG_PY]

        if qtype in ("single_choice", "multiple_choice"):
            opts = rec["options_raw"]
            if len(opts) < 2:
                warnings.append(f"[选项不足] {ctx}: {len(opts)} 个选项 -> {rec['stem'][:40]}")
            payload["options"] = opts
            keys = {o["key"] for o in opts}
            if qtype == "single_choice":
                corr = rec["inline_ans"]
                answer["correct"] = corr
                if corr not in keys:
                    warnings.append(f"[单选答案越界] {ctx}: 答案 {corr!r} 不在选项 {sorted(keys)}")
            else:
                corr = [t for t in re.split(r"[、，,；;]", rec["inline_ans"]) if t]
                answer["correct"] = corr
                bad = [c for c in corr if c not in keys]
                if bad:
                    warnings.append(f"[多选答案越界] {ctx}: {bad} 不在选项 {sorted(keys)}")

        elif qtype == "judge":  # -> single_choice 正确/错误
            real_type = "single_choice"
            payload["options"] = [{"key": "A", "text": "正确"}, {"key": "B", "text": "错误"}]
            t = rec["inline_ans"]
            mm = RE_JUDGE_TOK.search(t)
            corr = None
            if mm:
                tok = mm.group(1).lower()
                if tok in ("正确", "对", "√", "✓", "t", "true"):
                    corr = "A"
                elif tok in ("错误", "错", "×", "✗", "f", "false"):
                    corr = "B"
            if corr is None:
                warnings.append(f"[判断题答案未识别] {ctx}: {t!r}")
                corr = "A"
            answer["correct"] = corr
            tags.append(TAG_JUDGE)

        elif qtype == "fill_blank":
            text = rec["inline_ans"]
            # 多空分隔优先用全/半角分号；无分号时才可能用逗号连接多个空
            parts = (
                [p.strip() for p in re.split(r"[；;]", text)]
                if ("；" in text or ";" in text)
                else [text.strip()]
            )
            if (
                len(parts) == 1
                and rec["stem"].count("____") > 1
                and any(s in text for s in "，,、")
            ):
                parts = [p.strip() for p in re.split(r"[，,、]", text)]
            tokens = [p for p in parts if p]
            if not tokens:
                warnings.append(f"[填空无答案] {ctx}: {rec['stem'][:40]}")
            uline = len(RE_ULINE.findall(rec["stem"]))
            if uline and uline != len(tokens):
                warnings.append(
                    f"[填空空格数不匹配] {ctx}: 题干 {uline} 空 vs 答案 {len(tokens)} 个 -> {tokens}"
                )
            blanks = []
            for i, tok in enumerate(tokens, start=1):
                accepted = [
                    a.replace("`", "").strip() for a in tok.split("/") if a.replace("`", "").strip()
                ]
                blanks.append(
                    {
                        "id": i,
                        "accepted": accepted,
                        "regex": None,
                        "case_sensitive": False,
                        "numeric_tolerance": 0.001,
                    }
                )
            payload["blanks"] = [
                {"id": i + 1, "hint": "", "placeholder": ""} for i in range(len(blanks))
            ]
            answer["blanks"] = blanks

        elif qtype == "essay":
            payload["max_chars"] = None
            ref = rec["answer_text"] or rec["inline_ans"]
            answer["reference_answer"] = ref
            answer["keywords"] = []
            answer["min_chars"] = 0
            if not ref:
                warnings.append(f"[简答无答案] {ctx}: {rec['stem'][:40]}")

        elif qtype == "coding":
            payload["language"] = "python"
            payload["template"] = rec["stem_code"] or ""
            payload["testcases"] = []
            ref_code = rec["reference_code"] or rec["answer_text"]
            answer["reference_code"] = ref_code
            answer["complexity"] = ""
            if not ref_code:
                warnings.append(f"[代码题无参考答案] {ctx}: {rec['stem'][:40]}")
            if rec["reference_code"] and rec["answer_text"]:
                extra = rec["answer_text"]
                rec["analysis"] = (
                    f"{rec['analysis']}\n\n{extra}" if rec["analysis"] else extra
                ).strip() or None
        else:
            warnings.append(f"[未知题型] {ctx}: {qtype}")

        # 判分模式：简答走关键词；无 testcase 的代码题标注人工判
        judge_config = {}
        if real_type == "essay":
            judge_config["mode"] = "keyword"
        if real_type == "coding" and not payload.get("testcases"):
            judge_config["mode"] = "manual"

        out.append(
            {
                "code": f"PY-{code_seq:04d}",
                "type": real_type,
                "stem": rec["stem"],
                "analysis": rec["analysis"],
                "difficulty": 3,
                "category": rec["ch_title"],
                "tags": tags,
                "payload": payload,
                "answer": answer,
                "judge_config": judge_config,
                "source": SOURCE,
            }
        )

    return out, stats


# --------------------------------------------------------------------------- #
# 规范化 MD 渲染
# --------------------------------------------------------------------------- #
def _q(text: str) -> str:
    return "\n".join(f"> {l}" if l else ">" for l in text.split("\n"))


def render_normalized(chapters: list[dict], total: int, warnings: list[str]) -> str:
    out: list[str] = []
    out.append("# Python 知识点题库 —— 规范版")
    out.append("")
    out.append(
        f"> 覆盖 Python 知识体系 21 章 × 六题型，共 {total} 题（判断题按「正确/错误」单选处理），"
        "每道题含题干、选项/参考答案与解析。"
    )
    out.append("")
    out.append("## 目录")
    for ch in chapters:
        out.append(f"- [**{ch['title']}**](#{slug(ch['title'])})")
    out.append("")

    for ch in chapters:
        out.append("")
        out.append("---")
        out.append("")
        out.append(f"## {ch['title']}")
        out.append("")
        for qt in ch["order"]:
            items = ch["sections"].get(qt, [])
            if not items:
                continue
            out.append(f"### {SECTION_LABEL[qt]}")
            out.append("")
            for n, it in enumerate(items, start=1):
                rec = parse_body(it, warnings)
                out.append(f"**{n}. {rec['stem']}**")
                out.append("")
                if rec.get("stem_code"):
                    out.append("```python")
                    out.append(rec["stem_code"])
                    out.append("```")
                    out.append("")
                for o in rec["options_raw"]:
                    out.append(f"{o['key']}. {o['text']}")
                if rec["options_raw"]:
                    out.append("")
                if it.qtype in ("single_choice", "multiple_choice"):
                    out.append(f"> **答案：{rec['inline_ans']}**")
                    if rec["analysis"]:
                        out.append(_q("解析：" + rec["analysis"]))
                elif it.qtype == "judge":
                    t = rec["inline_ans"]
                    mm = RE_JUDGE_TOK.search(t)
                    tok = mm.group(1).lower() if mm else "正确"
                    ok = tok in ("正确", "对", "√", "✓", "t", "true")
                    out.append(f"> **答案：{'A（正确）' if ok else 'B（错误）'}**")
                    if rec["analysis"]:
                        out.append(_q("解析：" + rec["analysis"]))
                elif it.qtype == "fill_blank":
                    out.append(f"> **答案：{rec['inline_ans']}**")
                    if rec["analysis"]:
                        out.append(_q("解析：" + rec["analysis"]))
                elif it.qtype == "essay":
                    out.append("> **参考答案：**")
                    body_txt = rec["answer_text"] or rec["inline_ans"]
                    out.append(_q(body_txt))
                    if rec["analysis"]:
                        out.append(_q("解析：" + rec["analysis"]))
                else:  # coding
                    out.append("> **参考答案：**")
                    code = rec["reference_code"] or rec["answer_text"]
                    if code:
                        out.append("> ```python")
                        for cl in code.split("\n"):
                            out.append(f"> {cl}" if cl else ">")
                        out.append("> ```")
                    if rec["analysis"]:
                        out.append(_q("解析：" + rec["analysis"]))
                out.append("")
    return "\n".join(out)


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def main() -> int:
    if len(sys.argv) < 2:
        print("用法: python convert.py <题库.md> [out_dir]", file=sys.stderr)
        return 2
    src = Path(sys.argv[1])
    out_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(__file__).parent / "out"
    out_dir.mkdir(parents=True, exist_ok=True)

    text = src.read_text(encoding="utf-8-sig")
    lines = text.splitlines()
    chapters, warnings = scan(lines)

    items: list[Item] = []
    for ch in chapters:
        for qt in ch["order"]:
            items.extend(ch["sections"].get(qt, []))

    records, stats = to_import_records(items, warnings)
    (out_dir / "import.json").write_text(
        json.dumps({"version": 1, "questions": records}, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )

    md = render_normalized(chapters, len(records), warnings)
    (out_dir / "normalized.md").write_text(md, encoding="utf-8")

    buf: list[str] = ["# 解析告警", ""]
    if warnings:
        for w in warnings:
            buf.append(f"- {w}")
    else:
        buf.append("（无）")
    buf += ["", "# 统计", "", f"- 章节数: {len(chapters)}", f"- 题目数: {len(records)}"]
    for k in ("single_choice", "multiple_choice", "fill_blank", "judge", "essay", "coding"):
        buf.append(f"- {k}: {stats[k]}")
    per_ch = {
        f"第{c['no']}章 {c['title']}": sum(len(v) for v in c["sections"].values()) for c in chapters
    }
    buf += ["", "# 每章题数"]
    for k, v in per_ch.items():
        buf.append(f"- {k}: {v}")
    (out_dir / "lint.txt").write_text("\n".join(buf), encoding="utf-8")

    print(f"chapters={len(chapters)}  questions={len(records)}  warnings={len(warnings)}")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    print(f"-> {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
