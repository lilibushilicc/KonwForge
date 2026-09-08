"""远程库读性能基准：Turso(libSQL HTTP pipeline) vs Neon(PostgreSQL psycopg)。

用法:
  # Turso —— 从 Render env 快照提取 DB_URL，或直接给 --url "libsql://host?authToken=xxx"
  python verify/bench_remote_db.py turso --env ../.workbuddy/render_env.json
  # Neon —— 直接给连接串（建议 pooled）
  python verify/bench_remote_db.py neon --url "postgresql://user:pass@ep-xxx-pooler...neon.tech/neondb?sslmode=require"

每个场景预热 5 次、正式测 30 次，输出 min/avg/p50/p95/max (ms)。
结果 JSON 落盘 .workbuddy/bench_results_<backend>.json，供跨库对比与出图。
"""

from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
import time
import urllib.request
from pathlib import Path

WARMUP = 5
ROUNDS = 30
PROXY = "http://127.0.0.1:7897"
OUT_DIR = Path(__file__).resolve().parent.parent / ".workbuddy"


# ---------------------------------------------------------------- turso ----
def load_turso(url: str | None, env_json: str | None) -> tuple[str, str]:
    if url:
        return url.split("//", 1)[1].split("?")[0], url.split("authToken=")[1]
    data = json.loads(Path(env_json).read_text(encoding="utf-8-sig"))
    db_url = next(e["envVar"]["value"] for e in data if e["envVar"]["key"] == "DB_URL")
    assert db_url.startswith("libsql"), f"Render DB_URL 不是 libsql: {db_url[:30]}"
    return db_url.split("//", 1)[1].split("?")[0], db_url.split("authToken=")[1]


class TursoClient:
    """libSQL HTTP v2/pipeline，单条 HTTPS 长连接（keep-alive，贴近生产驱动行为）。

    探测阶段依次尝试 直连 → Clash 代理，通了的路径钉死整场基准。
    请求失败（连接被掐/超时）时重建连接重试，最多 3 次。
    """

    def __init__(self, host: str, token: str):
        import http.client

        self._hc = http.client
        self.host, self.token = host, token
        self.mode: str | None = None
        self.conn = None
        for mode, probe_timeout in (("direct", 8), ("proxy", 15)):
            for attempt in range(3):
                try:
                    self.conn = self._connect(mode, probe_timeout)
                    self._post([{"type": "execute", "stmt": {"sql": "SELECT 1"}}])
                    self.mode = mode
                    break
                except Exception as e:
                    print(f"  probe {mode}#{attempt + 1} failed: {type(e).__name__}: {str(e)[:80]}")
                    self._close()
                    time.sleep(1)
            if self.mode:
                break
        if not self.mode:
            raise SystemExit("直连与代理均不可用，稍后重试或检查网络")

    def _connect(self, mode: str, timeout: float):
        if mode == "direct":
            return self._hc.HTTPSConnection(self.host, timeout=timeout)
        c = self._hc.HTTPSConnection("127.0.0.1", 7897, timeout=timeout)
        c.set_tunnel(self.host, 443)
        return c

    def _close(self):
        if self.conn:
            try:
                self.conn.close()
            except Exception:
                pass
            self.conn = None

    def _post(self, requests: list[dict]) -> dict:
        body = json.dumps({"requests": requests}).encode()
        headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
        last_err = None
        for attempt in range(3):
            try:
                self.conn.request("POST", "/v2/pipeline", body=body, headers=headers)
                return json.loads(self.conn.getresponse().read())
            except Exception as e:
                last_err = e
                self._close()
                time.sleep(0.5)
                self.conn = self._connect(self.mode, 20)
        raise last_err

    def query(self, sql: str) -> list[list]:
        d = self._post([{"type": "execute", "stmt": {"sql": sql}}])
        r = d["results"][0]["response"]["result"]
        return [[f["value"]["text"] if isinstance(f["value"], dict) and "text" in f["value"] else f["value"] for f in row] for row in r["rows"]]

    def pipeline(self, sqls: list[str]) -> int:
        d = self._post([{"type": "execute", "stmt": {"sql": s}} for s in sqls])
        return sum(1 for r in d["results"] if "response" in r)


# ----------------------------------------------------------------- neon ----
class NeonClient:
    def __init__(self, url: str):
        import psycopg

        self.pg = psycopg
        url = url.replace("postgresql+psycopg://", "postgresql://")
        self.conn = psycopg.connect(url, sslmode="require", connect_timeout=15)

    def query(self, sql: str) -> list[list]:
        with self.conn.cursor() as cur:
            cur.execute(sql)
            return [[v for v in row] for row in cur.fetchall()]


# ------------------------------------------------------------ benchmark ----
def stats(samples: list[float]) -> dict:
    s = sorted(samples)
    return {
        "min": round(min(s), 1),
        "avg": round(statistics.mean(s), 1),
        "p50": round(s[len(s) // 2], 1),
        "p95": round(s[int(len(s) * 0.95)], 1),
        "max": round(max(s), 1),
    }


def run_case(name: str, fn, results: dict):
    for _ in range(WARMUP):
        fn()
    samples = []
    for _ in range(ROUNDS):
        t0 = time.perf_counter()
        fn()
        samples.append((time.perf_counter() - t0) * 1000)
    results[name] = stats(samples)
    print(f"  {name:<28} {results[name]}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("backend", choices=["turso", "neon"])
    ap.add_argument("--url", default=None)
    ap.add_argument("--env", default=None)
    args = ap.parse_args()

    if args.backend == "turso":
        host, token = load_turso(args.url, args.env)
        cli = TursoClient(host, token)
        print(f"[turso] {host}  (mode={cli.mode})")
    else:
        cli = NeonClient(args.url)
        print(f"[neon] {args.url.split('@')[1].split('/')[0]}")

    n = int(cli.query("SELECT COUNT(*) FROM question")[0][0])
    print(f"  question rows: {n}")

    results: dict = {
        "meta": {"backend": args.backend, "rows": n, "warmup": WARMUP, "rounds": ROUNDS, "ts": time.strftime("%Y-%m-%d %H:%M:%S")},
        "cases": {},
    }

    print("\n场景预热 5 + 正式 30 轮 (ms):")
    run_case("ping(SELECT 1)", lambda: cli.query("SELECT 1"), results["cases"])
    run_case("count_all", lambda: cli.query("SELECT COUNT(*) FROM question"), results["cases"])
    rid = random.randint(1, n)
    run_case(
        "one_row_by_id",
        lambda: cli.query(f"SELECT id, stem, type, difficulty FROM question WHERE id = {rid}"),
        results["cases"],
    )
    off = random.randint(0, max(0, n - 20))
    run_case(
        "list_20",
        lambda: cli.query(f"SELECT id, stem, type FROM question ORDER BY id LIMIT 20 OFFSET {off}"),
        results["cases"],
    )

    if args.backend == "turso":
        off = random.randint(0, max(0, n - 20))
        sqls = [f"SELECT id, stem, type FROM question ORDER BY id LIMIT 1 OFFSET {off + i}" for i in range(20)]
        run_case("pipeline_20x1_http", lambda: cli.pipeline(sqls), results["cases"])

    out = OUT_DIR / f"bench_results_{args.backend}.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nsaved -> {out}")


if __name__ == "__main__":
    sys.exit(main())
