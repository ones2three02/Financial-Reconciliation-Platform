from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class ImportFileBase(BaseModel):
    filename: str
    data_source: str
    upload_status: Optional[str] = "pending"
    error_message: Optional[str] = None
    row_count: Optional[int] = 0

class ImportFileCreate(ImportFileBase):
    pass

class ImportFile(ImportFileBase):
    id: int
    uploaded_at: datetime

    class Config:
        from_attributes = True
