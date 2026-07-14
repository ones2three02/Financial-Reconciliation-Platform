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
)
from backend.app.api.files import delete_file, import_file
from backend.app.models.import_file import ImportFile
from backend.app.models.store import Store
from backend.app.schemas.batch import (
    BatchActorRequest,
    BatchCreate,
    BatchReopenRequest,
    ConfirmZeroRequest,
)


def finance_workbook() -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "收入流水表"
    sheet.append(["日期", "付款方式", "金额"])
    sheet.append([datetime(2026, 7, 10), "微信", 100])
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


def test_batch_routes_cover_create_zero_reconcile_close_and_reopen(db_session):
    store = Store(name="民院店", code="MD010", is_active=True)
    db_session.add(store)
    db_session.commit()
    batch = create_reconciliation_batch(
        payload=BatchCreate(business_date=date(2026, 7, 10), actor="admin"),
        db=db_session,
    )

    for source in ("tonglian", "meituan", "douyin", "cash", "sales"):
        confirm_batch_source_zero(
            batch_id=batch.id,
            payload=ConfirmZeroRequest(
                store_id=store.id,
                source_code=source,
                actor="admin",
            ),
            db=db_session,
        )
    response = reconcile_reconciliation_batch(batch_id=batch.id, db=db_session)
    assert response[0].status == "consistent"
    assert get_reconciliation_batch(batch.id, db=db_session).status == "ready_to_close"

    closed = close_reconciliation_batch(
        batch_id=batch.id,
        payload=BatchActorRequest(actor="admin"),
        db=db_session,
    )
    assert closed.status == "closed"
    reopened = reopen_reconciliation_batch(
        batch_id=batch.id,
        payload=BatchReopenRequest(actor="admin", reason="补充文件"),
        db=db_session,
    )
    assert reopened.status == "attention_required"


def test_closed_batch_import_returns_conflict(db_session):
    store = Store(name="民院店", code="MD010", is_active=True)
    db_session.add(store)
    batch = create_reconciliation_batch(
        payload=BatchCreate(business_date=date(2026, 7, 10), actor="admin"),
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
                actor="admin",
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
