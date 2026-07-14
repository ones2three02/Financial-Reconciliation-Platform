from datetime import UTC, date, datetime
from decimal import Decimal
from io import BytesIO

import pytest
from openpyxl import Workbook
from pydantic import ValidationError

from backend.app.models.audit import AuditEvent
from backend.app.models.clean_data import CleanData
from backend.app.models.coverage import SourceCoverage
from backend.app.models.extraction import ExtractionRun
from backend.app.models.import_file import ImportFile
from backend.app.models.raw_data import RawData
from backend.app.models.reconciliation import ReconciliationResult
from backend.app.models.store import Store, StoreAlias
from backend.app.schemas.import_command import (
    InvalidateImportRequest,
    ResetBatchCurrentDataRequest,
)
from backend.app.services.batch_service import get_or_create_batch
from backend.app.services.import_pipeline import ImportWorkbookCommand, import_workbook
from backend.app.services import import_version_service
from backend.app.services.import_version_service import (
    ImportVersionConflictError,
    invalidate_import_file,
    replace_import_file,
    reset_batch_current_data,
)
from backend.app.services.reconciliation_service import confirm_zero


BUSINESS_DATE = date(2026, 7, 10)


def finance_workbook(*rows: tuple[str, int]) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "收入流水表"
    sheet.append(["日期", "付款方式", "金额"])
    for payment_method, amount in rows:
        sheet.append([datetime(2026, 7, 10), payment_method, amount])
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


def meituan_workbook(raw_store_name: str, amount: int) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "收益明细表"
    sheet.append(["验券/退款/", "消费门店", "总收入（元）", "商家营销费用（元）"])
    sheet.append([datetime(2026, 7, 10), raw_store_name, amount, 0])
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


def setup_batch(db_session):
    store = Store(name="民院店", code="MD010")
    db_session.add(store)
    db_session.flush()
    batch = get_or_create_batch(
        db_session,
        business_date=BUSINESS_DATE,
        actor="admin",
    )
    db_session.commit()
    return batch, store


def import_finance(db_session, batch_id: int, store_id: int, content: bytes):
    return import_workbook(
        db_session,
        ImportWorkbookCommand(
            batch_id=batch_id,
            filename="7月民院财务表.xlsx",
            content=content,
            profile_code="store_finance_v1",
            store_id=store_id,
            actor="finance-user",
        ),
    )


def import_meituan(db_session, batch_id: int, content: bytes):
    return import_workbook(
        db_session,
        ImportWorkbookCommand(
            batch_id=batch_id,
            filename="美团收入.xlsx",
            content=content,
            profile_code="meituan_v1",
            store_id=None,
            actor="finance-user",
        ),
    )


def coverage(db_session, batch_id: int, store_id: int, source: str) -> SourceCoverage:
    return db_session.query(SourceCoverage).filter_by(
        batch_id=batch_id,
        store_id=store_id,
        source_code=source,
    ).one()


def current_amount(db_session, batch_id: int, store_id: int, source: str) -> Decimal:
    rows = db_session.query(CleanData).filter_by(
        batch_id=batch_id,
        store_id=store_id,
        source=source,
        is_current=True,
        is_valid=True,
    ).all()
    return sum((Decimal(str(row.amount)) for row in rows), Decimal("0.00"))


def test_reason_requests_strip_and_validate_input():
    assert InvalidateImportRequest(reason="  导错文件  ").reason == "导错文件"
    assert ResetBatchCurrentDataRequest(
        reason="  整日导错  ",
        confirmation_date=BUSINESS_DATE,
    ).reason == "整日导错"

    with pytest.raises(ValidationError):
        InvalidateImportRequest(reason="   ")
    with pytest.raises(ValidationError):
        InvalidateImportRequest(reason="x" * 501)


