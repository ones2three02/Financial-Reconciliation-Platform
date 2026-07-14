from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, Text

from backend.app.core.db import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class DataQualityIssue(Base):
    __tablename__ = "data_quality_issue"

    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(
        Integer,
        ForeignKey("reconciliation_batch.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    import_file_id = Column(
        Integer,
        ForeignKey("import_file.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    extraction_run_id = Column(
        Integer,
        ForeignKey("extraction_run.id", ondelete="RESTRICT"),
        nullable=True,
    )
    issue_type = Column(String(40), nullable=False, index=True)
    source_code = Column(String(50), nullable=False, index=True)
    raw_value = Column(Text, nullable=True)
    affected_row_count = Column(Integer, nullable=False, default=0)
    affected_amount = Column(Numeric(14, 2), nullable=False, default=Decimal("0.00"))
    status = Column(String(20), nullable=False, default="open", index=True)
    resolved_by = Column(String(50), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
