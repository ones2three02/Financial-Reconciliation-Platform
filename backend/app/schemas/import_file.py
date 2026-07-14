from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional

class ImportFileBase(BaseModel):
    filename: str
    data_source: str
    upload_status: Optional[str] = "pending"
    error_message: Optional[str] = None
    row_count: Optional[int] = 0
    store_id: Optional[int] = None

class ImportFileCreate(ImportFileBase):
    pass

class ImportFile(ImportFileBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    uploaded_at: datetime
    profile_code: Optional[str] = None
    profile_version: Optional[int] = None
    supersedes_file_id: Optional[int] = None
    is_current: bool
