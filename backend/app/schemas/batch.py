from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from backend.app.schemas.reconciliation import ReconciliationResult


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


class BatchImportFileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    data_source: str
    upload_status: str
    error_message: str | None = None
    row_count: int
    uploaded_at: datetime
    store_id: int | None = None
    profile_code: str | None = None
    profile_version: int | None = None
    supersedes_file_id: int | None = None
    is_current: bool


class SourceCoverageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    store_id: int
    source_code: str
    status: str
    evidence_type: str | None = None
    amount: Decimal
    file_count: int
    valid_row_count: int
    error_row_count: int
    updated_at: datetime


class DataQualityIssueRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    import_file_id: int | None = None
    issue_type: str
    source_code: str
    raw_value: str | None = None
    affected_row_count: int
    affected_amount: Decimal
    status: str
    created_at: datetime


class BatchDetailRead(BaseModel):
    batch: BatchRead
    import_files: list[BatchImportFileRead]
    coverages: list[SourceCoverageRead]
    quality_issues: list[DataQualityIssueRead]
    results: list[ReconciliationResult]
