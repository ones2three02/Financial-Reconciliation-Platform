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
