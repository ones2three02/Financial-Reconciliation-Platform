import asyncio
from datetime import date, datetime
from io import BytesIO

import pytest
from fastapi import HTTPException, UploadFile
from openpyxl import Workbook
from pydantic import ValidationError

from backend.app.api import batches as batches_api
from backend.app.api import mappings as mappings_api
from backend.app.api import stores as stores_api
from backend.app.schemas import batch as batch_schemas
from backend.app.api.batches import (
    close_reconciliation_batch,
    confirm_batch_source_zero,
    create_reconciliation_batch,
    get_reconciliation_batch,
    get_reconciliation_batch_detail,
    reconcile_reconciliation_batch,
    reopen_reconciliation_batch,
    reset_reconciliation_batch_current_data,
)
from backend.app.api import files as files_api
from backend.app.api.files import (
    delete_file,
    import_file,
    invalidate_file,
    replace_file,
)
from backend.app.models.audit import AuditEvent
from backend.app.models.import_file import ImportFile
from backend.app.models.auth import AppUser
from backend.app.models.field_mapping import FieldMapping
from backend.app.models.store import Store, StoreAlias
from backend.app.schemas.batch import (
    BatchCreate,
    BatchReopenRequest,
    ConfirmZeroRequest,
)
from backend.app.schemas.import_command import (
    InvalidateImportRequest,
    ResetBatchCurrentDataRequest,
)
from backend.app.schemas import import_command as import_command_schemas
from backend.app.schemas.field_mapping import FieldMappingCreate, FieldMappingUpdate
from backend.app.schemas.store import StoreAliasConfirm, StoreUpdate


ADMIN = AppUser(id=1, username="admin", role="admin", is_active=True)


def finance_workbook(amount: int = 100) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "收入流水表"
    sheet.append(["日期", "付款方式", "金额"])
    sheet.append([datetime(2026, 7, 10), "微信", amount])
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


def test_batch_routes_cover_create_zero_reconcile_close_and_reopen(db_session):
    store = Store(name="民院店", code="MD010", is_active=True)
    db_session.add(store)
    db_session.commit()
    batch = create_reconciliation_batch(
        payload=BatchCreate(business_date=date(2026, 7, 10)),
        current_user=ADMIN,
        db=db_session,
    )

    for source in ("tonglian", "meituan", "douyin", "cash", "sales"):
        confirm_batch_source_zero(
            batch_id=batch.id,
            payload=ConfirmZeroRequest(
                store_id=store.id,
                source_code=source,
            ),
            current_user=ADMIN,
            db=db_session,
        )
    response = reconcile_reconciliation_batch(
        batch_id=batch.id,
        current_user=ADMIN,
        db=db_session,
    )
    assert response[0].status == "consistent"
    assert get_reconciliation_batch(batch.id, db=db_session).status == "ready_to_close"

    closed = close_reconciliation_batch(
        batch_id=batch.id,
        current_user=ADMIN,
        db=db_session,
    )
    assert closed.status == "closed"
    reopened = reopen_reconciliation_batch(
        batch_id=batch.id,
        payload=BatchReopenRequest(reason="补充文件"),
        current_user=ADMIN,
        db=db_session,
    )
    assert reopened.status == "attention_required"


def test_closed_batch_import_returns_conflict(db_session):
    store = Store(name="民院店", code="MD010", is_active=True)
    db_session.add(store)
    batch = create_reconciliation_batch(
        payload=BatchCreate(business_date=date(2026, 7, 10)),
        current_user=ADMIN,
        db=db_session,
    )
    batch.status = "closed"
    db_session.commit()
    upload = UploadFile(filename="7月民院财务表.xlsx", file=BytesIO(finance_workbook()))

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            import_file(
                file=upload,
                batch_id=batch.id,
                profile_code="store_finance_v1",
                store_id=store.id,
                current_user=ADMIN,
                db=db_session,
            )
        )

    assert exc_info.value.status_code == 409


def test_legacy_delete_is_disabled_and_preserves_file(db_session):
    import_record = ImportFile(
        filename="历史文件.xlsx",
        data_source="tonglian",
        upload_status="processed",
    )
    db_session.add(import_record)
    db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        delete_file(import_record.id, db=db_session)

    assert exc_info.value.status_code == 409
    assert db_session.get(ImportFile, import_record.id) is not None


