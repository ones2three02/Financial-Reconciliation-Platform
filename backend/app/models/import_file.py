from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from backend.app.core.db import Base

class ImportFile(Base):
    __tablename__ = "import_file"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    data_source = Column(String(50), nullable=False, index=True)  # "tonglian", "meituan", "douyin", "cash", "sales"
    upload_status = Column(String(20), default="pending")  # "pending", "parsed", "failed"
    error_message = Column(Text, nullable=True)
    row_count = Column(Integer, default=0)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    store_id = Column(
        Integer,
        ForeignKey("store.id", ondelete="RESTRICT"),
        nullable=True,
    )
    batch_id = Column(
        Integer,
        ForeignKey("reconciliation_batch.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    content_hash = Column(String(64), nullable=True, index=True)
    file_size = Column(Integer, nullable=True)
    profile_code = Column(String(50), nullable=True)
    profile_version = Column(Integer, nullable=True)
    supersedes_file_id = Column(
        Integer,
        ForeignKey("import_file.id", ondelete="RESTRICT"),
        nullable=True,
    )
    is_current = Column(Boolean, nullable=False, default=True)

    # Relationships
    raw_rows = relationship("RawData", back_populates="import_file", cascade="all, delete-orphan")
    clean_rows = relationship("CleanData", back_populates="import_file", cascade="all, delete-orphan")
