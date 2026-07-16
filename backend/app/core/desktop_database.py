from pathlib import Path

import backend.app.models  # noqa: F401
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import make_url

from backend.app.core.db import Base
from backend.scripts.backup_sqlite import backup_sqlite


BACKEND_DIR = Path(__file__).resolve().parents[2]


def _alembic_config(database_url: str) -> Config:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def _sqlite_path(database_url: str) -> Path:
    url = make_url(database_url)
    if url.drivername != "sqlite" or not url.database or url.database == ":memory:":
        raise ValueError("桌面端仅支持持久化 SQLite 数据库")
    return Path(url.database).expanduser().resolve()


def _current_revision(database_url: str) -> str | None:
    engine = create_engine(database_url)
    try:
        inspector = inspect(engine)
        if "alembic_version" not in inspector.get_table_names():
            return None
        with engine.connect() as connection:
            return connection.exec_driver_sql("SELECT version_num FROM alembic_version").scalar_one()
    finally:
        engine.dispose()


def _matches_current_metadata(database_url: str) -> bool:
    engine = create_engine(database_url)
    try:
        inspector = inspect(engine)
        actual_tables = set(inspector.get_table_names()) - {"alembic_version"}
        expected_tables = set(Base.metadata.tables)
        if actual_tables != expected_tables:
            return False
        for table_name, table in Base.metadata.tables.items():
            actual_columns = {column["name"] for column in inspector.get_columns(table_name)}
            if actual_columns != set(table.columns.keys()):
                return False
        return True
    finally:
        engine.dispose()


def prepare_desktop_database(database_url: str) -> Path | None:
    database_path = _sqlite_path(database_url)
    database_path.parent.mkdir(parents=True, exist_ok=True)
    config = _alembic_config(database_url)
    head_revision = ScriptDirectory.from_config(config).get_current_head()
    current_revision = _current_revision(database_url) if database_path.exists() else None

    if current_revision == head_revision:
        return None

    backup_path: Path | None = None
    if database_path.exists() and database_path.stat().st_size > 0:
        engine = create_engine(database_url)
        try:
            existing_tables = set(inspect(engine).get_table_names()) - {"alembic_version"}
        finally:
            engine.dispose()
        if existing_tables:
            backup_path = backup_sqlite(database_path)

    if current_revision is None and database_path.exists():
        engine = create_engine(database_url)
        try:
            existing_tables = set(inspect(engine).get_table_names()) - {"alembic_version"}
        finally:
            engine.dispose()
        if existing_tables:
            if not _matches_current_metadata(database_url):
                raise RuntimeError(
                    f"检测到未知版本的桌面数据库，已备份到 {backup_path}，请先人工确认结构"
                )
            # ORM 直接建出的旧桌面库已有最新表结构，但仍需执行当前头迁移中的
            # 默认数据初始化，不能直接盖章到 head 跳过数据迁移。
            head_script = ScriptDirectory.from_config(config).get_revision(head_revision)
            if head_script is None or not isinstance(head_script.down_revision, str):
                raise RuntimeError("无法确定桌面数据库的数据初始化迁移起点")
            command.stamp(config, head_script.down_revision)
            command.upgrade(config, "head")
            return backup_path

    command.upgrade(config, "head")
    return backup_path
