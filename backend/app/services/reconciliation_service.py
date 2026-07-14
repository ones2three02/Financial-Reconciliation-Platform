from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import or_
from sqlalchemy.orm import Session

from backend.app.models.audit import AuditEvent
from backend.app.models.batch import ReconciliationBatch
from backend.app.models.coverage import SourceCoverage
from backend.app.models.quality_issue import DataQualityIssue
from backend.app.models.reconciliation import ReconciliationResult
from backend.app.models.store import Store
from backend.app.models.store_source_requirement import StoreSourceRequirement
from backend.app.services.coverage_service import upsert_coverage


SOURCE_CODES = ("tonglian", "meituan", "douyin", "cash", "sales")
COMPLETE_COVERAGE_STATUSES = {"present_data", "present_zero"}


def _get_batch(db: Session, batch_id: int) -> ReconciliationBatch:
    batch = db.get(ReconciliationBatch, batch_id)
    if batch is None:
        raise ValueError(f"对账批次不存在: {batch_id}")
    return batch


def _source_requirement(
    db: Session,
    *,
    store_id: int,
    source_code: str,
    business_date,
) -> str:
    configured = (
        db.query(StoreSourceRequirement)
        .filter(
            StoreSourceRequirement.store_id == store_id,
            StoreSourceRequirement.source_code == source_code,
            StoreSourceRequirement.effective_from <= business_date,
            or_(
                StoreSourceRequirement.effective_to.is_(None),
                StoreSourceRequirement.effective_to >= business_date,
            ),
        )
        .order_by(StoreSourceRequirement.effective_from.desc())
        .first()
    )
    return configured.requirement if configured is not None else "required"


def _coverage_for_source(
    db: Session,
    *,
    batch: ReconciliationBatch,
    store_id: int,
    source_code: str,
) -> SourceCoverage | None:
    return (
        db.query(SourceCoverage)
        .filter(
            SourceCoverage.batch_id == batch.id,
            SourceCoverage.store_id == store_id,
            SourceCoverage.source_code == source_code,
        )
        .first()
    )


def confirm_zero(
    db: Session,
    *,
    batch_id: int,
    store_id: int,
    source_code: str,
    actor: str,
) -> SourceCoverage:
    batch = _get_batch(db, batch_id)
    clean_actor = actor.strip()
    clean_source = source_code.strip()
    if not clean_actor:
        raise ValueError("确认零收入必须提供操作人")
    if clean_source not in SOURCE_CODES:
        raise ValueError(f"不支持的收入来源: {clean_source}")
    if batch.status == "closed":
        raise ValueError("已关账批次不能确认零收入")
    store = db.get(Store, store_id)
    if store is None or not store.is_active:
        raise ValueError(f"标准门店不存在或已停用: {store_id}")
    if _source_requirement(
        db,
        store_id=store_id,
        source_code=clean_source,
        business_date=batch.business_date,
    ) == "not_required":
        raise ValueError("该门店来源已配置为不需要，无需确认零收入")

    existing = _coverage_for_source(
        db,
        batch=batch,
        store_id=store_id,
        source_code=clean_source,
    )
    if existing is not None and existing.status == "present_data":
        raise ValueError("该门店来源已有有效数据，不能确认零收入")
    coverage = upsert_coverage(
        db,
        batch_id=batch.id,
        business_date=batch.business_date,
        store_id=store_id,
        source_code=clean_source,
        status="present_zero",
        evidence_type="manual_zero_confirmation",
        amount=Decimal("0.00"),
        file_count=0,
        valid_row_count=0,
        error_row_count=0,
        extraction_run_id=None,
    )
    db.add(
        AuditEvent(
            batch_id=batch.id,
            event_type="source_zero_confirmed",
            actor=clean_actor,
            entity_type="source_coverage",
            entity_id=f"{batch.id}:{store_id}:{clean_source}",
            event_data={
                "store_id": store_id,
                "source_code": clean_source,
                "business_date": batch.business_date.isoformat(),
            },
        )
    )
    db.flush()
    return coverage


