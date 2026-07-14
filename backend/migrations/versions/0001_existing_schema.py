"""建立现有 MVP 数据库基线。

Revision ID: 0001_existing_schema
Revises:
Create Date: 2026-07-14
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0001_existing_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "store",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=True),
        sa.Column("region", sa.String(length=100), nullable=True),
        sa.Column("manager", sa.String(length=50), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_store_id", "store", ["id"], unique=False)
    op.create_index("ix_store_name", "store", ["name"], unique=True)

    op.create_table(
        "field_mapping",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("data_source", sa.String(length=50), nullable=False),
        sa.Column("target_field", sa.String(length=50), nullable=False),
        sa.Column("source_column", sa.String(length=100), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_field_mapping_data_source", "field_mapping", ["data_source"], unique=False)
    op.create_index("ix_field_mapping_id", "field_mapping", ["id"], unique=False)

    op.create_table(
        "import_file",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("data_source", sa.String(length=50), nullable=False),
        sa.Column("upload_status", sa.String(length=20), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("row_count", sa.Integer(), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(), nullable=True),
        sa.Column("store_id", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_import_file_data_source", "import_file", ["data_source"], unique=False)
    op.create_index("ix_import_file_id", "import_file", ["id"], unique=False)

    op.create_table(
        "reconciliation_result",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("standard_store_name", sa.String(length=100), nullable=False),
        sa.Column("tonglian_amount", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("meituan_amount", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("douyin_amount", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("cash_amount", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("sales_amount", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("expected_amount", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("actual_amount", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("difference", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=True),
        sa.Column("remarks", sa.Text(), nullable=True),
        sa.Column("is_resolved", sa.Boolean(), nullable=True),
        sa.Column("resolved_by", sa.String(length=50), nullable=True),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_reconciliation_result_id", "reconciliation_result", ["id"], unique=False)
    op.create_index("ix_reconciliation_result_standard_store_name", "reconciliation_result", ["standard_store_name"], unique=False)
    op.create_index("ix_reconciliation_result_trade_date", "reconciliation_result", ["trade_date"], unique=False)

    op.create_table(
        "store_alias",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("alias_name", sa.String(length=100), nullable=False),
        sa.Column("store_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["store_id"], ["store.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_store_alias_alias_name", "store_alias", ["alias_name"], unique=True)
    op.create_index("ix_store_alias_id", "store_alias", ["id"], unique=False)

    op.create_table(
        "raw_data",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("import_file_id", sa.Integer(), nullable=False),
        sa.Column("row_index", sa.Integer(), nullable=False),
        sa.Column("data_source", sa.String(length=50), nullable=False),
        sa.Column("content", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["import_file_id"], ["import_file.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_raw_data_data_source", "raw_data", ["data_source"], unique=False)
    op.create_index("ix_raw_data_id", "raw_data", ["id"], unique=False)

    op.create_table(
        "clean_data",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("raw_data_id", sa.Integer(), nullable=False),
        sa.Column("import_file_id", sa.Integer(), nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("original_store_name", sa.String(length=100), nullable=False),
        sa.Column("standard_store_name", sa.String(length=100), nullable=True),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("is_valid", sa.Boolean(), nullable=True),
        sa.Column("clean_status", sa.String(length=20), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["import_file_id"], ["import_file.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["raw_data_id"], ["raw_data.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_clean_data_id", "clean_data", ["id"], unique=False)
    op.create_index("ix_clean_data_source", "clean_data", ["source"], unique=False)
    op.create_index("ix_clean_data_standard_store_name", "clean_data", ["standard_store_name"], unique=False)
    op.create_index("ix_clean_data_trade_date", "clean_data", ["trade_date"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_clean_data_trade_date", table_name="clean_data")
    op.drop_index("ix_clean_data_standard_store_name", table_name="clean_data")
    op.drop_index("ix_clean_data_source", table_name="clean_data")
    op.drop_index("ix_clean_data_id", table_name="clean_data")
    op.drop_table("clean_data")

    op.drop_index("ix_raw_data_id", table_name="raw_data")
    op.drop_index("ix_raw_data_data_source", table_name="raw_data")
    op.drop_table("raw_data")

    op.drop_index("ix_store_alias_id", table_name="store_alias")
    op.drop_index("ix_store_alias_alias_name", table_name="store_alias")
    op.drop_table("store_alias")

    op.drop_index("ix_reconciliation_result_trade_date", table_name="reconciliation_result")
    op.drop_index("ix_reconciliation_result_standard_store_name", table_name="reconciliation_result")
    op.drop_index("ix_reconciliation_result_id", table_name="reconciliation_result")
    op.drop_table("reconciliation_result")

    op.drop_index("ix_import_file_id", table_name="import_file")
    op.drop_index("ix_import_file_data_source", table_name="import_file")
    op.drop_table("import_file")

    op.drop_index("ix_field_mapping_id", table_name="field_mapping")
    op.drop_index("ix_field_mapping_data_source", table_name="field_mapping")
    op.drop_table("field_mapping")

    op.drop_index("ix_store_name", table_name="store")
    op.drop_index("ix_store_id", table_name="store")
    op.drop_table("store")