def test_version_routes_use_authenticated_actor(db_session):
    store = Store(name="民院店", code="MD010", is_active=True)
    db_session.add(store)
    batch = create_reconciliation_batch(
        payload=BatchCreate(business_date=date(2026, 7, 10)),
        current_user=ADMIN,
        db=db_session,
    )
    first_upload = UploadFile(
        filename="7月民院财务表.xlsx",
        file=BytesIO(finance_workbook()),
    )
    imported = asyncio.run(import_file(
        file=first_upload,
        batch_id=batch.id,
        profile_code="store_finance_v1",
        store_id=store.id,
        current_user=ADMIN,
        db=db_session,
    ))

    response = invalidate_file(
        file_id=imported.import_file_id,
        payload=InvalidateImportRequest(reason="导错账期"),
        current_user=ADMIN,
        db=db_session,
    )
    assert response.status == "invalidated"
    assert db_session.query(AuditEvent).filter_by(event_type="file_invalidated").one().actor == ADMIN.username


def test_reset_route_returns_conflict_for_closed_batch(db_session):
    batch = create_reconciliation_batch(
        payload=BatchCreate(business_date=date(2026, 7, 10)),
        current_user=ADMIN,
        db=db_session,
    )
    batch.status = "closed"
    db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        reset_reconciliation_batch_current_data(
            batch_id=batch.id,
            payload=ResetBatchCurrentDataRequest(
                reason="整日导出错误",
                confirmation_date=date(2026, 7, 10),
                risk_acknowledged=True,
            ),
            current_user=ADMIN,
            db=db_session,
        )

    assert exc_info.value.status_code == 409


def test_replace_route_returns_bad_request_for_same_content(db_session):
    store = Store(name="民院店", code="MD010", is_active=True)
    db_session.add(store)
    batch = create_reconciliation_batch(
        payload=BatchCreate(business_date=date(2026, 7, 10)),
        current_user=ADMIN,
        db=db_session,
    )
    content = finance_workbook()
    imported = asyncio.run(import_file(
        file=UploadFile(filename="原文件.xlsx", file=BytesIO(content)),
        batch_id=batch.id,
        profile_code="store_finance_v1",
        store_id=store.id,
        current_user=ADMIN,
        db=db_session,
    ))

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(replace_file(
            file_id=imported.import_file_id,
            file=UploadFile(filename="相同文件.xlsx", file=BytesIO(content)),
            reason="测试相同文件",
            current_user=ADMIN,
            db=db_session,
        ))

    assert exc_info.value.status_code == 400


def test_revoke_zero_route_uses_authenticated_actor(db_session):
    store = Store(name="民院店", code="MD010", is_active=True)
    db_session.add(store)
    db_session.commit()
    batch = create_reconciliation_batch(
        payload=BatchCreate(business_date=date(2026, 7, 10)),
        current_user=ADMIN,
        db=db_session,
    )
    confirm_batch_source_zero(
        batch_id=batch.id,
        payload=ConfirmZeroRequest(store_id=store.id, source_code="meituan"),
        current_user=ADMIN,
        db=db_session,
    )

    response = batches_api.revoke_batch_source_zero(
        batch_id=batch.id,
        payload=batch_schemas.RevokeZeroRequest(
            store_id=store.id,
            source_code="meituan",
            reason="刚才点错了",
        ),
        current_user=ADMIN,
        db=db_session,
    )

    assert response["status"] == "missing"
    audit = db_session.query(AuditEvent).filter_by(
        event_type="source_zero_confirmation_revoked"
    ).one()
    assert audit.actor == ADMIN.username


def test_revoke_zero_request_rejects_blank_reason():
    with pytest.raises(ValidationError):
        batch_schemas.RevokeZeroRequest(
            store_id=1,
            source_code="meituan",
            reason="",
        )


def test_restore_file_route_uses_authenticated_actor(db_session):
    store = Store(name="民院店", code="MD010", is_active=True)
    db_session.add(store)
    db_session.commit()
    batch = create_reconciliation_batch(
        payload=BatchCreate(business_date=date(2026, 7, 10)),
        current_user=ADMIN,
        db=db_session,
    )
    imported = asyncio.run(import_file(
        file=UploadFile(filename="原文件.xlsx", file=BytesIO(finance_workbook())),
        batch_id=batch.id,
        profile_code="store_finance_v1",
        store_id=store.id,
        current_user=ADMIN,
        db=db_session,
    ))
    invalidate_file(
        file_id=imported.import_file_id,
        payload=InvalidateImportRequest(reason="误作废测试"),
        current_user=ADMIN,
        db=db_session,
    )

    response = files_api.restore_file(
        file_id=imported.import_file_id,
        payload=import_command_schemas.RestoreImportRequest(reason="撤销误作废"),
        current_user=ADMIN,
        db=db_session,
    )

    assert response.import_file_id == imported.import_file_id
    audit = db_session.query(AuditEvent).filter_by(event_type="file_restored").one()
    assert audit.actor == ADMIN.username


