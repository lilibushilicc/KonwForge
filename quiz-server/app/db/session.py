from pathlib import Path
from urllib.parse import urlparse, parse_qs, urlencode

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# 项目根（app/ 的上一级），用于把相对路径的 SQLite DSN 固定到项目内
PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _normalize_libsql(url: str) -> tuple[str, str | None]:
    """libsql://host/db?authToken=xxx → (sqlite+libsql://host/db?secure=true, auth_token)

    sqlalchemy-libsql 只认 `sqlite+libsql://` 这个 dialect 前缀，且 auth token 必须走
    connect_args，不能放在 URL query 里。这里统一归一化，避免各处重复处理。
    """
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    token = qs.pop("authToken", [None])[0] or qs.pop("auth_token", [None])[0]
    qs.setdefault("secure", ["true"])
    new_query = urlencode(qs, doseq=True)
    path = parsed.path or ""
    new_url = f"sqlite+libsql://{parsed.netloc}{path}"
    if new_query:
        new_url += f"?{new_query}"
    return new_url, token


def _resolve_sqlite_path(url: str) -> str:
    """sqlite:///./data/quiz.db → 项目内绝对路径，避免依赖进程启动目录。"""
    parsed = urlparse(url)
    path = parsed.path.lstrip("/")
    if not path:
        return url
    abs_path = Path(path)
    if not abs_path.is_absolute():
        abs_path = PROJECT_ROOT / abs_path
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{abs_path.as_posix()}"


def _parse_db_url(raw: str) -> tuple[str, dict]:
    """单一真理来源：把配置里的 DB_URL 解析成 (sqlalchemy 用的 url, create_engine 的 kwargs)。

    之前 resolve_db_url 与模块级 token 抽取各自重新解析 URL（重复调用、且 libsql 分支
    在归一化后被淹没成死代码）。合并到这里后只解析一次，引擎参数也一目了然。
    """
    if raw.startswith("libsql"):
        url, token = _normalize_libsql(raw)
        connect_args = {"auth_token": token} if token else {}
        return url, {"future": True, "connect_args": connect_args}
    if raw.startswith("sqlite"):
        return _resolve_sqlite_path(raw), {
            "future": True,
            "connect_args": {"check_same_thread": False},
        }
    # 服务端 PostgreSQL / Neon：开启连接预检，避免池里残留已断开的连接
    # （Neon 等 serverless 数据库会回收空闲连接，pre_ping 能自动重建）。
    return raw, {"future": True, "pool_pre_ping": True}


def resolve_db_url(url: str) -> str:
    """供 Alembic offline 模式等只需 url 字符串的场景使用（不连库、不含 token）。"""
    return _parse_db_url(url)[0]


def _enable_sqlite_fk(dbapi_conn, _conn_record) -> None:
    """SQLite/libSQL 默认不强制外键，显式开启，保证 ON DELETE CASCADE 生效。"""
    try:
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()
    except Exception:
        # libSQL 的 HTTP 连接可能不认连接级 PRAGMA，忽略（ORM 层已用 cascade 处理删除）
        pass


DB_URL, _ENGINE_KWARGS = _parse_db_url(settings.DB_URL)
engine = create_engine(DB_URL, echo=settings.DB_ECHO, **_ENGINE_KWARGS)

# sqlite:// 与 sqlite+libsql:// 都走 SQLite 系，需要显式开启外键约束
if DB_URL.startswith("sqlite"):
    from sqlalchemy import event

    event.listen(engine, "connect", _enable_sqlite_fk)
SessionLocal = sessionmaker(bind=engine, class_=Session, autoflush=False, expire_on_commit=False)


def init_db() -> None:
    """开发期一键建表（正式环境走 Alembic）。"""
    import app.models  # noqa: F401  确保全部模型已注册
    from app.db.base import Base

    Base.metadata.create_all(bind=engine)
    logger.info("database ready: %s", DB_URL)
