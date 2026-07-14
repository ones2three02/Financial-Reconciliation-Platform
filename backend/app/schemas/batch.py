from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class BatchCreate(BaseModel):
    business_date: date


class BatchRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    business_date: date
    status: str
    version: int
    created_by: str
    created_at: datetime
    closed_by: str | None = None
    closed_at: datetime | None = None
    reopened_by: str | None = None
    reopened_at: datetime | None = None
    reopen_reason: str | None = None


class ConfirmZeroRequest(BaseModel):
    store_id: int
    source_code: str = Field(min_length=1, max_length=50)


class BatchReopenRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500)
