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
from backend.app.models.raw_data import RawData
from backend.app.services.coverage_service import rebuild_scope_coverage, upsert_coverage
from backend.app.services.extraction_engine import extract_current_batch_rows
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


def _locked_historical_file(
    db: Session,
    file_id: int,
) -> tuple[ImportFile, ReconciliationBatch]:
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
    if import_file is None:
        raise ImportVersionNotFoundError("导入文件不存在")
    if import_file.is_current:
        raise ImportVersionConflictError("该文件已经是当前版本，无需恢复")
    if batch.status == "closed":
        raise ImportVersionConflictError("已关账批次必须先重开才能恢复历史文件")
    if not import_file.profile_code or import_file.profile_version is None:
        raise ImportVersionConflictError("历史文件缺少提取模板信息，不能自动恢复")
    return import_file, batch


def _chain_contains(db: Session, current_file: ImportFile, target_file_id: int) -> bool:
    visited: set[int] = set()
    cursor: ImportFile | None = current_file
    while cursor is not None and cursor.id not in visited:
        if cursor.id == target_file_id:
            return True
        visited.add(cursor.id)
        if cursor.supersedes_file_id is None:
            return False
        cursor = db.get(ImportFile, cursor.supersedes_file_id)
    return False


def _current_descendants(db: Session, target: ImportFile) -> list[ImportFile]:
    current_files = db.query(ImportFile).filter(
        ImportFile.batch_id == target.batch_id,
        ImportFile.is_current.is_(True),
    ).all()
    return [
        row
        for row in current_files
        if _chain_contains(db, row, target.id)
    ]


def _new_extraction_run(db: Session, import_file: ImportFile) -> ExtractionRun:
    if not import_file.profile_code or import_file.profile_version is None:
        raise ImportVersionConflictError("历史文件缺少提取模板信息，不能自动恢复")
    raw_count = db.query(RawData).filter(
        RawData.import_file_id == import_file.id
    ).count()
    run = ExtractionRun(
        import_file_id=import_file.id,
        profile_code=import_file.profile_code,
        profile_version=import_file.profile_version,
        status="pending",
        started_at=datetime.now(UTC),
        raw_row_count=raw_count,
        output_row_count=0,
        error_row_count=0,
        is_current=True,
    )
    db.add(run)
    db.flush()
    return run


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
    password: str | None = None,
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
                    password=password,
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


def restore_import_file(
    db: Session,
    *,
    file_id: int,
    reason: str,
    actor: str,
) -> ImportOutcome:
    clean_reason = _clean_reason(reason, "恢复原因不能为空")
    clean_actor = _clean_required(actor, "恢复操作人不能为空")
    target, batch = _locked_historical_file(db, file_id)
    descendants = _current_descendants(db, target)
    descendant_ids = {row.id for row in descendants}

    if target.content_hash:
        duplicate_query = db.query(ImportFile).filter(
            ImportFile.batch_id == batch.id,
            ImportFile.content_hash == target.content_hash,
            ImportFile.profile_code == target.profile_code,
            ImportFile.store_id == target.store_id,
            ImportFile.is_current.is_(True),
        )
        if descendant_ids:
            duplicate_query = duplicate_query.filter(
                ImportFile.id.not_in(descendant_ids)
            )
        if duplicate_query.first() is not None:
            raise ImportVersionConflictError(
                "同一业务范围已有相同内容的当前文件，不能重复恢复"
            )

    try:
        with db.begin_nested():
            affected_scopes = _file_scopes(db, target)
            for descendant in descendants:
                affected_scopes.update(_file_scopes(db, descendant))
                _retire_file(db, descendant, clean_actor)

            target.is_current = True
            target.error_message = None
            run = _new_extraction_run(db, target)
            summary = extract_current_batch_rows(db, run.id)
            affected_scopes.update(_file_scopes(db, target))
            _refresh_scopes(db, batch, affected_scopes)
            reconcile_batch(db, batch.id)
            db.add(
                AuditEvent(
                    batch_id=batch.id,
                    event_type="file_restored",
                    actor=clean_actor,
                    entity_type="import_file",
                    entity_id=str(target.id),
                    event_data={
                        "file_id": target.id,
                        "new_extraction_run_id": run.id,
                        "retired_descendant_file_ids": sorted(descendant_ids),
                        "reason": clean_reason,
                        "profile_code": target.profile_code,
                        "business_date": batch.business_date.isoformat(),
                    },
                )
            )
            db.flush()
        db.commit()
        return ImportOutcome(
            status="attention_required" if summary.issue_count else "imported",
            import_file_id=target.id,
            extraction_run_id=run.id,
        )
    except Exception:
        db.rollback()
        raise


