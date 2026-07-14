from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String

from backend.app.core.db import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class AuditEvent(Base):
    __tablename__ = "audit_event"

    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(
        Integer,
        ForeignKey("reconciliation_batch.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    event_type = Column(String(50), nullable=False, index=True)
    actor = Column(String(50), nullable=False)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(String(100), nullable=False)
    event_data = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
