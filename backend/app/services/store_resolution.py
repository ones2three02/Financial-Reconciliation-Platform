from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from difflib import SequenceMatcher

from sqlalchemy.orm import Session

from backend.app.models.audit import AuditEvent
from backend.app.models.quality_issue import DataQualityIssue
from backend.app.models.store import Store, StoreAlias
from backend.app.services.quality_service import (
    record_unknown_store_issue,
    resolve_unknown_store_issues,
)


@dataclass(frozen=True)
class StoreResolution:
    status: str
    store_id: int | None
    alias_id: int | None
    suggestions: tuple[int, ...]


def _suggest_store_ids(db: Session, raw_name: str) -> tuple[int, ...]:
    normalized_raw = "".join(raw_name.split()).casefold()
    candidates: list[tuple[float, int]] = []
    for store in db.query(Store).filter(Store.is_active.is_(True)).all():
        normalized_name = "".join(store.name.split()).casefold()
        score = SequenceMatcher(None, normalized_raw, normalized_name).ratio()
        if score >= 0.65:
            candidates.append((score, store.id))
    candidates.sort(key=lambda item: (-item[0], item[1]))
    return tuple(store_id for _, store_id in candidates[:3])


def resolve_store(
    db: Session,
    source_code: str,
    raw_name: str,
    *,
    batch_id: int | None = None,
    import_file_id: int | None = None,
    extraction_run_id: int | None = None,
    affected_amount: Decimal = Decimal("0.00"),
) -> StoreResolution:
    clean_source = source_code.strip()
    clean_name = raw_name.strip()
    if not clean_source:
        raise ValueError("门店解析必须提供数据来源")
    if not clean_name:
        raise ValueError("原始门店名称不能为空")

    exact_store = (
        db.query(Store)
        .filter(Store.name == clean_name, Store.is_active.is_(True))
        .first()
    )
    if exact_store is not None:
        return StoreResolution(
            status="resolved",
            store_id=exact_store.id,
            alias_id=None,
            suggestions=(),
        )

    alias = (
        db.query(StoreAlias)
        .filter(
            StoreAlias.source_code == clean_source,
            StoreAlias.alias_name == clean_name,
        )
        .first()
    )
    if (
        alias is not None
        and alias.status == "mapped"
        and alias.store_id is not None
        and alias.confirmed_at is not None
    ):
        store = db.get(Store, alias.store_id)
        if store is not None and store.is_active:
            return StoreResolution(
                status="resolved",
                store_id=store.id,
                alias_id=alias.id,
                suggestions=(),
            )

    suggestions = _suggest_store_ids(db, clean_name)
    if alias is None:
        alias = StoreAlias(
            source_code=clean_source,
            alias_name=clean_name,
            store_id=None,
            status="pending",
        )
        db.add(alias)
        db.flush()
    elif alias.status != "pending":
        alias.status = "pending"
        db.flush()

    if batch_id is not None:
        record_unknown_store_issue(
            db,
            batch_id=batch_id,
            import_file_id=import_file_id,
            extraction_run_id=extraction_run_id,
            source_code=clean_source,
            raw_name=clean_name,
            affected_amount=affected_amount,
        )

    return StoreResolution(
        status="pending",
        store_id=None,
        alias_id=alias.id,
        suggestions=suggestions,
    )


def confirm_alias(
    db: Session,
    *,
    alias_id: int,
    store_id: int,
    actor: str,
) -> StoreAlias:
    clean_actor = actor.strip()
    if not clean_actor:
        raise ValueError("确认门店别名必须提供操作人")
    alias = db.get(StoreAlias, alias_id)
    if alias is None:
        raise ValueError(f"门店别名不存在: {alias_id}")
    store = db.get(Store, store_id)
    if store is None or not store.is_active:
        raise ValueError(f"标准门店不存在或已停用: {store_id}")

    confirmed_at = datetime.now(UTC)
    alias.store_id = store.id
    alias.status = "mapped"
    alias.confirmed_by = clean_actor
    alias.confirmed_at = confirmed_at
    affected_run_ids = resolve_unknown_store_issues(
        db,
        source_code=alias.source_code,
        raw_name=alias.alias_name,
        actor=clean_actor,
    )
    db.add(
        AuditEvent(
            batch_id=None,
            event_type="store_alias_confirmed",
            actor=clean_actor,
            entity_type="store_alias",
            entity_id=str(alias.id),
            event_data={
                "source_code": alias.source_code,
                "alias_name": alias.alias_name,
                "store_id": store.id,
                "affected_run_ids": affected_run_ids,
            },
        )
    )
    db.flush()
    from backend.app.services.extraction_engine import extract_current_batch_rows

    for run_id in affected_run_ids:
        extract_current_batch_rows(db, run_id)
    return alias


def reprocess_affected_runs(db: Session, alias_id: int) -> list[int]:
    alias = db.get(StoreAlias, alias_id)
    if alias is None:
        raise ValueError(f"门店别名不存在: {alias_id}")
    run_ids = [
        run_id
        for (run_id,) in (
            db.query(DataQualityIssue.extraction_run_id)
            .filter(
                DataQualityIssue.issue_type == "unknown_store",
                DataQualityIssue.source_code == alias.source_code,
                DataQualityIssue.raw_value == alias.alias_name,
                DataQualityIssue.extraction_run_id.is_not(None),
            )
            .distinct()
            .all()
        )
    ]
    from backend.app.services.extraction_engine import extract_current_batch_rows

    for run_id in run_ids:
        extract_current_batch_rows(db, run_id)
    return run_ids
