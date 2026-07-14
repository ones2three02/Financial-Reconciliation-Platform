from pydantic import BaseModel, ConfigDict
from datetime import date, datetime
from typing import Optional
from decimal import Decimal

class CleanDataBase(BaseModel):
    raw_data_id: int
    import_file_id: int
    trade_date: date
    original_store_name: str
    standard_store_name: Optional[str] = None
    amount: Decimal
    source: str
    is_valid: Optional[bool] = True
    clean_status: Optional[str] = "cleaned"
    error_message: Optional[str] = None

class CleanDataCreate(CleanDataBase):
    pass

class CleanData(CleanDataBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