def test_restore_last_reset_route_exposes_eligibility_and_actor(db_session):
    store = Store(name="民院店", code="MD010", is_active=True)
    db_session.add(store)
    db_session.commit()
    batch = create_reconciliation_batch(
        payload=BatchCreate(business_date=date(2026, 7, 10)),
        current_user=ADMIN,
        db=db_session,
    )
    asyncio.run(import_file(
        file=UploadFile(filename="原文件.xlsx", file=BytesIO(finance_workbook())),
        batch_id=batch.id,
        profile_code="store_finance_v1",
        store_id=store.id,
        current_user=ADMIN,
        db=db_session,
    ))
    reset_reconciliation_batch_current_data(
        batch_id=batch.id,
        payload=ResetBatchCurrentDataRequest(
            reason="误导入整批数据",
            confirmation_date=date(2026, 7, 10),
            risk_acknowledged=True,
        ),
        current_user=ADMIN,
        db=db_session,
    )
    detail = get_reconciliation_batch_detail(batch.id, db=db_session)
    assert detail.can_restore_last_reset is True
    assert detail.last_reset_event_id is not None

    restored = batches_api.restore_reconciliation_batch_last_reset(
        batch_id=batch.id,
        payload=import_command_schemas.RestoreLastResetRequest(
            reason="刚才误重置",
            confirmation_date=date(2026, 7, 10),
            risk_acknowledged=True,
        ),
        current_user=ADMIN,
        db=db_session,
    )

    assert restored.version == 3
    audit = db_session.query(AuditEvent).filter_by(event_type="batch_reset_restored").one()
    assert audit.actor == ADMIN.username


def test_master_data_routes_audit_authenticated_actor(db_session):
    store = Store(name="无数据门店", code="MD020", is_active=True)
    mapping = FieldMapping(
        data_source="meituan",
        target_field="amount",
        source_column="总收入（元）",
        is_active=True,
    )
    db_session.add_all([store, mapping])
    db_session.commit()

    stores_api.update_store(
        store_id=store.id,
        store=StoreUpdate(
            is_active=False,
            status_change_reason="门店已停止营业",
        ),
        current_user=ADMIN,
        db=db_session,
    )
    mappings_api.update_field_mapping(
        mapping_id=mapping.id,
        mapping=FieldMappingUpdate(
            is_active=False,
            status_change_reason="平台模板已废弃",
        ),
        current_user=ADMIN,
        db=db_session,
    )

    events = db_session.query(AuditEvent).order_by(AuditEvent.id).all()
    assert [event.actor for event in events] == [ADMIN.username, ADMIN.username]
    assert [event.event_type for event in events] == [
        "store_deactivated",
        "field_mapping_deactivated",
    ]


def test_field_mapping_route_rejects_source_target_mismatch(db_session):
    with pytest.raises(HTTPException) as exc_info:
        mappings_api.create_field_mapping(
            mapping=FieldMappingCreate(
                data_source="tonglian",
                target_field="payment_method",
                source_column="付款方式",
            ),
            current_user=ADMIN,
            db=db_session,
        )

    assert exc_info.value.status_code == 400
    assert "不支持的目标字段" in exc_info.value.detail


def test_alias_rebind_route_passes_reason_to_audit(db_session):
    first_store = Store(name="民院店", code="MD010")
    second_store = Store(name="民院二店", code="MD011")
    db_session.add_all([first_store, second_store])
    db_session.flush()
    alias = StoreAlias(
        source_code="meituan",
        alias_name="美团民院门店",
        store_id=first_store.id,
        status="mapped",
        confirmed_by="admin",
    )
    db_session.add(alias)
    db_session.commit()

    stores_api.confirm_store_alias(
        alias_id=alias.id,
        confirmation=StoreAliasConfirm(
            store_id=second_store.id,
            reason="原门店选择错误",
        ),
        current_user=ADMIN,
        db=db_session,
    )

    audit = db_session.query(AuditEvent).filter_by(
        event_type="store_alias_confirmed"
    ).one()
    assert audit.event_data["reason"] == "原门店选择错误"