def reset_batch_current_data(
    db: Session,
    *,
    batch_id: int,
    reason: str,
    confirmation_date: date,
    risk_acknowledged: bool,
    actor: str,
) -> ReconciliationBatch:
    clean_reason = _clean_reason(reason, "重置原因不能为空")
    clean_actor = _clean_required(actor, "重置操作人不能为空")
    if not risk_acknowledged:
        raise ValueError("必须确认已了解整批重置风险")
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
            current_files = (
                db.query(ImportFile)
                .filter(
                    ImportFile.batch_id == batch.id,
                    ImportFile.is_current.is_(True),
                )
                .order_by(ImportFile.id)
                .all()
            )
            current_file_ids = [row.id for row in current_files]
            manual_zero_scopes = [
                {"store_id": row.store_id, "source_code": row.source_code}
                for row in (
                    db.query(SourceCoverage)
                    .filter(
                        SourceCoverage.batch_id == batch.id,
                        SourceCoverage.status == "present_zero",
                        SourceCoverage.evidence_type == "manual_zero_confirmation",
                    )
                    .order_by(SourceCoverage.store_id, SourceCoverage.source_code)
                    .all()
                )
            ]
            previous_status = batch.status
            previous_version = batch.version
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
                        "current_file_ids": current_file_ids,
                        "manual_zero_scopes": manual_zero_scopes,
                        "previous_status": previous_status,
                        "previous_version": previous_version,
                        "old_version": previous_version,
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


def _locked_open_batch(db: Session, batch_id: int) -> ReconciliationBatch:
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
        raise ImportVersionConflictError("已关账批次必须先重开才能恢复整批重置")
    return batch


def _latest_unrestored_reset_event(db: Session, batch_id: int) -> AuditEvent:
    reset_event = (
        db.query(AuditEvent)
        .filter(
            AuditEvent.batch_id == batch_id,
            AuditEvent.event_type == "batch_current_data_reset",
        )
        .order_by(AuditEvent.id.desc())
        .first()
    )
    if reset_event is None:
        raise ImportVersionConflictError("没有可恢复的整批重置")
    restored_events = db.query(AuditEvent).filter(
        AuditEvent.batch_id == batch_id,
        AuditEvent.event_type == "batch_reset_restored",
    ).all()
    if any(
        (event.event_data or {}).get("reset_event_id") == reset_event.id
        for event in restored_events
    ):
        raise ImportVersionConflictError("上一次整批重置已经恢复，不能重复恢复")
    return reset_event


def _validate_reset_restore_state(
    db: Session,
    batch: ReconciliationBatch,
    reset_event: AuditEvent,
) -> None:
    snapshot = reset_event.event_data or {}
    if batch.version != snapshot.get("new_version"):
        raise ImportVersionConflictError("批次版本在重置后已变化，不能自动恢复")
    if db.query(ImportFile).filter(
        ImportFile.batch_id == batch.id,
        ImportFile.is_current.is_(True),
    ).count():
        raise ImportVersionConflictError("重置后已有新增导入，不能自动恢复")
    non_missing_coverages = db.query(SourceCoverage).filter(
        SourceCoverage.batch_id == batch.id,
        SourceCoverage.status != "missing",
    ).all()
    if any(
        row.evidence_type == "manual_zero_confirmation"
        for row in non_missing_coverages
    ):
        raise ImportVersionConflictError("重置后已有新的业务确认，不能自动恢复")
    if non_missing_coverages:
        raise ImportVersionConflictError("重置后已有新的当前数据，不能自动恢复")

    file_ids = snapshot.get("current_file_ids")
    if not isinstance(file_ids, list):
        raise ImportVersionConflictError("重置快照不完整，不能自动恢复")
    for file_id in file_ids:
        import_file = db.get(ImportFile, file_id)
        if (
            import_file is None
            or import_file.batch_id != batch.id
            or import_file.is_current
        ):
            raise ImportVersionConflictError("重置快照中的历史文件状态已变化")


