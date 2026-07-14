from decimal import Decimal

from sqlalchemy.orm import Session

from backend.app.models.coverage import SourceCoverage


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
