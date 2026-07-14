from typing import Literal

from pydantic import BaseModel


class ImportOutcomeRead(BaseModel):
    status: Literal["imported", "duplicate", "attention_required"]
    import_file_id: int
    extraction_run_id: int | None
