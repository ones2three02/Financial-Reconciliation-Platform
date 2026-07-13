from sqlalchemy import Column, Integer, String, Date, Numeric, Boolean, Text, DateTime
from datetime import datetime
from backend.app.core.db import Base

class ReconciliationResult(Base):
    __tablename__ = "reconciliation_result"

    id = Column(Integer, primary_key=True, index=True)
    trade_date = Column(Date, nullable=False, index=True)
    standard_store_name = Column(String(100), nullable=False, index=True)
    
    # Details from each source
    tonglian_amount = Column(Numeric(12, 2), default=0.00)
    meituan_amount = Column(Numeric(12, 2), default=0.00)
    douyin_amount = Column(Numeric(12, 2), default=0.00)
    cash_amount = Column(Numeric(12, 2), default=0.00)
    sales_amount = Column(Numeric(12, 2), default=0.00)
    
    # Derived amounts
    # expected = tonglian + meituan + douyin
    # actual = sales - cash
    expected_amount = Column(Numeric(12, 2), default=0.00)
    actual_amount = Column(Numeric(12, 2), default=0.00)
    difference = Column(Numeric(12, 2), default=0.00)
    
    status = Column(String(20), default="consistent")  # "consistent", "discrepancy", "missing_data"
    
    # Manual resolution details
    remarks = Column(Text, nullable=True)
    is_resolved = Column(Boolean, default=False)
    resolved_by = Column(String(50), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
