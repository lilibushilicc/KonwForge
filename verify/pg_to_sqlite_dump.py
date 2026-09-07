"""把本地 PostgreSQL 全量导出为 SQLite 文件，供 `turso db import` 一键迁入云端。

- 源：本地 PG（quiz 库，127.0.0.1:5432）
- 目标：quiz-server/data/quiz_dump.db（全新，含 schema + 全部数据）
- 不需要出网（PG 本地、SQLite 本地）；导出的文件再用 `turso db import` 推到 Turso
- JSON 列序列化为文本；按 FK 序整表复制，保留原始 id / 层级 / 统计
"""
import json
import os
import sqlite3
from decimal import Decimal

from sqlalchemy import create_engine, inspect

import psycopg

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))  # quiz/verify
SERVER_ROOT = os.path.dirname(SCRIPT_DIR)  # quiz
SERVER_ROOT = os.path.join(SERVER_ROOT, "quiz-server")  # quiz-server
SRC = "postgresql://quiz:quiz_dev_pw@127.0.0.1:5432/quiz"
DST = os.path.join(SERVER_ROOT, "data", "quiz_dump.db")

# 导出顺序（FK 安全）；json 列需序列化
TABLES = [
    "category", "tag", "question", "question_stat", "question_tag",
    "practice_session", "session_item", "attempt", "mistake",
]
JSON_COLS = {
    "question": {"payload", "answer", "judge_config"},
    "practice_session": {"filter_snapshot", "question_ids"},
    "attempt": {"response", "judge_detail"},
}


def build_schema():
    """用项目模型的 metadata 建表（与 alembic head 一致）。"""
    os.makedirs(os.path.dirname(DST), exist_ok=True)
    import app.models  # noqa: F401  注册全部模型
    from app.db.base import Base

    eng = create_engine(f"sqlite:///{DST}")
    Base.metadata.create_all(eng)
    eng.dispose()


def main():
    if os.path.exists(DST):
        os.remove(DST)
    build_schema()

    src = psycopg.connect(SRC)
    dst = sqlite3.connect(DST)
    dst.execute("PRAGMA foreign_keys=OFF")

    for tbl in TABLES:
        with src.cursor() as cur:
            cur.execute(f"SELECT * FROM {tbl}")
            cols = [d.name for d in cur.description]
            rows = cur.fetchall()
        if not rows:
            print(f"[skip] {tbl}: 0 行")
            continue
        jsoncols = JSON_COLS.get(tbl, set())
        vals = []
        for r in rows:
            vr = list(r)
            for i, c in enumerate(cols):
                v = vr[i]
                if c in jsoncols and v is not None and not isinstance(v, str):
                    v = json.dumps(v, ensure_ascii=False)
                elif isinstance(v, Decimal):
                    v = float(v)
                vr[i] = v
            vals.append(tuple(vr))
        placeholders = ", ".join(["?"] * len(cols))
        colsql = ", ".join(cols)
        dst.executemany(
            f"INSERT INTO {tbl} ({colsql}) VALUES ({placeholders})", vals
        )
        print(f"[copy] {tbl}: {len(rows)} 行")

    src.close()
    dst.commit()
    dst.close()

    # 校验
    eng = create_engine(f"sqlite:///{DST}")
    insp = inspect(eng)
    print("--- 校验（本地 SQLite 计数）---")
    for tbl in TABLES:
        with eng.connect() as c:
            n = c.exec_driver_sql(f"SELECT count(*) FROM {tbl}").scalar()
            print(f"  {tbl}: {n}")
    eng.dispose()


if __name__ == "__main__":
    main()
