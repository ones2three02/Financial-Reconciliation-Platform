from datetime import date
from decimal import Decimal

from backend.app.api.batches import (
    get_reconciliation_batch_detail,
    list_reconciliation_batches,
)
from backend.app.models.batch import ReconciliationBatch
from backend.app.models.coverage import SourceCoverage
from backend.app.models.import_file import ImportFile
from backend.app.models.quality_issue import DataQualityIssue
from backend.app.models.reconciliation import ReconciliationResult
from backend.app.models.store import Store


def _create_batch(db_session, business_date: date) -> ReconciliationBatch:
    batch = ReconciliationBatch(
        business_date=business_date,
        status="attention_required",
        created_by="finance",
    )
    db_session.add(batch)
    db_session.flush()
    return batch


def test_batch_list_is_ordered_by_business_date_descending(db_session):
    older = _create_batch(db_session, date(2026, 7, 9))
    newer = _create_batch(db_session, date(2026, 7, 10))
    db_session.commit()

    batches = list_reconciliation_batches(skip=0, limit=20, db=db_session)

    assert [item.id for item in batches] == [newer.id, older.id]


def test_batch_detail_returns_import_coverage_issue_and_result(db_session):
    store = Store(name="民院店", code="MD010", is_active=True)
    db_session.add(store)
    batch = _create_batch(db_session, date(2026, 7, 10))
    db_session.flush()
    import_file = ImportFile(
        batch_id=batch.id,
        filename="美团收入.xlsx",
        data_source="meituan",
        upload_status="processed",
        row_count=1,
        profile_code="meituan_v1",
        profile_version=1,
        is_current=True,
    )
    db_session.add(import_file)
    db_session.flush()
    historical_file = ImportFile(
        batch_id=batch.id,
        filename="美团收入_历史.xlsx",
        data_source="meituan",
        upload_status="processed",
        row_count=1,
        profile_code="meituan_v1",
        profile_version=1,
        is_current=False,
    )
    db_session.add(historical_file)
    db_session.flush()
    import_file.supersedes_file_id = historical_file.id
    db_session.add_all(
        [
            SourceCoverage(
                batch_id=batch.id,
                business_date=batch.business_date,
                store_id=store.id,
                source_code="meituan",
                status="present_data",
                evidence_type="imported_rows",
                amount=Decimal("9.90"),
                file_count=1,
                valid_row_count=1,
                error_row_count=0,
            ),
            DataQualityIssue(
                batch_id=batch.id,
                import_file_id=import_file.id,
                issue_type="unknown_store",
                source_code="meituan",
                raw_value="示例未知门店",
                affected_row_count=1,
                affected_amount=Decimal("9.90"),
                status="open",
            ),
            ReconciliationResult(
                batch_id=batch.id,
                store_id=store.id,
                trade_date=batch.business_date,
                standard_store_name=store.name,
                meituan_amount=Decimal("9.90"),
                expected_amount=Decimal("9.90"),
                actual_amount=Decimal("0.00"),
                difference=Decimal("9.90"),
                status="incomplete",
                completeness_status="incomplete",
            ),
        ]
    )
    db_session.commit()

    detail = get_reconciliation_batch_detail(batch.id, db=db_session)

    assert detail.batch.id == batch.id
    assert [item.filename for item in detail.import_files] == [
        "美团收入.xlsx",
        "美团收入_历史.xlsx",
    ]
    assert detail.import_files[0].supersedes_file_id == historical_file.id
    assert detail.import_files[1].is_current is False
    assert detail.coverages[0].amount == Decimal("9.90")
    assert detail.quality_issues[0].raw_value == "示例未知门店"
    assert detail.results[0].standard_store_name == "民院店"
