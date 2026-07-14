from decimal import Decimal

from sqlalchemy import distinct, func
from sqlalchemy.orm import Session

from backend.app.models.batch import ReconciliationBatch
from backend.app.models.clean_data import CleanData
from backend.app.models.coverage import SourceCoverage
from backend.app.models.extraction import ExtractionRun
from backend.app.models.import_file import ImportFile


def upsert_coverage(
    db: Session,
    *,
    batch_id: int,
    business_date,
    store_id: int,
    source_code: str,
    status: str,
    evidence_type: str | None,
    amount: Decimal,
    file_count: int,
    valid_row_count: int,
    error_row_count: int,
    extraction_run_id: int | None,
) -> SourceCoverage:
    coverage = (
        db.query(SourceCoverage)
        .filter(
            SourceCoverage.batch_id == batch_id,
            SourceCoverage.store_id == store_id,
            SourceCoverage.source_code == source_code,
        )
        .first()
    )
    if coverage is None:
        coverage = SourceCoverage(
            batch_id=batch_id,
            business_date=business_date,
            store_id=store_id,
            source_code=source_code,
        )
        db.add(coverage)

    coverage.status = status
    coverage.evidence_type = evidence_type
    coverage.amount = amount
    coverage.file_count = file_count
    coverage.valid_row_count = valid_row_count
    coverage.error_row_count = error_row_count
    coverage.extraction_run_id = extraction_run_id
    db.flush()
    return coverage


def rebuild_scope_coverage(
    db: Session,
    *,
    batch: ReconciliationBatch,
    store_id: int,
    source_code: str,
) -> SourceCoverage:
    """依据当前有效数据重建单个门店来源覆盖，避免历史版本继续计数。"""
    amount, row_count, file_count, extraction_run_id = (
        db.query(
            func.sum(CleanData.amount),
            func.count(CleanData.id),
            func.count(distinct(CleanData.import_file_id)),
            func.max(CleanData.extraction_run_id),
        )
        .filter(
            CleanData.batch_id == batch.id,
            CleanData.store_id == store_id,
            CleanData.source == source_code,
            CleanData.is_current.is_(True),
            CleanData.is_valid.is_(True),
        )
        .one()
    )
    row_count = int(row_count or 0)
    file_count = int(file_count or 0)
    amount = Decimal(str(amount or 0))

    if row_count:
        status = "present_data"
        evidence_type = "data_rows"
    else:
        finance_files = []
        if source_code in {"sales", "cash"}:
            finance_files = (
                db.query(ImportFile)
                .filter(
                    ImportFile.batch_id == batch.id,
                    ImportFile.store_id == store_id,
                    ImportFile.profile_code == "store_finance_v1",
                    ImportFile.is_current.is_(True),
                )
                .all()
            )
        if finance_files:
            status = "present_zero"
            evidence_type = "file_scope"
            file_count = len(finance_files)
            latest_run = (
                db.query(ExtractionRun)
                .filter(
                    ExtractionRun.import_file_id.in_([row.id for row in finance_files]),
                    ExtractionRun.is_current.is_(True),
                )
                .order_by(ExtractionRun.id.desc())
                .first()
            )
            extraction_run_id = latest_run.id if latest_run else None
        else:
            status = "missing"
            evidence_type = None
            file_count = 0
            extraction_run_id = None

    return upsert_coverage(
        db,
        batch_id=batch.id,
        business_date=batch.business_date,
        store_id=store_id,
        source_code=source_code,
        status=status,
        evidence_type=evidence_type,
        amount=amount,
        file_count=file_count,
        valid_row_count=row_count,
        error_row_count=0,
        extraction_run_id=extraction_run_id,
    )