def test_replace_finance_file_uses_only_new_version(db_session):
    batch, store = setup_batch(db_session)
    old = import_finance(
        db_session,
        batch.id,
        store.id,
        finance_workbook(("微信", 100), ("现金", 20)),
    )

    outcome = replace_import_file(
        db_session,
        file_id=old.import_file_id,
        filename="7月民院财务表_正确.xlsx",
        content=finance_workbook(("微信", 200), ("现金", 30)),
        reason="原文件金额导出错误",
        actor="finance-user",
    )

    old_file = db_session.get(ImportFile, old.import_file_id)
    new_file = db_session.get(ImportFile, outcome.import_file_id)
    assert old_file.is_current is False
    assert new_file.is_current is True
    assert new_file.supersedes_file_id == old_file.id
    assert current_amount(db_session, batch.id, store.id, "sales") == Decimal("230.00")
    assert current_amount(db_session, batch.id, store.id, "cash") == Decimal("30.00")
    assert coverage(db_session, batch.id, store.id, "sales").amount == Decimal("230.00")
    assert coverage(db_session, batch.id, store.id, "cash").amount == Decimal("30.00")
    assert db_session.query(RawData).filter_by(import_file_id=old_file.id).count() == 2
    assert db_session.query(AuditEvent).filter_by(event_type="file_replaced").one().actor == "finance-user"


def test_failed_replace_keeps_old_version_current(db_session):
    batch, store = setup_batch(db_session)
    old = import_finance(db_session, batch.id, store.id, finance_workbook(("微信", 100)))

    with pytest.raises(Exception):
        replace_import_file(
            db_session,
            file_id=old.import_file_id,
            filename="损坏.xlsx",
            content=b"not-an-xlsx",
            reason="测试失败回滚",
            actor="finance-user",
        )

    assert db_session.get(ImportFile, old.import_file_id).is_current is True
    assert db_session.query(ImportFile).count() == 1
    assert current_amount(db_session, batch.id, store.id, "sales") == Decimal("100.00")


def test_same_content_replace_is_rejected(db_session):
    batch, store = setup_batch(db_session)
    content = finance_workbook(("微信", 100))
    old = import_finance(db_session, batch.id, store.id, content)

    with pytest.raises(ValueError, match="完全相同") as exc_info:
        replace_import_file(
            db_session,
            file_id=old.import_file_id,
            filename="相同内容.xlsx",
            content=content,
            reason="误操作",
            actor="finance-user",
        )
    assert type(exc_info.value) is ValueError


def test_replace_rejects_content_used_by_another_current_file(db_session):
    batch, store = setup_batch(db_session)
    old = import_finance(db_session, batch.id, store.id, finance_workbook(("微信", 100)))
    other_content = finance_workbook(("微信", 200))
    import_finance(db_session, batch.id, store.id, other_content)

    with pytest.raises(ImportVersionConflictError, match="已有内容完全相同"):
        replace_import_file(
            db_session,
            file_id=old.import_file_id,
            filename="与另一文件重复.xlsx",
            content=other_content,
            reason="错误替换目标",
            actor="finance-user",
        )

    assert db_session.get(ImportFile, old.import_file_id).is_current is True
    assert db_session.query(ImportFile).filter_by(is_current=True).count() == 2


def test_replace_channel_file_refreshes_old_and_new_store_scopes(db_session):
    batch, old_store = setup_batch(db_session)
    new_store = Store(name="民院二店", code="MD011")
    db_session.add(new_store)
    db_session.flush()
    old_alias = "美团民院一店"
    new_alias = "美团民院二店"
    db_session.add_all([
        StoreAlias(source_code="meituan", alias_name=old_alias, store_id=old_store.id, status="mapped", confirmed_by="admin", confirmed_at=datetime.now(UTC)),
        StoreAlias(source_code="meituan", alias_name=new_alias, store_id=new_store.id, status="mapped", confirmed_by="admin", confirmed_at=datetime.now(UTC)),
    ])
    db_session.commit()
    old = import_meituan(db_session, batch.id, meituan_workbook(old_alias, 100))

    replace_import_file(
        db_session,
        file_id=old.import_file_id,
        filename="美团收入_正确.xlsx",
        content=meituan_workbook(new_alias, 250),
        reason="原文件选错门店",
        actor="finance-user",
    )

    assert current_amount(db_session, batch.id, old_store.id, "meituan") == Decimal("0.00")
    assert current_amount(db_session, batch.id, new_store.id, "meituan") == Decimal("250.00")
    assert coverage(db_session, batch.id, old_store.id, "meituan").status == "missing"
    assert coverage(db_session, batch.id, new_store.id, "meituan").amount == Decimal("250.00")


