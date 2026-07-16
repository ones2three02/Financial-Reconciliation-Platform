"""重置并启用运行时字段映射。

Revision ID: 0004_field_mapping_runtime
Revises: 0003_authentication_foundation
Create Date: 2026-07-16
"""
from typing import Sequence, Union
from datetime import UTC, datetime

from alembic import op
import sqlalchemy as sa


revision: str = "0004_field_mapping_runtime"
down_revision: Union[str, None] = "0003_authentication_foundation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


field_mapping = sa.table(
    "field_mapping",
    sa.column("data_source", sa.String()),
    sa.column("target_field", sa.String()),
    sa.column("source_column", sa.String()),
    sa.column("is_active", sa.Boolean()),
    sa.column("created_at", sa.DateTime()),
    sa.column("updated_at", sa.DateTime()),
)


DEFAULT_MAPPINGS = (
    ("tonglian", "trade_date", "统计日期"),
    ("tonglian", "store_name", "门店名"),
    ("tonglian", "amount", "成功交易金额"),
    ("douyin", "trade_date", "核销时间"),
    ("douyin", "store_name", "核销门店"),
    ("douyin", "amount", "订单实收"),
    ("meituan", "trade_date", "验券/退款/调整时间"),
    ("meituan", "trade_date", "验券/退款/"),
    ("meituan", "store_name", "消费门店"),
    ("meituan", "amount", "总收入（元）"),
    ("meituan", "marketing_fee", "商家营销费用（元）"),
    ("store_finance", "trade_date", "日期"),
    ("store_finance", "amount", "金额"),
    ("store_finance", "payment_method", "付款方式"),
)


def upgrade() -> None:
    now = datetime.now(UTC).replace(tzinfo=None)
    op.execute(sa.delete(field_mapping))
    op.bulk_insert(
        field_mapping,
        [
            {
                "data_source": data_source,
                "target_field": target_field,
                "source_column": source_column,
                "is_active": True,
                "created_at": now,
                "updated_at": now,
            }
            for data_source, target_field, source_column in DEFAULT_MAPPINGS
        ],
    )


def downgrade() -> None:
    op.execute(sa.delete(field_mapping))
