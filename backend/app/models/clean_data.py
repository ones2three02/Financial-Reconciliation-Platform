from sqlalchemy import Column, Integer, String, Date, Numeric, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from backend.app.core.db import Base

class CleanData(Base):
    __tablename__ = "clean_data"

    id = Column(Integer, primary_key=True, index=True)
    raw_data_id = Column(Integer, ForeignKey("raw_data.id", ondelete="CASCADE"), nullable=False)
    import_file_id = Column(Integer, ForeignKey("import_file.id", ondelete="CASCADE"), nullable=False)
    trade_date = Column(Date, nullable=False, index=True)
    original_store_name = Column(String(100), nullable=False)
    standard_store_name = Column(String(100), nullable=True, index=True)
    amount = Column(Numeric(12, 2), nullable=False)
    source = Column(String(50), nullable=False, index=True)  # "tonglian", "meituan", "douyin", "cash", "sales"
    is_valid = Column(Boolean, default=True)
    clean_status = Column(String(20), default="cleaned")  # "cleaned", "pending_store_mapping", "error"
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    batch_id = Column(
        Integer,
        ForeignKey("reconciliation_batch.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    store_id = Column(
        Integer,
        ForeignKey("store.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    extraction_run_id = Column(
        Integer,
        ForeignKey("extraction_run.id", ondelete="RESTRICT"),
        nullable=True,
    )
    profile_code = Column(String(50), nullable=True)
    profile_version = Column(Integer, nullable=True)
    is_current = Column(Boolean, nullable=False, default=True)

    # Relationships
    raw_data = relationship("RawData", back_populates="clean_rows")
    import_file = relationship("ImportFile", back_populates="clean_rows")
