from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from decimal import Decimal
from hashlib import sha256
from typing import Literal

from sqlalchemy.orm import Session

from backend.app.domain.extraction_profiles import ProfileDefinition, get_profile
from backend.app.models.batch import ReconciliationBatch
from backend.app.models.extraction import ExtractionRun
from backend.app.models.import_file import ImportFile
from backend.app.models.raw_data import RawData
from backend.app.services.workbook_preflight import preflight_workbook
from backend.app.services.extraction_engine import extract_current_batch_rows
from backend.app.services.workbook_io import load_data_workbook


@dataclass(frozen=True)
class ImportWorkbookCommand:
    batch_id: int
    filename: str
    content: bytes
    profile_code: str
    store_id: int | None
    actor: str


@dataclass(frozen=True)
class ImportOutcome:
    status: Literal["imported", "duplicate", "attention_required"]
    import_file_id: int
    extraction_run_id: int | None


class BatchClosedError(ValueError):
    """已关账批次不允许继续导入。"""


def calculate_content_hash(content: bytes) -> str:
    return sha256(content).hexdigest()


def _json_safe(value: object) -> object:
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _unique_headers(values: tuple[object, ...]) -> list[str]:
    headers: list[str] = []
    counts: dict[str, int] = {}
    for index, value in enumerate(values, start=1):
        base = str(value).strip() if value not in (None, "") else f"column_{index}"
        counts[base] = counts.get(base, 0) + 1
        headers.append(base if counts[base] == 1 else f"{base}_{counts[base]}")
    return headers


def _persist_raw_rows(
    db: Session,
    import_file_id: int,
    content: bytes,
    profile: ProfileDefinition,
) -> int:
    workbook = load_data_workbook(content)
    try:
        sheet_name = next(name for name in profile.sheet_names if name in workbook.sheetnames)
        sheet = workbook[sheet_name]
        header_values = next(
            sheet.iter_rows(
                min_row=profile.header_row,
                max_row=profile.header_row,
                values_only=True,
            )
        )
        headers = _unique_headers(header_values)
        row_count = 0
        for excel_row_number, values in enumerate(
            sheet.iter_rows(min_row=profile.header_row + 1, values_only=True),
            start=profile.header_row + 1,
        ):
            if not any(value not in (None, "") for value in values):
                continue
            content_row = {
                header: _json_safe(values[index] if index < len(values) else None)
                for index, header in enumerate(headers)
            }
            db.add(
                RawData(
                    import_file_id=import_file_id,
                    row_index=excel_row_number,
                    data_source=profile.input_source,
                    content=content_row,
                )
            )
            row_count += 1
        db.flush()
        return row_count
    finally:
        workbook.close()


def import_workbook(db: Session, command: ImportWorkbookCommand) -> ImportOutcome:
    clean_filename = command.filename.strip()
    clean_actor = command.actor.strip()
    if not clean_filename:
        raise ValueError("文件名不能为空")
    if not clean_actor:
        raise ValueError("导入必须提供操作人")

    content_hash = calculate_content_hash(command.content)
    batch = db.get(ReconciliationBatch, command.batch_id)
    if batch is None:
        raise ValueError(f"对账批次不存在: {command.batch_id}")
    if batch.status == "closed":
        raise BatchClosedError("已关账批次不允许导入文件")

    duplicate = (
        db.query(ImportFile)
        .filter(
            ImportFile.batch_id == batch.id,
            ImportFile.content_hash == content_hash,
            ImportFile.is_current.is_(True),
        )
        .first()
    )
    if duplicate is not None:
        return ImportOutcome(
            status="duplicate",
            import_file_id=duplicate.id,
            extraction_run_id=None,
        )

    profile = get_profile(command.profile_code)
    preflight_workbook(
        command.content,
        profile_code=profile.code,
        business_date=batch.business_date,
        store_id=command.store_id,
    )

    try:
        with db.begin_nested():
            import_file = ImportFile(
                filename=clean_filename,
                data_source=profile.input_source,
                upload_status="pending",
                row_count=0,
                store_id=command.store_id,
                batch_id=batch.id,
                content_hash=content_hash,
                file_size=len(command.content),
                profile_code=profile.code,
                profile_version=profile.version,
                is_current=True,
            )
            db.add(import_file)
            db.flush()

            row_count = _persist_raw_rows(
                db,
                import_file_id=import_file.id,
                content=command.content,
                profile=profile,
            )
            now = datetime.now(UTC)
            extraction_run = ExtractionRun(
                import_file_id=import_file.id,
                profile_code=profile.code,
                profile_version=profile.version,
                status="pending",
                started_at=now,
                raw_row_count=row_count,
                output_row_count=0,
                error_row_count=0,
                is_current=True,
            )
            db.add(extraction_run)
            import_file.row_count = row_count
            db.flush()
            summary = extract_current_batch_rows(db, extraction_run.id)

        db.commit()
        return ImportOutcome(
            status="attention_required" if summary.issue_count else "imported",
            import_file_id=import_file.id,
            extraction_run_id=extraction_run.id,
        )
    except Exception:
        db.rollback()
        raise