def test_invalidate_file_preserves_history_and_refreshes_coverage(db_session):
    batch, store = setup_batch(db_session)
    imported = import_finance(
        db_session,
        batch.id,
        store.id,
        finance_workbook(("微信", 100), ("现金", 20)),
    )
    raw_count = db_session.query(RawData).count()
    clean_count = db_session.query(CleanData).count()

    invalidate_import_file(
        db_session,
        file_id=imported.import_file_id,
        reason="该文件不属于本账期",
        actor="finance-user",
    )

    assert db_session.get(ImportFile, imported.import_file_id).is_current is False
    assert db_session.query(ExtractionRun).filter_by(import_file_id=imported.import_file_id, is_current=True).count() == 0
    assert db_session.query(CleanData).filter_by(import_file_id=imported.import_file_id, is_current=True).count() == 0
    assert db_session.query(RawData).count() == raw_count
    assert db_session.query(CleanData).count() == clean_count
    assert coverage(db_session, batch.id, store.id, "sales").status == "missing"
    assert coverage(db_session, batch.id, store.id, "cash").status == "missing"
    assert db_session.query(AuditEvent).filter_by(event_type="file_invalidated").one().actor == "finance-user"


def test_closed_batch_rejects_file_version_actions(db_session):
    batch, store = setup_batch(db_session)
    imported = import_finance(db_session, batch.id, store.id, finance_workbook(("微信", 100)))
    batch.status = "closed"
    db_session.commit()

    with pytest.raises(ImportVersionConflictError, match="已关账"):
        invalidate_import_file(
            db_session,
            file_id=imported.import_file_id,
            reason="尝试作废",
            actor="finance-user",
        )


def test_reset_batch_retires_current_data_and_manual_zero(db_session):
    batch, store = setup_batch(db_session)
    imported = import_finance(db_session, batch.id, store.id, finance_workbook(("微信", 100)))
    confirm_zero(
        db_session,
        batch_id=batch.id,
        store_id=store.id,
        source_code="tonglian",
        actor="finance-user",
    )
    db_session.commit()
    old_version = batch.version

    reset_batch_current_data(
        db_session,
        batch_id=batch.id,
        reason="当日导出范围全部错误",
        confirmation_date=BUSINESS_DATE,
        actor="finance-user",
    )

    assert db_session.get(ImportFile, imported.import_file_id).is_current is False
    assert db_session.query(CleanData).filter_by(batch_id=batch.id, is_current=True).count() == 0
    for row in db_session.query(SourceCoverage).filter_by(batch_id=batch.id).all():
        assert row.status == "missing"
        assert row.amount == Decimal("0.00")
        assert row.file_count == 0
    db_session.refresh(batch)
    assert batch.version == old_version + 1
    assert batch.status == "attention_required"
    results = db_session.query(ReconciliationResult).filter_by(batch_id=batch.id).all()
    assert results
    assert all(result.status == "incomplete" for result in results)
    assert db_session.query(AuditEvent).filter_by(event_type="batch_current_data_reset").one().actor == "finance-user"


def test_reset_batch_requires_matching_confirmation_date(db_session):
    batch, store = setup_batch(db_session)
    imported = import_finance(db_session, batch.id, store.id, finance_workbook(("微信", 100)))

    with pytest.raises(ValueError, match="确认日期"):
        reset_batch_current_data(
            db_session,
            batch_id=batch.id,
            reason="错误日期确认",
            confirmation_date=date(2026, 7, 11),
            actor="finance-user",
        )

    assert db_session.get(ImportFile, imported.import_file_id).is_current is True


def test_invalidated_file_can_be_restored_from_raw_data(db_session):
    batch, store = setup_batch(db_session)
    imported = import_finance(
        db_session,
        batch.id,
        store.id,
        finance_workbook(("微信", 100)),
    )
    old_run = db_session.get(ExtractionRun, imported.extraction_run_id)
    invalidate_import_file(
        db_session,
        file_id=imported.import_file_id,
        reason="测试作废",
        actor="finance-user",
    )

    outcome = import_version_service.restore_import_file(
        db_session,
        file_id=imported.import_file_id,
        reason="误作废",
        actor="finance-user",
    )

    restored_file = db_session.get(ImportFile, imported.import_file_id)
    restored_run = db_session.get(ExtractionRun, outcome.extraction_run_id)
    assert restored_file.is_current is True
    assert restored_run.id != old_run.id
    assert restored_run.is_current is True
    assert old_run.is_current is False
    assert current_amount(db_session, batch.id, store.id, "sales") == Decimal("100.00")
    assert db_session.query(AuditEvent).filter_by(event_type="file_restored").one().event_data["reason"] == "误作废"


