from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from backend.app.models.quality_issue import DataQualityIssue


def record_unknown_store_issue(
    db: Session,
    *,
    batch_id: int,
    import_file_id: int | None,
    extraction_run_id: int | None,
    source_code: str,
    raw_name: str,
    affected_amount: Decimal,
) -> DataQualityIssue:
    issue = (
        db.query(DataQualityIssue)
        .filter(
            DataQualityIssue.batch_id == batch_id,
            DataQualityIssue.import_file_id == import_file_id,
            DataQualityIssue.extraction_run_id == extraction_run_id,
            DataQualityIssue.issue_type == "unknown_store",
            DataQualityIssue.source_code == source_code,
            DataQualityIssue.raw_value == raw_name,
            DataQualityIssue.status == "open",
        )
        .first()
    )
    if issue is None:
        issue = DataQualityIssue(
            batch_id=batch_id,
            import_file_id=import_file_id,
            extraction_run_id=extraction_run_id,
            issue_type="unknown_store",
            source_code=source_code,
            raw_value=raw_name,
            affected_row_count=1,
            affected_amount=affected_amount,
            status="open",
        )
        db.add(issue)
    else:
        issue.affected_row_count += 1
        issue.affected_amount += affected_amount
    db.flush()
    return issue


def resolve_unknown_store_issues(
    db: Session,
    *,
    source_code: str,
    raw_name: str,
    actor: str,
) -> list[int]:
    issues = (
        db.query(DataQualityIssue)
        .filter(
            DataQualityIssue.issue_type == "unknown_store",
            DataQualityIssue.source_code == source_code,
            DataQualityIssue.raw_value == raw_name,
            DataQualityIssue.status == "open",
        )
        .all()
    )
    resolved_at = datetime.now(UTC)
    run_ids: set[int] = set()
    for issue in issues:
        issue.status = "resolved"
        issue.resolved_by = actor
        issue.resolved_at = resolved_at
        if issue.extraction_run_id is not None:
            run_ids.add(issue.extraction_run_id)
    db.flush()
    return sorted(run_ids)
