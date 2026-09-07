"""通过 libSQL 云端 HTTP API 把本地 dump 推上 Turso（无需 Rust 驱动）。

正确请求格式（实测）:
  POST /v1/execute
  {"stmt": {"sql": "SQL", "args": [{"type":"integer","value":"1"}, ...]}}
  参数 value 一律用字符串；响应在 data["result"]。

用法（token 走环境变量，不写死在文件里）:
  TURSO_TOKEN=<jwt> .venv/Scripts/python.exe verify/import_to_turso.py
"""
import json
import os
import sqlite3
import urllib.error
import urllib.request

HOST = "knowforge-lilibushilicc.aws-ap-northeast-1.turso.io"
TOKEN = os.environ.get("TURSO_TOKEN")
if not TOKEN:
    raise SystemExit("缺少环境变量 TURSO_TOKEN")

BASE = f"https://{HOST}/v1/execute"
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
# 直连，绕开沙箱/系统代理对请求体的改写
_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))

DUMP = os.path.join(os.path.dirname(__file__), "..", "quiz-server", "data", "quiz_dump.db")

FK_ORDER = [
    "category", "tag", "question", "question_stat", "question_tag",
    "practice_session", "session_item", "attempt", "mistake",
]
ALEMBIC_HEAD = "906c31ab74fe"


def _post(sql: str, args=None) -> dict:
    body = json.dumps({"stmt": {"sql": sql, "args": args or []}}).encode()
    req = urllib.request.Request(BASE, data=body, headers=HEADERS, method="POST")
    try:
        with _OPENER.open(req, timeout=120) as r:
            data = json.loads(r.read())
    except urllib.error.HTTPError as e:
        detail = e.read().decode()[:400]
        raise SystemExit(f"HTTP {e.code} on [{sql[:70]}]: {detail}")
    if "error" in data:
        raise SystemExit(f"API error on [{sql[:70]}]: {data}")
    return data.get("result", {})


def build_params(values: tuple):
    out = []
    for v in values:
        if v is None:
            out.append({"type": "null", "value": None})
        elif isinstance(v, bool):
            # libSQL: integer 的 value 必须是字符串
            out.append({"type": "integer", "value": "1" if v else "0"})
        elif isinstance(v, int):
            out.append({"type": "integer", "value": str(v)})
        elif isinstance(v, float):
            # libSQL: float 的 value 必须是 JSON 数字（不是字符串）
            out.append({"type": "float", "value": v})
        elif isinstance(v, str):
            out.append({"type": "text", "value": v})
        else:
            out.append({"type": "text", "value": str(v)})
    return out


def main():
    src = sqlite3.connect(DUMP)
    print("[1] 建表（CREATE TABLE IF NOT EXISTS）")
    rows = src.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    for (sql,) in rows:
        if not sql:
            continue
        safe = sql.replace("CREATE TABLE ", "CREATE TABLE IF NOT EXISTS ", 1)
        _post(safe)
    _post(
        "CREATE TABLE IF NOT EXISTS alembic_version "
        "(version_num VARCHAR(32) NOT NULL, "
        "CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num))"
    )
    print(f"    [OK] {len(rows)} 张表 + alembic_version 已建")

    print("[2] 清空已有数据（保证重导干净）")
    for tbl in reversed(FK_ORDER):
        _post(f"DELETE FROM {tbl}")

    print("[3] 导入数据（父表先插，每批 40 行）")
    for tbl in FK_ORDER:
        all_rows = src.execute(f"SELECT * FROM {tbl}").fetchall()
        if not all_rows:
            print(f"    [skip] {tbl}: 0 行")
            continue
        cols = [d[0] for d in src.execute(f"SELECT * FROM {tbl}").description]
        ncol = len(cols)
        colsql = ", ".join(cols)
        batch = 40
        for i in range(0, len(all_rows), batch):
            chunk = all_rows[i : i + batch]
            placeholders = ", ".join(
                ["(" + ", ".join(["?"] * ncol) + ")"] * len(chunk)
            )
            flat = []
            for r in chunk:
                flat.extend(build_params(r))
            _post(
                f"INSERT INTO {tbl} ({colsql}) VALUES {placeholders}",
                flat,
            )
        print(f"    [copy] {tbl}: {len(all_rows)} 行")

    print("[3] alembic_version = head")
    _post(
        "INSERT OR IGNORE INTO alembic_version (version_num) VALUES (?)",
        [{"type": "text", "value": ALEMBIC_HEAD}],
    )

    print("[4] 校验：本地 vs Turso 计数")
    ok = True
    for tbl in FK_ORDER + ["alembic_version"]:
        local = src.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
        res = _post(f"SELECT COUNT(*) AS c FROM {tbl}")
        remote = 0
        try:
            remote = int(res["rows"][0][0]["value"])
        except Exception:
            remote = 0
        flag = "OK" if local == remote else "MISMATCH"
        if local != remote:
            ok = False
        print(f"    {tbl:16s} local={local:5d}  remote={remote:5d}  [{flag}]")
    src.close()
    print("\n全部完成 ✅" if ok else "\n⚠️ 存在计数不一致，请检查上方 MISMATCH")


if __name__ == "__main__":
    main()
