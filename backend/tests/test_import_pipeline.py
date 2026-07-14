from dataclasses import replace
from datetime import date, datetime
from io import BytesIO

import pytest
from openpyxl import Workbook

from backend.app.models.extraction import ExtractionRun
from backend.app.models.import_file import ImportFile
from backend.app.models.raw_data import RawData
from backend.app.models.store import Store
from backend.app.services.batch_service import get_or_create_batch
from backend.app.services.import_pipeline import ImportWorkbookCommand, import_workbook


def finance_workbook(amount: int) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "收入流水表"
    sheet.append(["日期", "付款方式", "金额"])
    sheet.append([datetime(2026, 7, 10), "微信", amount])
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


def create_store(db_session) -> Store:
    store = Store(name="民院店", code="MD010")
    db_session.add(store)
    db_session.commit()
    return store


def create_command(db_session, content: bytes) -> ImportWorkbookCommand:
    store = create_store(db_session)
    batch = get_or_create_batch(
        db_session,
        business_date=date(2026, 7, 10),
        actor="admin",
    )
    db_session.commit()
    return ImportWorkbookCommand(
        batch_id=batch.id,
        filename="7月民院财务表.xlsx",
        content=content,
        profile_code="store_finance_v1",
        store_id=store.id,
        actor="admin",
    )


def test_same_hash_in_same_batch_is_duplicate(db_session):
    command = create_command(db_session, finance_workbook(100))

    first = import_workbook(db_session, command)
    second = import_workbook(db_session, command)

    assert first.status == "imported"
    assert second.status == "duplicate"
    assert second.import_file_id == first.import_file_id
    assert db_session.query(ImportFile).count() == 1


def test_same_filename_with_different_content_is_preserved(db_session):
    command = create_command(db_session, finance_workbook(100))

    first = import_workbook(db_session, command)
    second = import_workbook(
        db_session,
        replace(command, content=finance_workbook(200)),
    )

    assert first.import_file_id != second.import_file_id
    assert db_session.query(ImportFile).count() == 2


def test_failed_raw_write_rolls_back_entire_file(db_session, monkeypatch):
    command = create_command(db_session, finance_workbook(100))

    def fail_raw_write(*args, **kwargs):
        raise RuntimeError("injected raw write failure")

    monkeypatch.setattr(
        "backend.app.services.import_pipeline._persist_raw_rows",
        fail_raw_write,
    )

    with pytest.raises(RuntimeError, match="injected raw write failure"):
        import_workbook(db_session, command)

    assert db_session.query(ImportFile).count() == 0
    assert db_session.query(RawData).count() == 0
    assert db_session.query(ExtractionRun).count() == 0
