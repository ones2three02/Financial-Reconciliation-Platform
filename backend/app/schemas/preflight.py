from datetime import date

from pydantic import BaseModel, ConfigDict


class PreflightResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    profile_code: str
    profile_version: int
    sheet_name: str
    business_date: date
    store_id: int | None
    output_sources: list[str]
    total_data_rows: int
    matching_row_count: int
    date_range_start: date | None
    date_range_end: date | None
    detected_store_names: list[str]
