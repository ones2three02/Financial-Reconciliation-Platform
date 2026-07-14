from datetime import UTC, datetime

from sqlalchemy.orm import Session

from backend.app.models.audit import AuditEvent
from backend.app.models.batch import ReconciliationBatch
from backend.app.models.quality_issue import DataQualityIssue
from backend.app.services.reconciliation_service import reconcile_batch


class BatchNotClosableError(ValueError):
    """批次尚未满足关账门禁。"""


def _get_batch(db: Session, batch_id: int) -> ReconciliationBatch:
    batch = db.get(ReconciliationBatch, batch_id)
    if batch is None:
        raise ValueError(f"对账批次不存在: {batch_id}")
    return batch


def close_batch(db: Session, batch_id: int, actor: str) -> ReconciliationBatch:
    batch = _get_batch(db, batch_id)
    clean_actor = actor.strip()
    if not clean_actor:
        raise ValueError("关账必须提供操作人")
    if batch.status == "closed":
        raise BatchNotClosableError("批次已经关账")

    # 关账前强制刷新完整性与差异门禁，避免依赖过期的批次状态。
    reconcile_batch(db, batch.id)
    open_issue = (
        db.query(DataQualityIssue)
        .filter(
            DataQualityIssue.batch_id == batch.id,
            DataQualityIssue.status == "open",
        )
        .order_by(DataQualityIssue.id)
        .first()
    )
    if open_issue is not None:
        if open_issue.issue_type == "unknown_store":
            raise BatchNotClosableError("批次仍有待确认门店，不能关账")
        raise BatchNotClosableError("批次仍有未解决的数据质量问题，不能关账")
    if batch.status != "ready_to_close":
        raise BatchNotClosableError("批次尚未满足完整性或差异处理要求")

    closed_at = datetime.now(UTC)
    batch.status = "closed"
    batch.closed_by = clean_actor
    batch.closed_at = closed_at
    db.add(
        AuditEvent(
            batch_id=batch.id,
            event_type="batch_closed",
            actor=clean_actor,
            entity_type="reconciliation_batch",
            entity_id=str(batch.id),
            event_data={"version": batch.version},
        )
    )
    db.flush()
    return batch


def reopen_batch(
    db: Session,
    batch_id: int,
    actor: str,
    reason: str,
) -> ReconciliationBatch:
    batch = _get_batch(db, batch_id)
    clean_actor = actor.strip()
    clean_reason = reason.strip()
    if not clean_actor:
        raise ValueError("重开必须提供操作人")
    if not clean_reason:
        raise ValueError("重开必须填写原因")
    if batch.status != "closed":
        raise ValueError("只有已关账批次可以重开")

    reopened_at = datetime.now(UTC)
    previous_version = batch.version
    batch.status = "attention_required"
    batch.version += 1
    batch.reopened_by = clean_actor
    batch.reopened_at = reopened_at
    batch.reopen_reason = clean_reason
    db.add(
        AuditEvent(
            batch_id=batch.id,
            event_type="batch_reopened",
            actor=clean_actor,
            entity_type="reconciliation_batch",
            entity_id=str(batch.id),
            event_data={
                "reason": clean_reason,
                "previous_version": previous_version,
                "new_version": batch.version,
            },
        )
    )
    db.flush()
    return batch
