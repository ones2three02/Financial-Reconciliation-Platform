from sqlalchemy import Column, Integer, String, Boolean, DateTime
from backend.app.core.db import Base
from backend.app.core.time import utc_now_naive

class FieldMapping(Base):
    __tablename__ = "field_mapping"

    id = Column(Integer, primary_key=True, index=True)
    data_source = Column(String(50), nullable=False, index=True)  # 输入来源，例如 tonglian、store_finance
    target_field = Column(String(50), nullable=False)  # 标准字段，例如 trade_date、payment_method
    source_column = Column(String(100), nullable=False)  # Excel column header name
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utc_now_naive)
    updated_at = Column(DateTime, default=utc_now_naive, onupdate=utc_now_naive)
