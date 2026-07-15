from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

import backend.app.models  # noqa: F401
from backend.app.core.db import Base

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = PROJECT_ROOT / "backend"


def upgrade_database(database_url: str, revision: str) -> None:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, revision)


def downgrade_database(database_url: str, revision: str) -> None:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url)
    command.downgrade(config, revision)


def table_names(database_url: str) -> set[str]:
    engine = create_engine(database_url)
    try:
        return set(inspect(engine).get_table_names())
    finally:
        engine.dispose()


def test_alembic_upgrade_creates_existing_schema(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'migration.db'}"

    upgrade_database(database_url, "head")

    assert {
        "store",
        "store_alias",
        "field_mapping",
        "import_file",
        "raw_data",
        "clean_data",
        "reconciliation_result",
    } <= table_names(database_url)


def test_foundation_migration_can_downgrade_and_upgrade(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'roundtrip.db'}"

    upgrade_database(database_url, "head")
    assert {
        "reconciliation_batch",
        "extraction_profile",
        "extraction_run",
        "source_coverage",
        "data_quality_issue",
        "audit_event",
        "store_source_requirement",
        "app_user",
        "user_session",
    } <= table_names(database_url)

    downgrade_database(database_url, "0001_existing_schema")
    assert "reconciliation_batch" not in table_names(database_url)
    assert "store" in table_names(database_url)

    upgrade_database(database_url, "head")
    assert "source_coverage" in table_names(database_url)


def test_desktop_database_uses_alembic_for_a_new_database(tmp_path):
    try:
        from backend.app.core.desktop_database import prepare_desktop_database
    except ModuleNotFoundError:
        raise AssertionError("桌面数据库迁移入口尚未实现") from None
    database_path = tmp_path / "desktop.db"

    backup_path = prepare_desktop_database(f"sqlite:///{database_path}")

    assert backup_path is None
    assert "alembic_version" in table_names(f"sqlite:///{database_path}")
    engine = create_engine(f"sqlite:///{database_path}")
    try:
        with engine.connect() as connection:
            assert connection.exec_driver_sql("SELECT version_num FROM alembic_version").scalar_one() == (
                "0003_authentication_foundation"
            )
            assert connection.exec_driver_sql("SELECT COUNT(*) FROM app_user").scalar_one() == 0
    finally:
        engine.dispose()


def test_desktop_database_backs_up_and_stamps_matching_legacy_schema(tmp_path):
    try:
        from backend.app.core.desktop_database import prepare_desktop_database
    except ModuleNotFoundError:
        raise AssertionError("桌面数据库迁移入口尚未实现") from None
    database_path = tmp_path / "legacy-desktop.db"
    database_url = f"sqlite:///{database_path}"
    engine = create_engine(database_url)
    try:
        Base.metadata.create_all(engine)
    finally:
        engine.dispose()

    backup_path = prepare_desktop_database(database_url)

    assert backup_path is not None
    assert backup_path.is_file()
    engine = create_engine(database_url)
    try:
        with engine.connect() as connection:
            assert connection.exec_driver_sql("SELECT version_num FROM alembic_version").scalar_one() == (
                "0003_authentication_foundation"
            )
    finally:
        engine.dispose()
