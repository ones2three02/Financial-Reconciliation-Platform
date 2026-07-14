"""新增用户与服务端会话。

Revision ID: 0003_authentication_foundation
Revises: 0002_reconciliation_foundation
Create Date: 2026-07-14
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0003_authentication_foundation"
down_revision: Union[str, None] = "0002_reconciliation_foundation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "app_user",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=80), nullable=False),
        sa.Column("password_hash", sa.String(length=128), nullable=False),
        sa.Column("password_salt", sa.String(length=32), nullable=False),
        sa.Column("role", sa.String(length=30), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_login_attempts", sa.Integer(), nullable=False),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_app_user_id", "app_user", ["id"], unique=False)
    op.create_index("ix_app_user_username", "app_user", ["username"], unique=True)

    op.create_table(
        "user_session",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["app_user.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_session_id", "user_session", ["id"], unique=False)
    op.create_index("ix_user_session_user_id", "user_session", ["user_id"], unique=False)
    op.create_index("ix_user_session_token_hash", "user_session", ["token_hash"], unique=True)
    op.create_index("ix_user_session_expires_at", "user_session", ["expires_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_user_session_expires_at", table_name="user_session")
    op.drop_index("ix_user_session_token_hash", table_name="user_session")
    op.drop_index("ix_user_session_user_id", table_name="user_session")
    op.drop_index("ix_user_session_id", table_name="user_session")
    op.drop_table("user_session")
    op.drop_index("ix_app_user_username", table_name="app_user")
    op.drop_index("ix_app_user_id", table_name="app_user")
    op.drop_table("app_user")
