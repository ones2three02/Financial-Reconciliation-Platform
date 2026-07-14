from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional

class FieldMappingBase(BaseModel):
    data_source: str
    target_field: str
    source_column: str
    is_active: Optional[bool] = True

class FieldMappingCreate(FieldMappingBase):
    pass

class FieldMappingUpdate(BaseModel):
    data_source: Optional[str] = None
    target_field: Optional[str] = None
    source_column: Optional[str] = None
    is_active: Optional[bool] = None

class FieldMapping(FieldMappingBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
