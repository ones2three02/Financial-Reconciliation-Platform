from sqlalchemy import Column, Integer, String, Boolean, DateTime
from datetime import datetime
from backend.app.core.db import Base

class FieldMapping(Base):
    __tablename__ = "field_mapping"

    id = Column(Integer, primary_key=True, index=True)
    data_source = Column(String(50), nullable=False, index=True)  # "tonglian", "meituan", "douyin", "cash", "sales"
    target_field = Column(String(50), nullable=False)  # "trade_date", "store_name", "amount"
    source_column = Column(String(100), nullable=False)  # Excel column header name
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