def get_last_reset_restore_eligibility(
    db: Session,
    batch_id: int,
) -> tuple[bool, int | None]:
    batch = db.get(ReconciliationBatch, batch_id)
    if batch is None or batch.status == "closed":
        return False, None
    try:
        reset_event = _latest_unrestored_reset_event(db, batch_id)
        _validate_reset_restore_state(db, batch, reset_event)
    except (ImportVersionConflictError, ImportVersionNotFoundError):
        return False, None
    return True, reset_event.id


def _restore_snapshot_file(
    db: Session,
    batch: ReconciliationBatch,
    file_id: int,
) -> ExtractionRun:
    import_file = (
        db.query(ImportFile)
        .filter(ImportFile.id == file_id)
        .populate_existing()
        .with_for_update()
        .one_or_none()
    )
    if (
        import_file is None
        or import_file.batch_id != batch.id
        or import_file.is_current
    ):
        raise ImportVersionConflictError("重置快照中的历史文件状态已变化")
    import_file.is_current = True
    import_file.error_message = None
    run = _new_extraction_run(db, import_file)
    extract_current_batch_rows(db, run.id)
    return run


def _restore_manual_zero(
    db: Session,
    batch: ReconciliationBatch,
    scope: dict[str, object],
) -> None:
    store_id = scope.get("store_id")
    source_code = scope.get("source_code")
    if not isinstance(store_id, int) or not isinstance(source_code, str):
        raise ImportVersionConflictError("重置快照中的零收入范围无效")
    existing = db.query(SourceCoverage).filter(
        SourceCoverage.batch_id == batch.id,
        SourceCoverage.store_id == store_id,
        SourceCoverage.source_code == source_code,
    ).one_or_none()
    if existing is not None and existing.status != "missing":
        raise ImportVersionConflictError("零收入范围已有新数据，不能覆盖恢复")
    upsert_coverage(
        db,
        batch_id=batch.id,
        business_date=batch.business_date,
        store_id=store_id,
        source_code=source_code,
        status="present_zero",
        evidence_type="manual_zero_confirmation",
        amount=Decimal("0.00"),
        file_count=0,
        valid_row_count=0,
        error_row_count=0,
        extraction_run_id=None,
    )


def restore_last_reset(
    db: Session,
    *,
    batch_id: int,
    reason: str,
    confirmation_date: date,
    risk_acknowledged: bool,
    actor: str,
) -> ReconciliationBatch:
    clean_reason = _clean_reason(reason, "恢复原因不能为空")
    clean_actor = _clean_required(actor, "恢复操作人不能为空")
    if not risk_acknowledged:
        raise ValueError("必须确认已了解整批恢复风险")
    batch = _locked_open_batch(db, batch_id)
    if confirmation_date != batch.business_date:
        raise ValueError("确认日期必须与批次业务日期完全一致")
    reset_event = _latest_unrestored_reset_event(db, batch.id)
    _validate_reset_restore_state(db, batch, reset_event)
    snapshot = reset_event.event_data or {}

    try:
        with db.begin_nested():
            restored_run_ids = [
                _restore_snapshot_file(db, batch, int(file_id)).id
                for file_id in snapshot.get("current_file_ids", [])
            ]
            manual_zero_scopes = snapshot.get("manual_zero_scopes", [])
            if not isinstance(manual_zero_scopes, list):
                raise ImportVersionConflictError("重置快照中的零收入范围无效")
            for scope in manual_zero_scopes:
                if not isinstance(scope, dict):
                    raise ImportVersionConflictError("重置快照中的零收入范围无效")
                _restore_manual_zero(db, batch, scope)

            reconcile_batch(db, batch.id)
            previous_version = batch.version
            batch.version += 1
            db.add(
                AuditEvent(
                    batch_id=batch.id,
                    event_type="batch_reset_restored",
                    actor=clean_actor,
                    entity_type="reconciliation_batch",
                    entity_id=str(batch.id),
                    event_data={
                        "reset_event_id": reset_event.id,
                        "reason": clean_reason,
                        "restored_file_ids": snapshot.get("current_file_ids", []),
                        "restored_extraction_run_ids": restored_run_ids,
                        "restored_manual_zero_scopes": manual_zero_scopes,
                        "old_version": previous_version,
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