def revoke_zero(
    db: Session,
    *,
    batch_id: int,
    store_id: int,
    source_code: str,
    reason: str,
    actor: str,
) -> SourceCoverage:
    batch = _get_batch(db, batch_id)
    clean_actor = actor.strip()
    clean_source = source_code.strip()
    clean_reason = reason.strip()
    if not clean_actor:
        raise ValueError("撤销零收入确认必须提供操作人")
    if not clean_reason:
        raise ValueError("撤销零收入确认必须填写原因")
    if len(clean_reason) > 500:
        raise ValueError("撤销原因不能超过 500 个字符")
    if clean_source not in SOURCE_CODES:
        raise ValueError(f"不支持的收入来源: {clean_source}")
    if batch.status == "closed":
        raise ValueError("已关账批次不能撤销零收入确认，请先重开")

    coverage = _coverage_for_source(
        db,
        batch=batch,
        store_id=store_id,
        source_code=clean_source,
    )
    if (
        coverage is None
        or coverage.status != "present_zero"
        or coverage.evidence_type != "manual_zero_confirmation"
    ):
        raise ValueError("只能撤销人工确认的零收入")

    coverage = upsert_coverage(
        db,
        batch_id=batch.id,
        business_date=batch.business_date,
        store_id=store_id,
        source_code=clean_source,
        status="missing",
        evidence_type=None,
        amount=Decimal("0.00"),
        file_count=0,
        valid_row_count=0,
        error_row_count=0,
        extraction_run_id=None,
    )
    db.add(
        AuditEvent(
            batch_id=batch.id,
            event_type="source_zero_confirmation_revoked",
            actor=clean_actor,
            entity_type="source_coverage",
            entity_id=f"{batch.id}:{store_id}:{clean_source}",
            event_data={
                "store_id": store_id,
                "source_code": clean_source,
                "business_date": batch.business_date.isoformat(),
                "reason": clean_reason,
            },
        )
    )
    reconcile_batch(db, batch.id)
    db.flush()
    return coverage


def reconcile_batch(db: Session, batch_id: int) -> list[ReconciliationResult]:
    batch = _get_batch(db, batch_id)
    if batch.status == "closed":
        raise ValueError("已关账批次不能重新对账，请先重开")

    has_open_quality_issue = (
        db.query(DataQualityIssue)
        .filter(
            DataQualityIssue.batch_id == batch.id,
            DataQualityIssue.status == "open",
        )
        .count()
        > 0
    )
    stores = (
        db.query(Store)
        .filter(Store.is_active.is_(True))
        .order_by(Store.id)
        .all()
    )
    results: list[ReconciliationResult] = []
    all_closeable = bool(stores) and not has_open_quality_issue
    calculated_at = datetime.now(UTC)

    for store in stores:
        amounts = {source: Decimal("0.00") for source in SOURCE_CODES}
        incomplete_sources: list[str] = []
        for source_code in SOURCE_CODES:
            requirement = _source_requirement(
                db,
                store_id=store.id,
                source_code=source_code,
                business_date=batch.business_date,
            )
            if requirement == "not_required":
                continue
            coverage = _coverage_for_source(
                db,
                batch=batch,
                store_id=store.id,
                source_code=source_code,
            )
            if coverage is None:
                coverage = upsert_coverage(
                    db,
                    batch_id=batch.id,
                    business_date=batch.business_date,
                    store_id=store.id,
                    source_code=source_code,
                    status="missing",
                    evidence_type=None,
                    amount=Decimal("0.00"),
                    file_count=0,
                    valid_row_count=0,
                    error_row_count=0,
                    extraction_run_id=None,
                )
            if coverage.status not in COMPLETE_COVERAGE_STATUSES:
                incomplete_sources.append(source_code)
                continue
            amounts[source_code] = Decimal(str(coverage.amount or 0))

        expected = amounts["tonglian"] + amounts["meituan"] + amounts["douyin"]
        actual = amounts["sales"] - amounts["cash"]
        difference = expected - actual
        is_complete = not incomplete_sources and not has_open_quality_issue
        status = (
            "incomplete"
            if not is_complete
            else "consistent" if difference == Decimal("0.00") else "discrepancy"
        )

        result = (
            db.query(ReconciliationResult)
            .filter(
                ReconciliationResult.batch_id == batch.id,
                ReconciliationResult.store_id == store.id,
            )
            .first()
        )
        if result is None:
            result = ReconciliationResult(
                batch_id=batch.id,
                store_id=store.id,
                trade_date=batch.business_date,
                standard_store_name=store.name,
            )
            db.add(result)
        result.standard_store_name = store.name
        result.tonglian_amount = amounts["tonglian"]
        result.meituan_amount = amounts["meituan"]
        result.douyin_amount = amounts["douyin"]
        result.cash_amount = amounts["cash"]
        result.sales_amount = amounts["sales"]
        result.expected_amount = expected
        result.actual_amount = actual
        result.difference = difference
        result.status = status
        result.formula_version = 1
        result.completeness_status = "complete" if is_complete else "incomplete"
        result.calculated_at = calculated_at
        if status == "consistent":
            result.is_resolved = False
            result.remarks = None
            result.resolved_by = None
            result.resolved_at = None
        db.flush()
        results.append(result)

        discrepancy_handled = status != "discrepancy" or bool(
            result.is_resolved or (result.remarks and result.remarks.strip())
        )
        if not is_complete or not discrepancy_handled:
            all_closeable = False

    batch.status = "ready_to_close" if all_closeable else "attention_required"
    db.flush()
    return results
