"""新增每日对账正确性基础结构。

Revision ID: 0002_reconciliation_foundation
Revises: 0001_existing_schema
Create Date: 2026-07-14
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0002_reconciliation_foundation"
down_revision: Union[str, None] = "0001_existing_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "reconciliation_batch",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("business_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_by", sa.String(length=50), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reopened_by", sa.String(length=50), nullable=True),
        sa.Column("reopened_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reopen_reason", sa.String(length=500), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("business_date", name="uq_reconciliation_batch_business_date"),
    )
    op.create_index("ix_reconciliation_batch_id", "reconciliation_batch", ["id"], unique=False)

    op.create_table(
        "extraction_profile",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", "version", name="uq_extraction_profile_code_version"),
    )
    op.create_index("ix_extraction_profile_id", "extraction_profile", ["id"], unique=False)
    op.create_index("ix_extraction_profile_code", "extraction_profile", ["code"], unique=False)

    op.drop_index("ix_store_alias_alias_name", table_name="store_alias")
    with op.batch_alter_table("store_alias", recreate="always") as batch_op:
        batch_op.add_column(
            sa.Column(
                "source_code",
                sa.String(length=50),
                nullable=False,
                server_default="legacy",
            )
        )
        batch_op.add_column(sa.Column("confirmed_by", sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column("confirmed_at", sa.DateTime(), nullable=True))
        batch_op.create_unique_constraint(
            "uq_store_alias_source_name",
            ["source_code", "alias_name"],
        )
    op.create_index("ix_store_alias_alias_name", "store_alias", ["alias_name"], unique=False)
    op.create_index("ix_store_alias_source_code", "store_alias", ["source_code"], unique=False)
    op.execute(sa.text("UPDATE store_alias SET status = 'pending', confirmed_by = NULL, confirmed_at = NULL"))

    with op.batch_alter_table("import_file", recreate="always") as batch_op:
        batch_op.add_column(sa.Column("batch_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("content_hash", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("file_size", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("profile_code", sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column("profile_version", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("supersedes_file_id", sa.Integer(), nullable=True))
        batch_op.add_column(
            sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.true())
        )
        batch_op.create_foreign_key(
            "fk_import_file_store_id",
            "store",
            ["store_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch_op.create_foreign_key(
            "fk_import_file_batch_id",
            "reconciliation_batch",
            ["batch_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch_op.create_foreign_key(
            "fk_import_file_supersedes_file_id",
            "import_file",
            ["supersedes_file_id"],
            ["id"],
            ondelete="RESTRICT",
        )
    op.create_index("ix_import_file_batch_id", "import_file", ["batch_id"], unique=False)
    op.create_index("ix_import_file_content_hash", "import_file", ["content_hash"], unique=False)

    op.create_table(
        "extraction_run",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("import_file_id", sa.Integer(), nullable=False),
        sa.Column("profile_code", sa.String(length=50), nullable=False),
        sa.Column("profile_version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("raw_row_count", sa.Integer(), nullable=False),
        sa.Column("output_row_count", sa.Integer(), nullable=False),
        sa.Column("error_row_count", sa.Integer(), nullable=False),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.Column("is_current", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["import_file_id"],
            ["import_file.id"],
            name="fk_extraction_run_import_file_id",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_extraction_run_id", "extraction_run", ["id"], unique=False)
    op.create_index("ix_extraction_run_import_file_id", "extraction_run", ["import_file_id"], unique=False)

    with op.batch_alter_table("clean_data", recreate="always") as batch_op:
        batch_op.add_column(sa.Column("batch_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("store_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("extraction_run_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("profile_code", sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column("profile_version", sa.Integer(), nullable=True))
        batch_op.add_column(
            sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.true())
        )
        batch_op.create_foreign_key(
            "fk_clean_data_batch_id",
            "reconciliation_batch",
            ["batch_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch_op.create_foreign_key(
            "fk_clean_data_store_id",
            "store",
            ["store_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch_op.create_foreign_key(
            "fk_clean_data_extraction_run_id",
            "extraction_run",
            ["extraction_run_id"],
            ["id"],
            ondelete="RESTRICT",
        )
    op.create_index("ix_clean_data_batch_id", "clean_data", ["batch_id"], unique=False)
    op.create_index("ix_clean_data_store_id", "clean_data", ["store_id"], unique=False)

    op.create_table(
        "store_source_requirement",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("store_id", sa.Integer(), nullable=False),
        sa.Column("source_code", sa.String(length=50), nullable=False),
        sa.Column("requirement", sa.String(length=20), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["store_id"], ["store.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "store_id",
            "source_code",
            "effective_from",
            name="uq_store_source_requirement_period",
        ),
    )
    op.create_index("ix_store_source_requirement_id", "store_source_requirement", ["id"], unique=False)
    op.create_index("ix_store_source_requirement_store_id", "store_source_requirement", ["store_id"], unique=False)
    op.create_index("ix_store_source_requirement_source_code", "store_source_requirement", ["source_code"], unique=False)

    op.create_table(
        "source_coverage",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("batch_id", sa.Integer(), nullable=False),
        sa.Column("business_date", sa.Date(), nullable=False),
        sa.Column("store_id", sa.Integer(), nullable=False),
        sa.Column("source_code", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("evidence_type", sa.String(length=40), nullable=True),
        sa.Column("amount", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("file_count", sa.Integer(), nullable=False),
        sa.Column("valid_row_count", sa.Integer(), nullable=False),
        sa.Column("error_row_count", sa.Integer(), nullable=False),
        sa.Column("extraction_run_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["batch_id"], ["reconciliation_batch.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["store_id"], ["store.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["extraction_run_id"], ["extraction_run.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("batch_id", "store_id", "source_code", name="uq_source_coverage_scope"),
    )
    op.create_index("ix_source_coverage_id", "source_coverage", ["id"], unique=False)
    op.create_index("ix_source_coverage_batch_id", "source_coverage", ["batch_id"], unique=False)
    op.create_index("ix_source_coverage_business_date", "source_coverage", ["business_date"], unique=False)
    op.create_index("ix_source_coverage_store_id", "source_coverage", ["store_id"], unique=False)
    op.create_index("ix_source_coverage_source_code", "source_coverage", ["source_code"], unique=False)

    op.create_table(
        "data_quality_issue",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("batch_id", sa.Integer(), nullable=False),
        sa.Column("import_file_id", sa.Integer(), nullable=True),
        sa.Column("extraction_run_id", sa.Integer(), nullable=True),
        sa.Column("issue_type", sa.String(length=40), nullable=False),
        sa.Column("source_code", sa.String(length=50), nullable=False),
        sa.Column("raw_value", sa.Text(), nullable=True),
        sa.Column("affected_row_count", sa.Integer(), nullable=False),
        sa.Column("affected_amount", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("resolved_by", sa.String(length=50), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["batch_id"], ["reconciliation_batch.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["import_file_id"], ["import_file.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["extraction_run_id"], ["extraction_run.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_data_quality_issue_id", "data_quality_issue", ["id"], unique=False)
    op.create_index("ix_data_quality_issue_batch_id", "data_quality_issue", ["batch_id"], unique=False)
    op.create_index("ix_data_quality_issue_import_file_id", "data_quality_issue", ["import_file_id"], unique=False)
    op.create_index("ix_data_quality_issue_issue_type", "data_quality_issue", ["issue_type"], unique=False)
    op.create_index("ix_data_quality_issue_source_code", "data_quality_issue", ["source_code"], unique=False)
    op.create_index("ix_data_quality_issue_status", "data_quality_issue", ["status"], unique=False)

    op.create_table(
        "audit_event",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("batch_id", sa.Integer(), nullable=True),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("actor", sa.String(length=50), nullable=False),
        sa.Column("entity_type", sa.String(length=50), nullable=False),
        sa.Column("entity_id", sa.String(length=100), nullable=False),
        sa.Column("event_data", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["batch_id"], ["reconciliation_batch.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_event_id", "audit_event", ["id"], unique=False)
    op.create_index("ix_audit_event_batch_id", "audit_event", ["batch_id"], unique=False)
    op.create_index("ix_audit_event_event_type", "audit_event", ["event_type"], unique=False)

    with op.batch_alter_table("reconciliation_result", recreate="always") as batch_op:
        batch_op.add_column(sa.Column("batch_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("store_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("formula_version", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("completeness_status", sa.String(length=30), nullable=True))
        batch_op.add_column(sa.Column("calculated_at", sa.DateTime(), nullable=True))
        batch_op.create_foreign_key(
            "fk_reconciliation_result_batch_id",
            "reconciliation_batch",
            ["batch_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch_op.create_foreign_key(
            "fk_reconciliation_result_store_id",
            "store",
            ["store_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch_op.create_unique_constraint(
            "uq_reconciliation_result_batch_store",
            ["batch_id", "store_id"],
        )
    op.create_index("ix_reconciliation_result_batch_id", "reconciliation_result", ["batch_id"], unique=False)
    op.create_index("ix_reconciliation_result_store_id", "reconciliation_result", ["store_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_reconciliation_result_store_id", table_name="reconciliation_result")
    op.drop_index("ix_reconciliation_result_batch_id", table_name="reconciliation_result")
    with op.batch_alter_table("reconciliation_result", recreate="always") as batch_op:
        batch_op.drop_constraint("uq_reconciliation_result_batch_store", type_="unique")
        batch_op.drop_constraint("fk_reconciliation_result_store_id", type_="foreignkey")
        batch_op.drop_constraint("fk_reconciliation_result_batch_id", type_="foreignkey")
        batch_op.drop_column("calculated_at")
        batch_op.drop_column("completeness_status")
        batch_op.drop_column("formula_version")
        batch_op.drop_column("store_id")
        batch_op.drop_column("batch_id")

    op.drop_index("ix_audit_event_event_type", table_name="audit_event")
    op.drop_index("ix_audit_event_batch_id", table_name="audit_event")
    op.drop_index("ix_audit_event_id", table_name="audit_event")
    op.drop_table("audit_event")

    op.drop_index("ix_data_quality_issue_status", table_name="data_quality_issue")
    op.drop_index("ix_data_quality_issue_source_code", table_name="data_quality_issue")
    op.drop_index("ix_data_quality_issue_issue_type", table_name="data_quality_issue")
    op.drop_index("ix_data_quality_issue_import_file_id", table_name="data_quality_issue")
    op.drop_index("ix_data_quality_issue_batch_id", table_name="data_quality_issue")
    op.drop_index("ix_data_quality_issue_id", table_name="data_quality_issue")
    op.drop_table("data_quality_issue")

    op.drop_index("ix_source_coverage_source_code", table_name="source_coverage")
    op.drop_index("ix_source_coverage_store_id", table_name="source_coverage")
    op.drop_index("ix_source_coverage_business_date", table_name="source_coverage")
    op.drop_index("ix_source_coverage_batch_id", table_name="source_coverage")
    op.drop_index("ix_source_coverage_id", table_name="source_coverage")
    op.drop_table("source_coverage")

    op.drop_index("ix_store_source_requirement_source_code", table_name="store_source_requirement")
    op.drop_index("ix_store_source_requirement_store_id", table_name="store_source_requirement")
    op.drop_index("ix_store_source_requirement_id", table_name="store_source_requirement")
    op.drop_table("store_source_requirement")

    op.drop_index("ix_clean_data_store_id", table_name="clean_data")
    op.drop_index("ix_clean_data_batch_id", table_name="clean_data")
    with op.batch_alter_table("clean_data", recreate="always") as batch_op:
        batch_op.drop_constraint("fk_clean_data_extraction_run_id", type_="foreignkey")
        batch_op.drop_constraint("fk_clean_data_store_id", type_="foreignkey")
        batch_op.drop_constraint("fk_clean_data_batch_id", type_="foreignkey")
        batch_op.drop_column("is_current")
        batch_op.drop_column("profile_version")
        batch_op.drop_column("profile_code")
        batch_op.drop_column("extraction_run_id")
        batch_op.drop_column("store_id")
        batch_op.drop_column("batch_id")

    op.drop_index("ix_extraction_run_import_file_id", table_name="extraction_run")
    op.drop_index("ix_extraction_run_id", table_name="extraction_run")
    op.drop_table("extraction_run")

    op.drop_index("ix_import_file_content_hash", table_name="import_file")
    op.drop_index("ix_import_file_batch_id", table_name="import_file")
    with op.batch_alter_table("import_file", recreate="always") as batch_op:
        batch_op.drop_constraint("fk_import_file_supersedes_file_id", type_="foreignkey")
        batch_op.drop_constraint("fk_import_file_batch_id", type_="foreignkey")
        batch_op.drop_constraint("fk_import_file_store_id", type_="foreignkey")
        batch_op.drop_column("is_current")
        batch_op.drop_column("supersedes_file_id")
        batch_op.drop_column("profile_version")
        batch_op.drop_column("profile_code")
        batch_op.drop_column("file_size")
        batch_op.drop_column("content_hash")
        batch_op.drop_column("batch_id")

    op.drop_index("ix_store_alias_source_code", table_name="store_alias")
    op.drop_index("ix_store_alias_alias_name", table_name="store_alias")
    op.execute(
        sa.text(
            "UPDATE store_alias "
            "SET status = CASE WHEN store_id IS NOT NULL THEN 'mapped' ELSE 'pending' END"
        )
    )
    with op.batch_alter_table("store_alias", recreate="always") as batch_op:
        batch_op.drop_constraint("uq_store_alias_source_name", type_="unique")
        batch_op.drop_column("confirmed_at")
        batch_op.drop_column("confirmed_by")
        batch_op.drop_column("source_code")
    op.create_index("ix_store_alias_alias_name", "store_alias", ["alias_name"], unique=True)

    op.drop_index("ix_extraction_profile_code", table_name="extraction_profile")
    op.drop_index("ix_extraction_profile_id", table_name="extraction_profile")
    op.drop_table("extraction_profile")

    op.drop_index("ix_reconciliation_batch_id", table_name="reconciliation_batch")
    op.drop_table("reconciliation_batch")
