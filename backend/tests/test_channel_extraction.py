from datetime import UTC, date, datetime
from decimal import Decimal
from io import BytesIO

from openpyxl import Workbook
import pytest
from sqlalchemy import func

from backend.app.services import extraction_engine
from backend.app.models.clean_data import CleanData
from backend.app.models.coverage import SourceCoverage
from backend.app.models.extraction import ExtractionRun
from backend.app.models.import_file import ImportFile
from backend.app.models.quality_issue import DataQualityIssue
from backend.app.models.raw_data import RawData
from backend.app.models.store import Store, StoreAlias
from backend.app.services.batch_service import get_or_create_batch
from backend.app.services.import_pipeline import ImportWorkbookCommand, import_workbook
from backend.app.services.store_resolution import confirm_alias


BUSINESS_DATE = date(2026, 7, 10)


def workbook_bytes(
    sheet_name: str,
    headers: list[str],
    rows: list[list[object]],
    *,
    header_row: int = 1,
) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = sheet_name
    for _ in range(1, header_row):
        sheet.append(["报表说明"])
    sheet.append(headers)
    for row in rows:
        sheet.append(row)
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


def add_confirmed_alias(db_session, source: str, alias_name: str, store_id: int):
    alias = StoreAlias(
        source_code=source,
        alias_name=alias_name,
        store_id=store_id,
        status="mapped",
        confirmed_by="admin",
        confirmed_at=datetime.now(UTC),
    )
    db_session.add(alias)
    db_session.commit()
    return alias


def import_channel(db_session, batch_id: int, profile_code: str, content: bytes):
    return import_workbook(
        db_session,
        ImportWorkbookCommand(
            batch_id=batch_id,
            filename=f"{profile_code}.xlsx",
            content=content,
            profile_code=profile_code,
            store_id=None,
            actor="admin",
        ),
    )


def source_amount(db_session, batch_id: int, store_id: int, source: str) -> Decimal:
    value = (
        db_session.query(func.sum(CleanData.amount))
        .filter(
            CleanData.batch_id == batch_id,
            CleanData.store_id == store_id,
            CleanData.source == source,
            CleanData.is_current.is_(True),
            CleanData.is_valid.is_(True),
        )
        .scalar()
    )
    return Decimal(str(value or 0)).quantize(Decimal("0.01"))


def test_douyin_uses_redemption_date_store_and_order_receipt(db_session):
    batch, store = setup_batch(db_session)
    raw_store = "山道曙光游泳馆(曙光商贸城民族大道店)"
    add_confirmed_alias(db_session, "douyin", raw_store, store.id)
    content = workbook_bytes(
        "核销明细",
        ["核销时间", "核销门店", "订单实收"],
        [
            [datetime(2026, 7, 10, 9, 30), raw_store, 296],
            [datetime(2026, 7, 11, 9, 30), raw_store, 999],
        ],
    )

    outcome = import_channel(db_session, batch.id, "douyin_v1", content)

    assert outcome.status == "imported"
    assert source_amount(db_session, batch.id, store.id, "douyin") == Decimal("296.00")


def test_meituan_preserves_signed_marketing_amount(db_session):
    batch, store = setup_batch(db_session)
    raw_store = "武汉 : 山道健身游泳舞蹈(曙光店)"
    add_confirmed_alias(db_session, "meituan", raw_store, store.id)
    content = workbook_bytes(
        "收益明细表",
        ["验券/退款/", "消费门店", "总收入（元）", "商家营销费用（元）"],
        [[datetime(2026, 7, 10), raw_store, 377.40, -35]],
    )

    import_channel(db_session, batch.id, "meituan_v1", content)

    assert source_amount(db_session, batch.id, store.id, "meituan") == Decimal("342.40")


def test_tonglian_aggregates_multiple_confirmed_aliases(db_session):
    batch, store = setup_batch(db_session)
    first_alias = "山道健身－民院健身房"
    second_alias = "山道健身－民院游泳馆"
    add_confirmed_alias(db_session, "tonglian", first_alias, store.id)
    add_confirmed_alias(db_session, "tonglian", second_alias, store.id)
    content = workbook_bytes(
        "sheet1",
        ["统计日期", "门店名", "成功交易金额"],
        [
            [datetime(2026, 7, 10), first_alias, 10000],
            [datetime(2026, 7, 10), second_alias, 10480],
        ],
        header_row=2,
    )

    import_channel(db_session, batch.id, "tonglian_v1", content)

    assert source_amount(db_session, batch.id, store.id, "tonglian") == Decimal("20480.00")
    coverage = (
        db_session.query(SourceCoverage)
        .filter_by(batch_id=batch.id, store_id=store.id, source_code="tonglian")
        .one()
    )
    assert coverage.status == "present_data"
    assert coverage.valid_row_count == 2


def test_tonglian_reextract_skips_historical_summary_raw_data(db_session):
    batch, store = setup_batch(db_session)
    raw_store = "山道健身－民院健身房"
    add_confirmed_alias(db_session, "tonglian", raw_store, store.id)
    content = workbook_bytes(
        "sheet1",
        ["统计日期", "门店名", "成功交易金额"],
        [[datetime(2026, 7, 10), raw_store, 100]],
        header_row=2,
    )
    outcome = import_channel(db_session, batch.id, "tonglian_v1", content)
    summary_raw = RawData(
        import_file_id=outcome.import_file_id,
        row_index=4,
        data_source="tonglian",
        content={"统计日期": "汇总", "门店名": None, "成功交易金额": 100},
    )
    db_session.add(summary_raw)
    db_session.commit()

    extraction_engine.extract_current_batch_rows(db_session, outcome.extraction_run_id)

    current_rows = (
        db_session.query(CleanData)
        .filter(
            CleanData.import_file_id == outcome.import_file_id,
            CleanData.is_current.is_(True),
        )
        .all()
    )
    assert len(current_rows) == 1
    assert all(row.raw_data_id != summary_raw.id for row in current_rows)


