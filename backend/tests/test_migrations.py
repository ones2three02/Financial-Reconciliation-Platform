from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


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