def test_restoring_old_version_retires_current_descendant(db_session):
    batch, store = setup_batch(db_session)
    original = import_finance(
        db_session,
        batch.id,
        store.id,
        finance_workbook(("微信", 100)),
    )
    replacement = replace_import_file(
        db_session,
        file_id=original.import_file_id,
        filename="正确文件.xlsx",
        content=finance_workbook(("微信", 200)),
        reason="替换测试",
        actor="finance-user",
    )

    import_version_service.restore_import_file(
        db_session,
        file_id=original.import_file_id,
        reason="恢复原版",
        actor="finance-user",
    )

    assert db_session.get(ImportFile, original.import_file_id).is_current is True
    assert db_session.get(ImportFile, replacement.import_file_id).is_current is False
    assert current_amount(db_session, batch.id, store.id, "sales") == Decimal("100.00")


def test_restore_rejects_duplicate_independent_current_file(db_session):
    batch, store = setup_batch(db_session)
    content = finance_workbook(("微信", 100))
    original = import_finance(db_session, batch.id, store.id, content)
    invalidate_import_file(
        db_session,
        file_id=original.import_file_id,
        reason="先作废",
        actor="finance-user",
    )
    independent = import_finance(db_session, batch.id, store.id, content)

    with pytest.raises(ImportVersionConflictError, match="相同内容"):
        import_version_service.restore_import_file(
            db_session,
            file_id=original.import_file_id,
            reason="错误恢复",
            actor="finance-user",
        )

    assert db_session.get(ImportFile, independent.import_file_id).is_current is True
    assert db_session.get(ImportFile, original.import_file_id).is_current is False


def test_failed_restore_rolls_back_to_current_descendant(db_session, monkeypatch):
    batch, store = setup_batch(db_session)
    original = import_finance(
        db_session,
        batch.id,
        store.id,
        finance_workbook(("微信", 100)),
    )
    replacement = replace_import_file(
        db_session,
        file_id=original.import_file_id,
        filename="正确文件.xlsx",
        content=finance_workbook(("微信", 200)),
        reason="替换测试",
        actor="finance-user",
    )
    monkeypatch.setattr(
        import_version_service,
        "extract_current_batch_rows",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("恢复提取失败")),
        raising=False,
    )

    with pytest.raises(RuntimeError, match="恢复提取失败"):
        import_version_service.restore_import_file(
            db_session,
            file_id=original.import_file_id,
            reason="测试回滚",
            actor="finance-user",
        )

    assert db_session.get(ImportFile, original.import_file_id).is_current is False
    assert db_session.get(ImportFile, replacement.import_file_id).is_current is True
    assert current_amount(db_session, batch.id, store.id, "sales") == Decimal("200.00")
    assert db_session.query(AuditEvent).filter_by(event_type="file_restored").count() == 0


def test_restore_rejects_current_file_and_closed_batch(db_session):
    batch, store = setup_batch(db_session)
    imported = import_finance(
        db_session,
        batch.id,
        store.id,
        finance_workbook(("微信", 100)),
    )
    with pytest.raises(ImportVersionConflictError, match="当前版本"):
        import_version_service.restore_import_file(
            db_session,
            file_id=imported.import_file_id,
            reason="无需恢复",
            actor="finance-user",
        )

    invalidate_import_file(
        db_session,
        file_id=imported.import_file_id,
        reason="测试作废",
        actor="finance-user",
    )
    batch.status = "closed"
    db_session.commit()
    with pytest.raises(ImportVersionConflictError, match="已关账"):
        import_version_service.restore_import_file(
            db_session,
            file_id=imported.import_file_id,
            reason="关账后恢复",
            actor="finance-user",
        )
