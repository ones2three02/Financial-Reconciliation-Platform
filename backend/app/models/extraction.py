from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint

from backend.app.core.db import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class ExtractionProfile(Base):
    __tablename__ = "extraction_profile"
    __table_args__ = (
        UniqueConstraint("code", "version", name="uq_extraction_profile_code_version"),
    )

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), nullable=False, index=True)
    version = Column(Integer, nullable=False)
    config = Column(JSON, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)


class ExtractionRun(Base):
    __tablename__ = "extraction_run"

    id = Column(Integer, primary_key=True, index=True)
    import_file_id = Column(
        Integer,
        ForeignKey("import_file.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    profile_code = Column(String(50), nullable=False)
    profile_version = Column(Integer, nullable=False)
    status = Column(String(30), nullable=False, default="pending")
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    raw_row_count = Column(Integer, nullable=False, default=0)
    output_row_count = Column(Integer, nullable=False, default=0)
    error_row_count = Column(Integer, nullable=False, default=0)
    error_summary = Column(Text, nullable=True)
    is_current = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
