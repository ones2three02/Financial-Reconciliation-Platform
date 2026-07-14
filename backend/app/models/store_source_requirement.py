from datetime import UTC, date, datetime

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String, UniqueConstraint

from backend.app.core.db import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class StoreSourceRequirement(Base):
    __tablename__ = "store_source_requirement"
    __table_args__ = (
        UniqueConstraint(
            "store_id",
            "source_code",
            "effective_from",
            name="uq_store_source_requirement_period",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(
        Integer,
        ForeignKey("store.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    source_code = Column(String(50), nullable=False, index=True)
    requirement = Column(String(20), nullable=False, default="required")
    effective_from = Column(Date, nullable=False, default=date(1970, 1, 1))
    effective_to = Column(Date, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
