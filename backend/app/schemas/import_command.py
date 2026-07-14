from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class ImportOutcomeRead(BaseModel):
    status: Literal["imported", "duplicate", "attention_required"]
    import_file_id: int
    extraction_run_id: int | None


class _ReasonRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500)

    @field_validator("reason", mode="before")
    @classmethod
    def strip_reason(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class InvalidateImportRequest(_ReasonRequest):
    pass


class RestoreImportRequest(_ReasonRequest):
    pass


class ResetBatchCurrentDataRequest(_ReasonRequest):
    confirmation_date: date


class ImportVersionActionRead(BaseModel):
    status: Literal["invalidated", "reset"]
    batch_id: int
    file_id: int | None = None