def test_unknown_store_blocks_rows_until_manual_confirmation(db_session):
    batch, store = setup_batch(db_session)
    raw_store = "待人工确认的美团门店"
    content = workbook_bytes(
        "收益明细表",
        ["验券/退款/", "消费门店", "总收入（元）", "商家营销费用（元）"],
        [[datetime(2026, 7, 10), raw_store, 10, -0.10]],
    )

    outcome = import_channel(db_session, batch.id, "meituan_v1", content)

    assert outcome.status == "attention_required"
    assert source_amount(db_session, batch.id, store.id, "meituan") == Decimal("0.00")
    issue = db_session.query(DataQualityIssue).one()
    assert issue.status == "open"
    assert issue.affected_amount == Decimal("9.90")
    alias = db_session.query(StoreAlias).filter_by(
        source_code="meituan",
        alias_name=raw_store,
    ).one()
    assert alias.status == "pending"
    run = db_session.get(ExtractionRun, outcome.extraction_run_id)
    assert run.status == "attention_required"

    confirm_alias(db_session, alias_id=alias.id, store_id=store.id, actor="admin")
    db_session.commit()

    assert source_amount(db_session, batch.id, store.id, "meituan") == Decimal("9.90")
    assert issue.status == "resolved"
    assert run.status == "completed"


def test_confirmed_alias_remap_moves_current_amount_and_coverage(db_session):
    batch, first_store = setup_batch(db_session)
    second_store = Store(name="民院二店", code="MD011")
    db_session.add(second_store)
    db_session.commit()
    raw_store = "武汉 : 待改绑的门店"
    alias = add_confirmed_alias(db_session, "meituan", raw_store, first_store.id)
    content = workbook_bytes(
        "收益明细表",
        ["验券/退款/", "消费门店", "总收入（元）", "商家营销费用（元）"],
        [[datetime(2026, 7, 10), raw_store, 10, -0.10]],
    )
    import_channel(db_session, batch.id, "meituan_v1", content)
    assert source_amount(db_session, batch.id, first_store.id, "meituan") == Decimal("9.90")

    confirm_alias(
        db_session,
        alias_id=alias.id,
        store_id=second_store.id,
        actor="admin",
        reason="测试改绑门店",
    )
    db_session.commit()

    assert source_amount(db_session, batch.id, first_store.id, "meituan") == Decimal("0.00")
    assert source_amount(db_session, batch.id, second_store.id, "meituan") == Decimal("9.90")
    old_coverage = db_session.query(SourceCoverage).filter_by(
        batch_id=batch.id,
        store_id=first_store.id,
        source_code="meituan",
    ).one()
    new_coverage = db_session.query(SourceCoverage).filter_by(
        batch_id=batch.id,
        store_id=second_store.id,
        source_code="meituan",
    ).one()
    assert old_coverage.status == "missing"
    assert old_coverage.amount == Decimal("0.00")
    assert new_coverage.status == "present_data"


def test_historical_run_cannot_be_extracted(db_session):
    batch, store = setup_batch(db_session)
    raw_store = "武汉 : 历史门店"
    add_confirmed_alias(db_session, "meituan", raw_store, store.id)
    content = workbook_bytes(
        "收益明细表",
        ["验券/退款/", "消费门店", "总收入（元）", "商家营销费用（元）"],
        [[datetime(2026, 7, 10), raw_store, 10, -0.10]],
    )
    outcome = import_channel(db_session, batch.id, "meituan_v1", content)
    run = db_session.get(ExtractionRun, outcome.extraction_run_id)
    import_file = db_session.get(ImportFile, outcome.import_file_id)
    run.is_current = False
    import_file.is_current = False
    db_session.commit()

    with pytest.raises(extraction_engine.HistoricalExtractionError):
        extraction_engine.extract_current_batch_rows(db_session, run.id)


def test_alias_rebind_does_not_reprocess_historical_file(db_session, monkeypatch):
    batch, first_store = setup_batch(db_session)
    second_store = Store(name="民院二店", code="MD011")
    db_session.add(second_store)
    db_session.commit()
    raw_store = "武汉 : 已作废门店"
    alias = add_confirmed_alias(db_session, "meituan", raw_store, first_store.id)
    content = workbook_bytes(
        "收益明细表",
        ["验券/退款/", "消费门店", "总收入（元）", "商家营销费用（元）"],
        [[datetime(2026, 7, 10), raw_store, 10, -0.10]],
    )
    outcome = import_channel(db_session, batch.id, "meituan_v1", content)
    run = db_session.get(ExtractionRun, outcome.extraction_run_id)
    import_file = db_session.get(ImportFile, outcome.import_file_id)
    run.is_current = False
    import_file.is_current = False
    db_session.commit()
    called_run_ids: list[int] = []
    monkeypatch.setattr(
        extraction_engine,
        "extract_current_batch_rows",
        lambda _db, run_id: called_run_ids.append(run_id),
    )

    confirm_alias(
        db_session,
        alias_id=alias.id,
        store_id=second_store.id,
        actor="admin",
        reason="测试历史文件隔离",
    )

    assert called_run_ids == []
