# 一次性修复：从 out/normalized.md 提取题干代码块，回填 import.json 的 stem。
# 背景：convert.py 早期版本把选择题/填空题题干里的代码块丢进了 stem_code 却没并回 stem，
# 导致线上"以下代码的输出是？"只剩一句话没有代码。原始题库 md 已不可得，
# 但 normalized.md 与 import.json 同序（第 k 题 <-> PY-{k:04d}），可按序号对齐回填。

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
MD = HERE / "out" / "normalized.md"
OLD = HERE / "out" / "import.json"
OUT = HERE / "out" / "import_fixed.json"

RE_Q = re.compile(r"^\*\*(\d+)\. (.*)\*\*\s*$")
RE_SEC = re.compile(r"^### ")
RE_FENCE = re.compile(r"^(`{3,}|~{3,})\s*(\w*)")


def parse(md_text: str):
    lines = md_text.splitlines()
    questions: list[dict] = []
    section = ""
    in_fence = False
    fence_lang = ""
    fence_buf: list[str] = []
    cur: dict | None = None
    answered = False  # 当前题是否已进入答案区（其后 fence 属于解析，不收）

    for raw in lines:
        if in_fence:
            if RE_FENCE.match(raw):
                cur["codes"].append((fence_lang, "\n".join(fence_buf).rstrip("\n")))
                in_fence, fence_buf = False, []
            else:
                fence_buf.append(raw)
            continue

        if RE_SEC.match(raw):
            section = raw.lstrip("#").strip()
            continue

        m = RE_Q.match(raw)
        if m:
            cur = {"no": int(m.group(1)), "stem_line": m.group(2).strip(), "codes": [], "section": section}
            answered = False
            questions.append(cur)
            continue

        if cur is None:
            continue
        fm = RE_FENCE.match(raw)
        if fm and not answered:
            in_fence = True
            fence_lang = fm.group(2) or "python"
            fence_buf = []
            continue
        if "答案" in raw and raw.lstrip().startswith(">"):
            answered = True

    if in_fence and cur is not None:  # 未闭合 fence 兜底
        cur["codes"].append((fence_lang, "\n".join(fence_buf)))
    return questions


def main() -> int:
    qs = parse(MD.read_text(encoding="utf-8"))
    records = json.loads(OLD.read_text(encoding="utf-8"))
    if isinstance(records, dict):
        records = records.get("questions", [])
    print(f"normalized.md 解析出 {len(qs)} 题 | import.json {len(records)} 题")
    if len(qs) != len(records):
        print("!! 数量不一致，中止（顺序对齐不可信）", file=sys.stderr)
        return 1

    changed, skipped_coding, stem_mismatch = 0, 0, []
    for i, (q, rec) in enumerate(zip(qs, records), start=1):
        expect_code = f"PY-{i:04d}"
        if rec["code"] != expect_code:
            print(f"!! 序号错位: 第{i}题 expect {expect_code} got {rec['code']}", file=sys.stderr)
            return 1
        old_stem = rec["stem"]
        if not q["stem_line"]:
            stem_mismatch.append((rec["code"], "空题干行"))
            continue
        if not old_stem.startswith(q["stem_line"]):
            stem_mismatch.append((rec["code"], f"题干不一致: {q['stem_line'][:30]!r} vs {old_stem[:30]!r}"))
        if rec["type"] == "coding":
            skipped_coding += 1  # coding 的代码在 payload.template，不重复
            continue
        if not q["codes"]:
            continue
        blocks = "\n\n".join(
            f"```{lang}\n{code}\n```" for lang, code in q["codes"] if code.strip()
        )
        if blocks:
            rec["stem"] = old_stem.rstrip() + "\n\n" + blocks
            changed += 1

    OUT.write_text(json.dumps(records, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"回填代码块: {changed} 题 | coding 跳过: {skipped_coding} | 题干不一致告警: {len(stem_mismatch)}")
    for code, why in stem_mismatch[:10]:
        print(f"  [warn] {code}: {why}")
    demo = next(r for r in records if r["code"] == "PY-0029")
    print("--- PY-0029 修复后 stem ---")
    print(demo["stem"])
    print(f"-> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
