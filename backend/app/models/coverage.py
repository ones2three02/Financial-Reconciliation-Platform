from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint

from backend.app.core.db import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class SourceCoverage(Base):
    __tablename__ = "source_coverage"
    __table_args__ = (
        UniqueConstraint(
            "batch_id",
            "store_id",
            "source_code",
            name="uq_source_coverage_scope",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(
        Integer,
        ForeignKey("reconciliation_batch.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    business_date = Column(Date, nullable=False, index=True)
    store_id = Column(
        Integer,
        ForeignKey("store.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    source_code = Column(String(50), nullable=False, index=True)
    status = Column(String(30), nullable=False)
    evidence_type = Column(String(40), nullable=True)
    amount = Column(Numeric(14, 2), nullable=False, default=Decimal("0.00"))
    file_count = Column(Integer, nullable=False, default=0)
    valid_row_count = Column(Integer, nullable=False, default=0)
    error_row_count = Column(Integer, nullable=False, default=0)
    extraction_run_id = Column(
        Integer,
        ForeignKey("extraction_run.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)
