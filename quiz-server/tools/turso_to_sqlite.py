"""把远程 Turso(libSQL) 库拉成本地 SQLite 文件，供 DataGrip / SQLite 工具查看。

背景：DataGrip 原生不支持 Turso（远程库走 HTTP，无 JDBC 驱动，官方也未排期）。
变通做法：用 libSQL 的 HTTP 协议把 schema + 数据拉下来，写入本地 .db 文件，
再用 DataGrip 内置的 SQLite 驱动打开该文件（只读镜像，改数据请回线上或用 CLI）。

用法（纯标准库，任意 python3 可跑）：
    python turso_to_sqlite.py [输出文件路径] [--env ../.env]

产物默认：./knowforge_local.db
刷新数据：重新跑一次即可（会覆盖旧文件）。
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import ssl
import sys
import urllib.request
from pathlib import Path
from urllib.parse import parse_qs, urlparse

TIMEOUT = 300  # 大表（如 question/attempt）一次拉全量可能较慢


def _pipeline_once(host: str, token: str, requests_: list[dict]) -> dict:
    """调用 libSQL HTTP 协议 /v2/pipeline（AWS 区不支持 /v1/*）。"""
    url = f"https://{host}/v2/pipeline"
    body = json.dumps({"requests": requests_}).encode()
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, timeout=TIMEOUT, context=ctx) as resp:
        return json.loads(resp.read().decode())


def pipeline(host: str, token: str, requests_: list[dict], retry: int = 2) -> dict:
    """带重试的 pipeline 调用（网络抖动/大结果集偶发超时）。"""
    last: Exception | None = None
    for _ in range(retry + 1):
        try:
            return _pipeline_once(host, token, requests_)
        except Exception as e:  # noqa: BLE001
            last = e
    raise last  # type: ignore[misc]


def read_db_url(env_path: Path) -> str:
    """从 quiz-server/.env 里读 DB_URL（形如 libsql://host?authToken=xxx）。"""
    if not env_path.exists():
        sys.exit(f"找不到 env 文件: {env_path}")
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("DB_URL="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    sys.exit(f"{env_path} 里没有 DB_URL")


def rows_of(result: dict) -> list[list]:
    """从 pipeline 的 execute 结果里取出行（每格 {type, value}）。"""
    out = []
    for r in result.get("results", []):
        if r.get("type") != "ok":
            continue
        resp = r.get("response", {})
        if resp.get("type") != "execute":
            continue
        for row in resp.get("result", {}).get("rows", []):
            out.append([c.get("value") for c in row])
    return out


def main() -> int:
    here = Path(__file__).parent
    ap = argparse.ArgumentParser()
    ap.add_argument("out", nargs="?", default=str(here / "knowforge_local.db"))
    ap.add_argument("--env", default=str(here.parent / ".env"))
    ap.add_argument("--db-url", default=None, help="直接给 libsql://...?authToken=... 覆盖 .env")
    args = ap.parse_args()

    raw = args.db_url or read_db_url(Path(args.env))
    parsed = urlparse(raw)
    host = parsed.netloc
    token = parse_qs(parsed.query).get("authToken", [None])[0]
    if not token:
        sys.exit("DB_URL 里没有 authToken")

    out_path = Path(args.out)
    if out_path.exists():
        out_path.unlink()

    print(f"拉取 {host} -> {out_path}")

    # 1) 取 schema
    res = pipeline(host, token, [{"type": "execute", "stmt": {"sql":
        "SELECT name, sql FROM sqlite_master WHERE type='table' AND sql IS NOT NULL"}}])
    tables = rows_of(res)
    if not tables:
        sys.exit("没取到任何表，检查 token / host 是否正确")

    local = sqlite3.connect(out_path)
    try:
        for name, sql in tables:
            if name.startswith("sqlite_"):
                continue
            local.execute(sql)
        local.commit()

        # 2) 逐表搬数据
        total = 0
        for (name, _sql) in tables:
            if name.startswith("sqlite_"):
                continue
            res = pipeline(host, token, [{"type": "execute", "stmt": {"sql": f'SELECT * FROM "{name}"'}}])
            data = rows_of(res)
            if not data:
                print(f"  {name}: 0 行")
                continue
            ncol = len(data[0])
            local.executemany(
                f'INSERT OR REPLACE INTO "{name}" VALUES ({",".join("?" * ncol)})', data
            )
            total += len(data)
            print(f"  {name}: {len(data)} 行")
        local.commit()
        print(f"完成，共 {total} 行 -> {out_path}")
    finally:
        local.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
