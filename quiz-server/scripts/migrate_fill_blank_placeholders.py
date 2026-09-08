#!/usr/bin/env python3
"""一次性迁移：把存量填空题题干中的裸 `____` 占位符批量替换为 `{{n}}` 编号格式。

背景
----
前端已支持新格式 `{{1}}`、`{{2}}`…（编号与答案配置的空 id 一一对应，推荐使用），
并兼容旧格式 `____`（按出现顺序自动编号）。本脚本把数据库里仍用旧格式 `____` 的
填空题一次性迁移为 `{{n}}` 新格式，消除「代码块下划线被误识别」「多空渲染」等隐患。

行为
----
- 默认 dry-run：只统计将修改的题目，不写库；加 `--apply` 才实际写入。
- 先切代码块（``` 围栏）再处理占位符，代码块内的 `____`（如 `__init__`、`___`）
  不受影响，与前端 FillStem 解析规则保持一致。
- 纯 `____` 旧题按出现顺序替换为 `{{1}}`、`{{2}}`…；与已有 `{{n}}` 混合时接续编号
  （从已有最大编号 +1 起）。
- 若 `answer.blanks` 缺失，按空位数补齐（accepted 为空，需人工补答案）；
  若已有 `answer.blanks` 数量与题干空位数不符，跳过该题并告警（避免破坏答案配置）。
- 若 `payload.blanks` 缺失，按空位数补齐（仅前端提示用）。

用法
----
    cd quiz-server
    python scripts/migrate_fill_blank_placeholders.py            # dry-run 预览
    python scripts/migrate_fill_blank_placeholders.py --apply    # 实际迁移
    python scripts/migrate_fill_blank_placeholders.py --db "sqlite:////abs/path.db" --apply

说明
----
数据库默认取应用配置（app.core.config.settings.DB_URL）。若在部署环境运行，
可用 `--db` 显式指定（如 Turso 的 sqlite+libsql 连接串，需先 pip install libsql）。
迁移只改 fill_blank 题目的 stem / payload / answer 三列，不影响其他题型与作答历史。
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# 允许从项目根直接运行
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import sqlalchemy_libsql  # noqa: F401  # 注册 libsql 方言（Turso 连接必需）
from sqlalchemy import create_engine, select  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402

from app.models.question import Question  # noqa: E402

CODE_BLOCK_RE = re.compile(r"```(\w*)\n?([\s\S]*?)```")
# 空位 = 连续 ≥4 个下划线（存量题用 ______ 6 连；dunder 如 __init__ 只有 2 连，不受影响）
TOKEN_RE = re.compile(r"\{\{(\d+)\}\}|_{4,}")


def split_code_blocks(stem: str) -> tuple[list[str], str]:
    """把代码块整体替换为 \\x00idx\\x00 占位符，返回 (code_blocks, stem_without_code)。"""
    blocks: list[str] = []

    def _repl(m: re.Match) -> str:
        blocks.append(m.group(0))
        return f"\x00{len(blocks) - 1}\x00"

    return blocks, CODE_BLOCK_RE.sub(_repl, stem)


def restore_code_blocks(stem: str, blocks: list[str]) -> str:
    def _repl(m: re.Match) -> str:
        idx = int(m.group(1))
        return blocks[idx] if idx < len(blocks) else m.group(0)

    return re.sub(r"\x00(\d+)\x00", _repl, stem)


def analyze_placeholders(stem: str) -> tuple[list[tuple[int, str]], list[tuple[int, str]]]:
    """解析非代码部分的占位符。

    返回 (numbered, blanks)：
      - numbered: [(pos, "{{n}}")]，已有编号占位符（按出现顺序）
      - blanks:   [(pos, "____")]，旧格式占位符（按出现顺序，pos 为所在字符串索引）
    """
    _, without_code = split_code_blocks(stem)
    numbered: list[tuple[int, str]] = []
    blanks: list[tuple[int, str]] = []
    for m in TOKEN_RE.finditer(without_code):
        if m.group(1) is not None:
            numbered.append((m.start(), f"{{{{{m.group(1)}}}}}"))
        else:
            blanks.append((m.start(), "____"))
    return numbered, blanks


def migrate_stem(stem: str) -> str | None:
    """把题干里的 ____ 迁移为 {{n}}。若没有 ____ 返回 None。

    用正则回调按「出现顺序」编号：已有 {{数字}} 保留，____ 依次递增编号，
    从已有最大编号 +1 起（纯旧题即从 1 起）。天然规避字符串索引偏移问题。
    """
    blocks, without_code = split_code_blocks(stem)
    numbered, blanks = analyze_placeholders(stem)
    if not blanks:
        return None
    max_id = max((int(n[1][2:-2]) for n in numbered), default=0)
    counter = {"n": max_id}

    def _repl(m: re.Match) -> str:
        if m.group(1) is not None:
            return m.group(0)  # 已有 {{数字}}，保留
        counter["n"] += 1
        return "{{%d}}" % counter["n"]

    new_without = TOKEN_RE.sub(_repl, without_code)
    return restore_code_blocks(new_without, blocks)


def count_blanks(stem: str) -> int:
    """统计非代码部分的空位总数：{{n}} 按编号去重后计数 + ____ 计数。"""
    numbered, blanks = analyze_placeholders(stem)
    ids = {int(n[1][2:-2]) for n in numbered}
    return len(ids) + len(blanks)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="存量填空题 ____ → {{n}} 占位符迁移（默认 dry-run）"
    )
    ap.add_argument("--apply", action="store_true", help="实际写入数据库（默认只预览）")
    ap.add_argument("--db", help="数据库连接串（默认取应用配置 DB_URL）")
    args = ap.parse_args()

    if args.db:
        import sqlalchemy_libsql  # noqa: F401  注册 libsql 方言
        from app.db.session import _parse_db_url

        url, kwargs = _parse_db_url(args.db)
        engine = create_engine(url, **kwargs)
        SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
        db: Session = SessionLocal()
    else:
        try:
            # 复用应用引擎：libsql 的 token 在 connect_args 里，自建引擎会丢 token 导致 401
            from app.db.session import SessionLocal as AppSessionLocal

            db = AppSessionLocal()
        except Exception as exc:  # pragma: no cover
            print(f"读取应用配置失败（{exc}），请用 --db 显式指定连接串")
            return 2

    try:
        questions = list(
            db.execute(select(Question).where(Question.type == "fill_blank")).scalars().all()
        )
    except Exception as exc:  # pragma: no cover
        print(f"连接/查询数据库失败：{exc}")
        return 2

    print(f"共找到 {len(questions)} 道填空题\n")

    to_change: list[dict] = []
    skipped: list[str] = []
    for q in questions:
        old_stem = q.stem or ""
        new_stem = migrate_stem(old_stem)
        if new_stem is None or new_stem == old_stem:
            continue  # 已是新格式

        blanks_count = count_blanks(new_stem)
        ans = q.answer if isinstance(q.answer, dict) else {}
        pay = q.payload if isinstance(q.payload, dict) else {}
        ans_blanks = ans.get("blanks") or []
        pay_blanks = pay.get("blanks") or []

        # 答案配置数量不符：跳过，避免破坏答案
        if ans_blanks and len(ans_blanks) != blanks_count:
            skipped.append(
                f"#{q.id} ({q.code}) 题干空位 {blanks_count} != answer.blanks {len(ans_blanks)}，跳过"
            )
            continue

        new_payload = dict(pay)
        new_answer = dict(ans)
        # payload.blanks 缺失/数量不符 → 补齐（仅前端提示）
        if not pay_blanks or len(pay_blanks) != blanks_count:
            new_payload["blanks"] = [
                {"id": i + 1, "hint": "", "placeholder": ""} for i in range(blanks_count)
            ]
        # answer.blanks 缺失 → 补齐空壳（需人工补答案）
        if not ans_blanks:
            new_answer["blanks"] = [
                {"id": i + 1, "accepted": [], "regex": None, "case_sensitive": False}
                for i in range(blanks_count)
            ]

        to_change.append(
            {
                "id": q.id,
                "code": q.code,
                "old_stem": old_stem,
                "new_stem": new_stem,
                "blanks": blanks_count,
                "new_payload": new_payload,
                "new_answer": new_answer,
            }
        )

    print(f"需要迁移：{len(to_change)} 道；跳过（数量不符）：{len(skipped)} 道\n")
    for s in skipped:
        print(f"  [跳过] {s}")

    if to_change:
        print("\n预览（每题 前 1 个非空 diff 片段）：")
        for c in to_change[:10]:
            print(f"  #{c['id']} [{c['code']}] 空数={c['blanks']}")
            print(f"    旧: {c['old_stem'][:80]}")
            print(f"    新: {c['new_stem'][:80]}")
        if len(to_change) > 10:
            print(f"  … 其余 {len(to_change) - 10} 道略")

    if not args.apply:
        print("\n[dry-run] 未写库。确认无误后加 --apply 执行迁移。")
        return 0

    # ---- 写入 ----
    for c in to_change:
        q = db.get(Question, c["id"])
        if q is None:
            continue
        q.stem = c["new_stem"]
        q.payload = c["new_payload"]
        q.answer = c["new_answer"]
    db.commit()
    print(f"\n[已迁移] {len(to_change)} 道填空题已写入。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
