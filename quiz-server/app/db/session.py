from pathlib import Path
from urllib.parse import urlparse

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# 项目根（app/ 的上一级），用于把相对路径的 SQLite DSN 固定到项目内
PROJECT_ROOT = Path(__file__).resolve().parents[2]


def resolve_db_url(url: str) -> str:
    """sqlite:///./data/quiz.db → 绝对路径，避免依赖进程启动目录。"""
    if not url.startswith("sqlite"):
        return url
    parsed = urlparse(url)
    path = parsed.path.lstrip("/")
    if not path:
        return url
    abs_path = Path(path)
    if not abs_path.is_absolute():
        abs_path = PROJECT_ROOT / abs_path
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{abs_path.as_posix()}"


def _engine_kwargs(url: str) -> dict:
    if url.startswith("sqlite"):
        # SQLite 需要放宽线程限制；外键约束默认关闭，显式打开
        return {"connect_args": {"check_same_thread": False}, "future": True}
    if url.startswith("libsql"):
        # Turso/libSQL 自带连接管理（HTTP/gRPC），不需要 pool_pre_ping，也别传 check_same_thread
        return {"future": True}
    # 服务端 PostgreSQL / Neon：开启连接预检，避免池里残留已断开的连接
    # （Neon 等 serverless 数据库会回收空闲连接，pre_ping 能自动重建）。
    return {"future": True, "pool_pre_ping": True}


def _enable_sqlite_fk(dbapi_conn, _conn_record) -> None:
    """SQLite/libSQL 默认不强制外键，显式开启，保证 ON DELETE CASCADE 生效。"""
    try:
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()
    except Exception:
        # libSQL 的 HTTP 连接可能不认连接级 PRAGMA，忽略（ORM 层已用 cascade 处理删除）
        pass


DB_URL = resolve_db_url(settings.DB_URL)
engine = create_engine(DB_URL, echo=settings.DB_ECHO, **_engine_kwargs(DB_URL))

if DB_URL.startswith("sqlite") or DB_URL.startswith("libsql"):
    from sqlalchemy import event

    event.listen(engine, "connect", _enable_sqlite_fk)
SessionLocal = sessionmaker(bind=engine, class_=Session, autoflush=False, expire_on_commit=False)


def init_db() -> None:
    """开发期一键建表（正式环境走 Alembic）。"""
    import app.models  # noqa: F401  确保全部模型已注册
    from app.db.base import Base

    Base.metadata.create_all(bind=engine)
    logger.info("database ready: %s", DB_URL)
