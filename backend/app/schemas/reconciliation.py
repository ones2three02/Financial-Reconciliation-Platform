from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional, List
from decimal import Decimal

class ReconciliationResultBase(BaseModel):
    trade_date: date
    standard_store_name: str
    tonglian_amount: Decimal = Decimal("0.00")
    meituan_amount: Decimal = Decimal("0.00")
    douyin_amount: Decimal = Decimal("0.00")
    cash_amount: Decimal = Decimal("0.00")
    sales_amount: Decimal = Decimal("0.00")
    expected_amount: Decimal = Decimal("0.00")
    actual_amount: Decimal = Decimal("0.00")
    difference: Decimal = Decimal("0.00")
    status: str = "consistent"
    remarks: Optional[str] = None
    is_resolved: bool = False
    resolved_by: Optional[str] = None
    resolved_at: Optional[datetime] = None

class ReconciliationResultUpdate(BaseModel):
    remarks: Optional[str] = None
    is_resolved: Optional[bool] = None
    resolved_by: Optional[str] = None

class ReconciliationResult(ReconciliationResultBase):
    id: int
    batch_id: Optional[int] = None
    store_id: Optional[int] = None
    formula_version: Optional[int] = None
    completeness_status: Optional[str] = None
    calculated_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class DashboardSummary(BaseModel):
    total_stores: int
    consistent_count: int
    discrepancy_count: int
    missing_data_count: int
    total_sales: Decimal
    total_tonglian: Decimal
    total_difference: Decimal
