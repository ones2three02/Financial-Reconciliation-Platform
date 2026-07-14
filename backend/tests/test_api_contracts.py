import asyncio
from datetime import date, datetime
from io import BytesIO

import pytest
from fastapi import HTTPException, UploadFile
from openpyxl import Workbook

from backend.app.api.batches import (
    close_reconciliation_batch,
    confirm_batch_source_zero,
    create_reconciliation_batch,
    get_reconciliation_batch,
    reconcile_reconciliation_batch,
    reopen_reconciliation_batch,
    reset_reconciliation_batch_current_data,
)
from backend.app.api.files import (
    delete_file,
    import_file,
    invalidate_file,
    replace_file,
)
from backend.app.models.audit import AuditEvent
from backend.app.models.import_file import ImportFile
from backend.app.models.auth import AppUser
from backend.app.models.store import Store
from backend.app.schemas.batch import (
    BatchCreate,
    BatchReopenRequest,
    ConfirmZeroRequest,
)
from backend.app.schemas.import_command import (
    InvalidateImportRequest,
    ResetBatchCurrentDataRequest,
)


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
