from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from backend.app.models.audit import AuditEvent
from backend.app.models.batch import ReconciliationBatch
from backend.app.models.clean_data import CleanData
from backend.app.models.coverage import SourceCoverage
from backend.app.models.extraction import ExtractionRun
from backend.app.models.import_file import ImportFile
from backend.app.models.quality_issue import DataQualityIssue
from backend.app.services.coverage_service import rebuild_scope_coverage
from backend.app.services.import_pipeline import (
    ImportOutcome,
    ImportWorkbookCommand,
    calculate_content_hash,
    import_workbook_in_transaction,
)
from backend.app.services.reconciliation_service import reconcile_batch


class ImportVersionNotFoundError(ValueError):
    """目标文件或批次不存在。"""


class ImportVersionConflictError(ValueError):
    """当前状态不允许执行版本操作。"""


def _clean_required(value: str, message: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(message)
    return cleaned


def _clean_reason(value: str, message: str) -> str:
    cleaned = _clean_required(value, message)
    if len(cleaned) > 500:
        raise ValueError("操作原因不能超过 500 个字符")
    return cleaned


def _current_file(db: Session, file_id: int) -> tuple[ImportFile, ReconciliationBatch]:
    candidate = db.get(ImportFile, file_id)
    if candidate is None or candidate.batch_id is None:
        raise ImportVersionNotFoundError("导入文件不存在")
    batch = (
        db.query(ReconciliationBatch)
        .filter(ReconciliationBatch.id == candidate.batch_id)
        .populate_existing()
        .with_for_update()
        .one_or_none()
    )
    if batch is None:
        raise ImportVersionNotFoundError("导入文件关联的对账批次不存在")
    import_file = (
        db.query(ImportFile)
        .filter(ImportFile.id == file_id)
        .populate_existing()
        .with_for_update()
        .one_or_none()
    )
    if import_file is None or not import_file.is_current:
        raise ImportVersionConflictError("该文件已不是当前版本，不能再次操作")
    if batch.status == "closed":
        raise ImportVersionConflictError("已关账批次必须先重开才能修改导入文件")
    return import_file, batch


def _file_scopes(db: Session, import_file: ImportFile) -> set[tuple[int, str]]:
    scopes = {
        (row.store_id, row.source)
        for row in db.query(CleanData.store_id, CleanData.source)
        .filter(
            CleanData.import_file_id == import_file.id,
            CleanData.store_id.is_not(None),
        )
        .distinct()
        .all()
    }
    if import_file.profile_code == "store_finance_v1" and import_file.store_id:
        scopes.update({(import_file.store_id, "sales"), (import_file.store_id, "cash")})
    return scopes


def _retire_file(db: Session, import_file: ImportFile, actor: str) -> None:
    now = datetime.now(UTC)
    import_file.is_current = False
    for run in db.query(ExtractionRun).filter(
        ExtractionRun.import_file_id == import_file.id,
        ExtractionRun.is_current.is_(True),
    ):
        run.is_current = False
    for row in db.query(CleanData).filter(
        CleanData.import_file_id == import_file.id,
        CleanData.is_current.is_(True),
    ):
        row.is_current = False
    for issue in db.query(DataQualityIssue).filter(
        DataQualityIssue.import_file_id == import_file.id,
        DataQualityIssue.status == "open",
    ):
        issue.status = "superseded"
        issue.resolved_by = actor
        issue.resolved_at = now
    db.flush()


def _refresh_scopes(
    db: Session,
    batch: ReconciliationBatch,
    scopes: set[tuple[int, str]],
) -> None:
    for store_id, source_code in sorted(scopes):
        rebuild_scope_coverage(
            db,
            batch=batch,
            store_id=store_id,
            source_code=source_code,
        )


def replace_import_file(
    db: Session,
    *,
    file_id: int,
    filename: str,
    content: bytes,
    reason: str,
    actor: str,
) -> ImportOutcome:
    clean_reason = _clean_reason(reason, "替换原因不能为空")
    clean_actor = _clean_required(actor, "替换操作人不能为空")
    old_file, batch = _current_file(db, file_id)
    if calculate_content_hash(content) == old_file.content_hash:
        raise ValueError("新文件与被替换文件内容完全相同，无需替换")

    try:
        with db.begin_nested():
            old_scopes = _file_scopes(db, old_file)
            outcome = import_workbook_in_transaction(
                db,
                ImportWorkbookCommand(
                    batch_id=batch.id,
                    filename=filename,
                    content=content,
                    profile_code=old_file.profile_code or "",
                    store_id=old_file.store_id,
                    actor=clean_actor,
                ),
                supersedes_file_id=old_file.id,
                duplicate_exclude_file_id=old_file.id,
            )
            if outcome.status == "duplicate":
                raise ImportVersionConflictError("同一业务范围已有内容完全相同的当前文件")
            new_file = db.get(ImportFile, outcome.import_file_id)
            if new_file is None:
                raise RuntimeError("替换文件创建失败")
            new_scopes = _file_scopes(db, new_file)
            _retire_file(db, old_file, clean_actor)
            _refresh_scopes(db, batch, old_scopes | new_scopes)
            reconcile_batch(db, batch.id)
            db.add(
                AuditEvent(
                    batch_id=batch.id,
                    event_type="file_replaced",
                    actor=clean_actor,
                    entity_type="import_file",
                    entity_id=str(new_file.id),
                    event_data={
                        "old_file_id": old_file.id,
                        "new_file_id": new_file.id,
                        "reason": clean_reason,
                        "profile_code": new_file.profile_code,
                        "business_date": batch.business_date.isoformat(),
                    },
                )
            )
            db.flush()
        db.commit()
        return outcome
    except Exception:
        db.rollback()
        raise


def invalidate_import_file(
    db: Session,
    *,
    file_id: int,
    reason: str,
    actor: str,
) -> ImportFile:
    clean_reason = _clean_reason(reason, "作废原因不能为空")
    clean_actor = _clean_required(actor, "作废操作人不能为空")
    import_file, batch = _current_file(db, file_id)
    try:
        with db.begin_nested():
            scopes = _file_scopes(db, import_file)
            _retire_file(db, import_file, clean_actor)
            _refresh_scopes(db, batch, scopes)
            reconcile_batch(db, batch.id)
            db.add(
                AuditEvent(
                    batch_id=batch.id,
                    event_type="file_invalidated",
                    actor=clean_actor,
                    entity_type="import_file",
                    entity_id=str(import_file.id),
                    event_data={
                        "file_id": import_file.id,
                        "reason": clean_reason,
                        "affected_scopes": [
                            {"store_id": store_id, "source_code": source_code}
                            for store_id, source_code in sorted(scopes)
                        ],
                    },
                )
            )
            db.flush()
        db.commit()
        return import_file
    except Exception:
        db.rollback()
        raise


def reset_batch_current_data(
    db: Session,
    *,
    batch_id: int,
    reason: str,
    confirmation_date: date,
    actor: str,
) -> ReconciliationBatch:
    clean_reason = _clean_reason(reason, "重置原因不能为空")
    clean_actor = _clean_required(actor, "重置操作人不能为空")
    batch = (
        db.query(ReconciliationBatch)
        .filter(ReconciliationBatch.id == batch_id)
        .populate_existing()
        .with_for_update()
        .one_or_none()
    )
    if batch is None:
        raise ImportVersionNotFoundError("对账批次不存在")
    if batch.status == "closed":
        raise ImportVersionConflictError("已关账批次必须先重开才能重置")
    if confirmation_date != batch.business_date:
        raise ValueError("确认日期必须与批次业务日期完全一致")

    try:
        with db.begin_nested():
            current_files = db.query(ImportFile).filter(
                ImportFile.batch_id == batch.id,
                ImportFile.is_current.is_(True),
            ).all()
            for import_file in current_files:
                _retire_file(db, import_file, clean_actor)

            # 防止历史异常状态残留：重置语义覆盖该批次全部“当前”提取与标准行。
            file_ids = [row.id for row in db.query(ImportFile.id).filter(
                ImportFile.batch_id == batch.id
            ).all()]
            if file_ids:
                for run in db.query(ExtractionRun).filter(
                    ExtractionRun.import_file_id.in_(file_ids),
                    ExtractionRun.is_current.is_(True),
                ):
                    run.is_current = False
            for row in db.query(CleanData).filter(
                CleanData.batch_id == batch.id,
                CleanData.is_current.is_(True),
            ):
                row.is_current = False

            now = datetime.now(UTC)
            for issue in db.query(DataQualityIssue).filter(
                DataQualityIssue.batch_id == batch.id,
                DataQualityIssue.status == "open",
            ):
                issue.status = "superseded"
                issue.resolved_by = clean_actor
                issue.resolved_at = now

            for coverage in db.query(SourceCoverage).filter(
                SourceCoverage.batch_id == batch.id
            ):
                coverage.status = "missing"
                coverage.evidence_type = None
                coverage.amount = Decimal("0.00")
                coverage.file_count = 0
                coverage.valid_row_count = 0
                coverage.error_row_count = 0
                coverage.extraction_run_id = None

            old_version = batch.version
            batch.version += 1
            batch.status = "attention_required"
            reconcile_batch(db, batch.id)
            batch.status = "attention_required"
            db.add(
                AuditEvent(
                    batch_id=batch.id,
                    event_type="batch_current_data_reset",
                    actor=clean_actor,
                    entity_type="reconciliation_batch",
                    entity_id=str(batch.id),
                    event_data={
                        "reason": clean_reason,
                        "reset_file_count": len(current_files),
                        "old_version": old_version,
                        "new_version": batch.version,
                    },
                )
            )
            db.flush()
        db.commit()
        return batch
    except Exception:
        db.rollback()
        raise
