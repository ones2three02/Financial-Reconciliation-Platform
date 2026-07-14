from datetime import UTC, date, datetime

from sqlalchemy import Column, Date, DateTime, Integer, String, UniqueConstraint

from backend.app.core.db import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class ReconciliationBatch(Base):
    __tablename__ = "reconciliation_batch"
    __table_args__ = (
        UniqueConstraint("business_date", name="uq_reconciliation_batch_business_date"),
    )

    id = Column(Integer, primary_key=True, index=True)
    business_date = Column(Date, nullable=False)
    status = Column(String(30), nullable=False, default="draft")
    version = Column(Integer, nullable=False, default=1)
    created_by = Column(String(50), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    closed_by = Column(String(50), nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)
    reopened_by = Column(String(50), nullable=True)
    reopened_at = Column(DateTime(timezone=True), nullable=True)
    reopen_reason = Column(String(500), nullable=True)
