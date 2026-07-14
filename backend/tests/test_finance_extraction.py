from datetime import date, datetime
from decimal import Decimal
from io import BytesIO

from openpyxl import Workbook
from sqlalchemy import func

from backend.app.models.clean_data import CleanData
from backend.app.models.coverage import SourceCoverage
from backend.app.models.extraction import ExtractionRun
from backend.app.models.store import Store
from backend.app.services.batch_service import get_or_create_batch
from backend.app.services.import_pipeline import ImportWorkbookCommand, import_workbook


def finance_workbook(rows: list[list[object]]) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "收入流水表"
    sheet.append(["日期", "付款方式", "金额"])
    for row in rows:
        sheet.append(row)
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


def import_finance(db_session, content: bytes):
    store = Store(name="民院店", code="MD010")
    db_session.add(store)
    db_session.flush()
    batch = get_or_create_batch(
        db_session,
        business_date=date(2026, 7, 10),
        actor="admin",
    )
    db_session.commit()
    outcome = import_workbook(
        db_session,
        ImportWorkbookCommand(
            batch_id=batch.id,
            filename="7月民院财务表.xlsx",
            content=content,
            profile_code="store_finance_v1",
            store_id=store.id,
            actor="admin",
        ),
    )
    return batch, store, outcome


def source_amount(db_session, batch_id: int, store_id: int, source: str) -> Decimal:
    value = (
        db_session.query(func.sum(CleanData.amount))
        .filter(
            CleanData.batch_id == batch_id,
            CleanData.store_id == store_id,
            CleanData.source == source,
            CleanData.is_current.is_(True),
        )
        .scalar()
    )
    return Decimal(str(value or 0)).quantize(Decimal("0.01"))


def get_coverage(db_session, batch_id: int, store_id: int, source: str):
    return (
        db_session.query(SourceCoverage)
        .filter(
            SourceCoverage.batch_id == batch_id,
            SourceCoverage.store_id == store_id,
            SourceCoverage.source_code == source,
        )
        .one()
    )


def test_finance_file_generates_sales_and_cash(db_session):
    batch, store, outcome = import_finance(
        db_session,
        finance_workbook(
            [
                [datetime(2026, 7, 10), "微信", 100],
                [datetime(2026, 7, 10), "现金", 20],
                [datetime(2026, 7, 11), "现金", 999],
            ]
        ),
    )

    assert source_amount(db_session, batch.id, store.id, "sales") == Decimal("120.00")
    assert source_amount(db_session, batch.id, store.id, "cash") == Decimal("20.00")
    assert get_coverage(db_session, batch.id, store.id, "sales").status == "present_data"
    cash_coverage = get_coverage(db_session, batch.id, store.id, "cash")
    assert cash_coverage.status == "present_data"
    assert cash_coverage.evidence_type == "data_rows"
    assert db_session.get(ExtractionRun, outcome.extraction_run_id).status == "completed"


def test_finance_without_cash_creates_present_zero(db_session):
    batch, store, _ = import_finance(
        db_session,
        finance_workbook([[datetime(2026, 7, 10), "微信", 100]]),
    )

    assert source_amount(db_session, batch.id, store.id, "sales") == Decimal("100.00")
    assert source_amount(db_session, batch.id, store.id, "cash") == Decimal("0.00")
    assert (
        db_session.query(CleanData)
        .filter(CleanData.batch_id == batch.id, CleanData.source == "cash")
        .count()
        == 0
    )
    cash_coverage = get_coverage(db_session, batch.id, store.id, "cash")
    assert cash_coverage.status == "present_zero"
    assert cash_coverage.evidence_type == "file_scope"
    assert cash_coverage.amount == Decimal("0.00")
