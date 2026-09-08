"""测试夹具：in-memory SQLite（StaticPool 共享单连接）。

不用临时文件库：本机（Windows）上「每用例 drop/create 文件库」的高频磁盘操作
会偶发解释器级硬崩溃（崩点随机、连 shell 一起被带崩），in-memory 彻底消除该源。
StaticPool + check_same_thread=False 让 TestClient 工作线程与测试线程共享同一连接。
"""

import os

# 必须在导入 app 之前覆盖 DB_URL（env 优先级高于 .env），避免 import 期触碰磁盘
os.environ["DB_URL"] = "sqlite://"
os.environ["DB_ECHO"] = "false"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, event  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

import app.core.deps as deps_mod  # noqa: E402
import app.db.session as dbs  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.main import app  # noqa: E402

from app import models  # noqa: F401,E402  注册全部 ORM 模型（勿写成 import app.models，会覆盖 app 变量）


def _enable_sqlite_fk(dbapi_conn, _conn_record) -> None:
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA foreign_keys=ON")
    cur.close()


engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    future=True,
)
event.listen(engine, "connect", _enable_sqlite_fk)

SessionLocal = sessionmaker(bind=engine, class_=Session, autoflush=False, expire_on_commit=False)

# deps.get_db 在模块级 from-import 了 SessionLocal，两处都要替换
dbs.engine = engine
dbs.SessionLocal = SessionLocal
deps_mod.SessionLocal = SessionLocal


@pytest.fixture(autouse=True)
def _fresh_schema():
    """每个用例重建表（内存库，微秒级），保证互不干扰。"""
    from app.core import cache

    cache.invalidate_all()  # 缓存是进程级的，表都重建了缓存必须同步清掉
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db() -> Session:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as c:
        yield c


def unwrap(resp) -> dict:
    """剥掉统一响应信封，返回 data 部分。"""
    body = resp.json()
    assert body["code"] == 0, body
    return body["data"]
