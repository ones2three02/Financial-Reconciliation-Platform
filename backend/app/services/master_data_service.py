from sqlalchemy.orm import Session

from backend.app.models.audit import AuditEvent
from backend.app.models.batch import ReconciliationBatch
from backend.app.models.clean_data import CleanData
from backend.app.models.coverage import SourceCoverage
from backend.app.models.field_mapping import FieldMapping
from backend.app.models.import_file import ImportFile
from backend.app.models.store import Store


def _clean_required(value: str, message: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(message)
    if len(cleaned) > 500:
        raise ValueError("操作原因不能超过 500 个字符")
    return cleaned


def set_store_active(
    db: Session,
    *,
    store_id: int,
    is_active: bool,
    actor: str,
    reason: str,
) -> Store:
    clean_actor = _clean_required(actor, "门店状态操作人不能为空")
    clean_reason = _clean_required(reason, "门店状态变更原因不能为空")
    store = db.get(Store, store_id)
    if store is None:
        raise ValueError("标准门店不存在")
    if bool(store.is_active) == is_active:
        return store

    if not is_active:
        has_current_clean_data = (
            db.query(CleanData.id)
            .join(
                ReconciliationBatch,
                ReconciliationBatch.id == CleanData.batch_id,
            )
            .join(ImportFile, ImportFile.id == CleanData.import_file_id)
            .filter(
                CleanData.store_id == store.id,
                CleanData.is_current.is_(True),
                CleanData.is_valid.is_(True),
                ImportFile.is_current.is_(True),
                ReconciliationBatch.status != "closed",
            )
            .first()
            is not None
        )
        has_current_coverage = (
            db.query(SourceCoverage.id)
            .join(
                ReconciliationBatch,
                ReconciliationBatch.id == SourceCoverage.batch_id,
            )
            .filter(
                SourceCoverage.store_id == store.id,
                SourceCoverage.status != "missing",
                ReconciliationBatch.status != "closed",
            )
            .first()
            is not None
        )
        if has_current_clean_data or has_current_coverage:
            raise ValueError("该门店在当前未关账批次仍有数据，不能停用")

    previous_is_active = bool(store.is_active)
    store.is_active = is_active
    db.add(
        AuditEvent(
            batch_id=None,
            event_type="store_activated" if is_active else "store_deactivated",
            actor=clean_actor,
            entity_type="store",
            entity_id=str(store.id),
            event_data={
                "store_id": store.id,
                "store_name": store.name,
                "previous_is_active": previous_is_active,
                "new_is_active": is_active,
                "reason": clean_reason,
            },
        )
    )
    db.flush()
    return store


def set_field_mapping_active(
    db: Session,
    *,
    mapping_id: int,
    is_active: bool,
    actor: str,
    reason: str,
) -> FieldMapping:
    clean_actor = _clean_required(actor, "字段映射状态操作人不能为空")
    clean_reason = _clean_required(reason, "字段映射状态变更原因不能为空")
    mapping = db.get(FieldMapping, mapping_id)
    if mapping is None:
        raise ValueError("字段映射不存在")
    if bool(mapping.is_active) == is_active:
        return mapping

    previous_is_active = bool(mapping.is_active)
    mapping.is_active = is_active
    db.add(
        AuditEvent(
            batch_id=None,
            event_type=(
                "field_mapping_activated"
                if is_active
                else "field_mapping_deactivated"
            ),
            actor=clean_actor,
            entity_type="field_mapping",
            entity_id=str(mapping.id),
            event_data={
                "mapping_id": mapping.id,
                "data_source": mapping.data_source,
                "source_column": mapping.source_column,
                "previous_is_active": previous_is_active,
                "new_is_active": is_active,
                "reason": clean_reason,
            },
        )
    )
    db.flush()
    return mapping
