from datetime import date
from decimal import Decimal

import pytest

from backend.app.models.audit import AuditEvent
from backend.app.models.batch import ReconciliationBatch
from backend.app.models.import_file import ImportFile
from backend.app.models.auth import AppUser
from backend.app.models.quality_issue import DataQualityIssue
from backend.app.models.store import Store, StoreAlias
from backend.app.crud.store import create_store
from backend.app.schemas.store import StoreAliasConfirm, StoreCreate
from backend.app.api.stores import confirm_store_alias
from backend.app.services.store_resolution import confirm_alias, resolve_store


ADMIN = AppUser(id=1, username="admin", role="admin", is_active=True)


RAW_MEITUAN_NAME = "武汉 : 山道健身游泳舞蹈(曙光店)"


def create_context(db_session):
    store = Store(name="民院店", code="MD010")
    batch = ReconciliationBatch(
        business_date=date(2026, 7, 10),
        status="draft",
        created_by="admin",
    )
    db_session.add_all([store, batch])
    db_session.flush()
    import_file = ImportFile(
        filename="美团收入.xlsx",
        data_source="meituan",
        upload_status="parsed",
        batch_id=batch.id,
        profile_code="meituan_v1",
        profile_version=1,
        content_hash="a" * 64,
        is_current=True,
    )
    db_session.add(import_file)
    db_session.commit()
    return store, batch, import_file


def test_unknown_alias_does_not_bind_from_similarity(db_session):
    store, batch, import_file = create_context(db_session)

    resolution = resolve_store(
        db_session,
        "meituan",
        RAW_MEITUAN_NAME,
        batch_id=batch.id,
        import_file_id=import_file.id,
        affected_amount=Decimal("9.90"),
    )
    db_session.commit()

    assert resolution.status == "pending"
    assert resolution.store_id is None
    assert resolution.suggestions == ()
    alias = db_session.get(StoreAlias, resolution.alias_id)
    assert alias.status == "pending"
    issue = db_session.query(DataQualityIssue).one()
    assert issue.issue_type == "unknown_store"
    assert issue.status == "open"
    assert issue.affected_amount == Decimal("9.90")


def test_confirmation_is_source_specific_and_audited(db_session):
    store, batch, import_file = create_context(db_session)
    pending = resolve_store(
        db_session,
        "meituan",
        RAW_MEITUAN_NAME,
        batch_id=batch.id,
        import_file_id=import_file.id,
    )
    db_session.commit()

    alias = confirm_alias(
        db_session,
        alias_id=pending.alias_id,
        store_id=store.id,
        actor="admin",
    )
    db_session.commit()

    assert alias.status == "mapped"
    assert alias.confirmed_by == "admin"
    assert alias.confirmed_at is not None
    assert resolve_store(db_session, "meituan", RAW_MEITUAN_NAME).store_id == store.id
    assert resolve_store(db_session, "douyin", RAW_MEITUAN_NAME).status == "pending"
    assert db_session.query(DataQualityIssue).filter_by(status="resolved").count() == 1
    audit = db_session.query(AuditEvent).one()
    assert audit.event_type == "store_alias_confirmed"
    assert audit.actor == "admin"


def test_creating_standard_store_does_not_auto_confirm_pending_alias(db_session):
    pending_alias = StoreAlias(
        source_code="meituan",
        alias_name="新门店",
        status="pending",
    )
    db_session.add(pending_alias)
    db_session.commit()

    store = create_store(db_session, StoreCreate(name="新门店"))

    db_session.refresh(pending_alias)
    assert store.name == "新门店"
    assert pending_alias.status == "pending"
    assert pending_alias.store_id is None
    assert pending_alias.confirmed_at is None


def test_confirmation_endpoint_uses_server_side_actor(db_session):
    store, batch, import_file = create_context(db_session)
    pending = resolve_store(
        db_session,
        "meituan",
        RAW_MEITUAN_NAME,
        batch_id=batch.id,
        import_file_id=import_file.id,
    )
    db_session.commit()

    alias = confirm_store_alias(
        alias_id=pending.alias_id,
        confirmation=StoreAliasConfirm(store_id=store.id),
        current_user=ADMIN,
        db=db_session,
    )

    assert alias.status == "mapped"
    assert alias.confirmed_by == "admin"
    assert alias.confirmed_at is not None


def test_alias_rebind_requires_reason_and_audits_old_new_store(db_session):
    first_store = Store(name="民院店", code="MD010")
    second_store = Store(name="民院二店", code="MD011")
    alias = StoreAlias(
        source_code="meituan",
        alias_name="美团民院门店",
        store_id=first_store.id,
        status="mapped",
        confirmed_by="admin",
    )
    db_session.add_all([first_store, second_store])
    db_session.flush()
    alias.store_id = first_store.id
    db_session.add(alias)
    db_session.commit()

    with pytest.raises(ValueError, match="重新绑定必须填写原因"):
        confirm_alias(
            db_session,
            alias_id=alias.id,
            store_id=second_store.id,
            actor="admin",
        )

    confirm_alias(
        db_session,
        alias_id=alias.id,
        store_id=second_store.id,
        actor="admin",
        reason="原门店选择错误",
    )
    db_session.commit()

    audit = db_session.query(AuditEvent).filter_by(
        event_type="store_alias_confirmed"
    ).one()
    assert audit.event_data["previous_store_id"] == first_store.id
    assert audit.event_data["new_store_id"] == second_store.id
    assert audit.event_data["reason"] == "原门店选择错误"
