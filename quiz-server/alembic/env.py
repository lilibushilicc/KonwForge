from logging.config import fileConfig

from alembic import context

from app.core.config import settings
from app.db.base import Base
from app.db.session import resolve_db_url, engine as _app_engine
import app.models  # noqa: F401  保证全部模型注册到 metadata

config = context.config
# 与运行时一致：SQLite 相对路径解析成绝对路径，PG 等原样透传
config.set_main_option("sqlalchemy.url", resolve_db_url(settings.DB_URL))

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    # 复用 app 的 engine（含 libsql 的 auth_token connect_args），避免 alembic 自建引擎丢凭证
    connectable = _app_engine
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            render_as_batch=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
