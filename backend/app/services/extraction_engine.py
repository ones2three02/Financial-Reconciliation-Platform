from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import distinct, func
from sqlalchemy.orm import Session

from backend.app.models.batch import ReconciliationBatch
from backend.app.models.clean_data import CleanData
from backend.app.models.extraction import ExtractionRun
from backend.app.models.import_file import ImportFile
from backend.app.models.raw_data import RawData
from backend.app.models.store import Store
from backend.app.services.cleaner import clean_amount, clean_date
from backend.app.services.coverage_service import upsert_coverage


@dataclass(frozen=True)
class ExtractionSummary:
    extraction_run_id: int
    source_amounts: dict[str, Decimal]
    clean_row_count: int
    issue_count: int


def _scope_totals(
    db: Session,
    *,
    batch_id: int,
    store_id: int,
    source_code: str,
) -> tuple[Decimal, int, int]:
    amount, row_count, file_count = (
        db.query(
            func.sum(CleanData.amount),
            func.count(CleanData.id),
            func.count(distinct(CleanData.import_file_id)),
        )
        .filter(
            CleanData.batch_id == batch_id,
            CleanData.store_id == store_id,
            CleanData.source == source_code,
            CleanData.is_current.is_(True),
            CleanData.is_valid.is_(True),
        )
        .one()
    )
    return Decimal(str(amount or 0)), int(row_count or 0), int(file_count or 0)


def _refresh_finance_coverage(
    db: Session,
    *,
    batch: ReconciliationBatch,
    store_id: int,
    source_code: str,
    extraction_run_id: int,
) -> None:
    amount, row_count, file_count = _scope_totals(
        db,
        batch_id=batch.id,
        store_id=store_id,
        source_code=source_code,
    )
    has_rows = row_count > 0
    upsert_coverage(
        db,
        batch_id=batch.id,
        business_date=batch.business_date,
        store_id=store_id,
        source_code=source_code,
        status="present_data" if has_rows else "present_zero",
        evidence_type="data_rows" if has_rows else "file_scope",
        amount=amount,
        file_count=file_count if has_rows else 1,
        valid_row_count=row_count,
        error_row_count=0,
        extraction_run_id=extraction_run_id,
    )


def _extract_finance_rows(
    db: Session,
    *,
    extraction_run: ExtractionRun,
    import_file: ImportFile,
    batch: ReconciliationBatch,
    store: Store,
) -> ExtractionSummary:
    previous_rows = (
        db.query(CleanData)
        .filter(
            CleanData.extraction_run_id == extraction_run.id,
            CleanData.is_current.is_(True),
        )
        .all()
    )
    for previous in previous_rows:
        previous.is_current = False

    source_amounts = {
        "sales": Decimal("0.00"),
        "cash": Decimal("0.00"),
    }
    clean_row_count = 0
    raw_rows = (
        db.query(RawData)
        .filter(RawData.import_file_id == import_file.id)
        .order_by(RawData.row_index)
        .all()
    )
    for raw_row in raw_rows:
        content = raw_row.content or {}
        if clean_date(content.get("日期")) != batch.business_date:
            continue
        amount = clean_amount(content.get("金额"))
        payment_method = str(content.get("付款方式") or "").strip()
        common_fields = {
            "raw_data_id": raw_row.id,
            "import_file_id": import_file.id,
            "trade_date": batch.business_date,
            "original_store_name": store.name,
            "standard_store_name": store.name,
            "is_valid": True,
            "clean_status": "cleaned",
            "batch_id": batch.id,
            "store_id": store.id,
            "extraction_run_id": extraction_run.id,
            "profile_code": extraction_run.profile_code,
            "profile_version": extraction_run.profile_version,
            "is_current": True,
        }
        db.add(CleanData(amount=amount, source="sales", **common_fields))
        source_amounts["sales"] += amount
        clean_row_count += 1

        if payment_method == "现金":
            db.add(CleanData(amount=amount, source="cash", **common_fields))
            source_amounts["cash"] += amount
            clean_row_count += 1

    db.flush()
    for source_code in ("sales", "cash"):
        _refresh_finance_coverage(
            db,
            batch=batch,
            store_id=store.id,
            source_code=source_code,
            extraction_run_id=extraction_run.id,
        )

    extraction_run.status = "completed"
    extraction_run.output_row_count = clean_row_count
    extraction_run.error_row_count = 0
    extraction_run.finished_at = datetime.now(UTC)
    import_file.upload_status = "processed"
    db.flush()
    return ExtractionSummary(
        extraction_run_id=extraction_run.id,
        source_amounts=source_amounts,
        clean_row_count=clean_row_count,
        issue_count=0,
    )


def extract_current_batch_rows(
    db: Session,
    extraction_run_id: int,
) -> ExtractionSummary:
    extraction_run = db.get(ExtractionRun, extraction_run_id)
    if extraction_run is None:
        raise ValueError(f"提取运行不存在: {extraction_run_id}")
    import_file = db.get(ImportFile, extraction_run.import_file_id)
    if import_file is None or import_file.batch_id is None:
        raise ValueError("提取运行缺少有效导入文件或批次")
    batch = db.get(ReconciliationBatch, import_file.batch_id)
    if batch is None:
        raise ValueError("导入文件关联的批次不存在")

    if extraction_run.profile_code == "store_finance_v1":
        if import_file.store_id is None:
            raise ValueError("门店财务表缺少文件级标准门店")
        store = db.get(Store, import_file.store_id)
        if store is None:
            raise ValueError("门店财务表关联的标准门店不存在")
        return _extract_finance_rows(
            db,
            extraction_run=extraction_run,
            import_file=import_file,
            batch=batch,
            store=store,
        )

    raise ValueError(f"尚未实现的提取模板: {extraction_run.profile_code}")
