import pytest
from decimal import Decimal
from datetime import UTC, date, datetime
from backend.app.models.store import Store, StoreAlias
from backend.app.models.field_mapping import FieldMapping
from backend.app.models.import_file import ImportFile
from backend.app.models.raw_data import RawData
from backend.app.models.clean_data import CleanData
from backend.app.models.reconciliation import ReconciliationResult
from backend.app.services.cleaner import clean_amount, clean_date, get_or_create_store_alias, clean_import_file_data
from backend.app.services.reconciler import run_reconciliation_for_date

# --- Cleaner Unit Tests ---

def test_clean_amount():
    assert clean_amount("1,234.56") == Decimal("1234.56")
    assert clean_amount("¥99.00") == Decimal("99.00")
    assert clean_amount(" -10.5 ") == Decimal("-10.50")
    assert clean_amount("(150.00)") == Decimal("-150.00")
    assert clean_amount(None) == Decimal("0.00")
    assert clean_amount("") == Decimal("0.00")
    with pytest.raises(ValueError):
        clean_amount("abc")

def test_clean_date():
    assert clean_date("2026-07-13") == date(2026, 7, 13)
    assert clean_date("2026/07/13 12:00:00") == date(2026, 7, 13)
    assert clean_date("20260713") == date(2026, 7, 13)
    assert clean_date(date(2026, 7, 13)) == date(2026, 7, 13)
    with pytest.raises(ValueError):
        clean_date("invalid-date")

def test_store_alias_matching(db_session):
    # 1. Create standard store
    store = Store(name="杨一一店")
    db_session.add(store)
    db_session.commit()
    
    # 2. Check alias mapping (exact match standard name should auto-bind)
    std_name, status = get_or_create_store_alias(db_session, "杨一一店")
    assert std_name == "杨一一店"
    assert status == "cleaned"
    
    # 3. New alias should be added as pending
    std_name2, status2 = get_or_create_store_alias(db_session, "杨一一游泳馆")
    assert std_name2 is None
    assert status2 == "pending_store_mapping"
    
    alias_record = db_session.query(StoreAlias).filter(StoreAlias.alias_name == "杨一一游泳馆").first()
    assert alias_record is not None
    assert alias_record.status == "pending"

# --- E2E Engine Logic Test ---

def test_reconciliation_calculation(db_session):
    # 1. Setup Standard Store and Aliases
    store = Store(name="杨一一店")
    db_session.add(store)
    db_session.commit()
    
    # Create mapped aliases
    alias1 = StoreAlias(
        source_code="legacy",
        alias_name="杨一一游泳馆",
        store_id=store.id,
        status="mapped",
        confirmed_by="test",
        confirmed_at=datetime.now(UTC),
    )
    alias2 = StoreAlias(
        source_code="legacy",
        alias_name="杨一店",
        store_id=store.id,
        status="mapped",
        confirmed_by="test",
        confirmed_at=datetime.now(UTC),
    )
    db_session.add_all([alias1, alias2])
    db_session.commit()
    
    # 2. Create mock ImportFile and RawData
    imp_file = ImportFile(filename="test.xlsx", data_source="tonglian", upload_status="parsed")
    db_session.add(imp_file)
    db_session.commit()
    
    # Map headers: content key matches standard field column
    detected_maps = {
        "trade_date": "日期",
        "store_name": "店名",
        "amount": "实收"
    }
    
    raw1 = RawData(
        import_file_id=imp_file.id,
        row_index=1,
        data_source="tonglian",
        content={"日期": "2026-07-13", "店名": "杨一一游泳馆", "实收": "100.00", "_detected_mappings": detected_maps}
    )
    # Sales data file
    sales_imp = ImportFile(filename="sales.xlsx", data_source="sales", upload_status="parsed")
    db_session.add(sales_imp)
    db_session.commit()
    
    raw2 = RawData(
        import_file_id=sales_imp.id,
        row_index=1,
        data_source="sales",
        content={"日期": "2026-07-13", "店名": "杨一店", "实收": "120.00", "_detected_mappings": detected_maps}
    )
    
    # Cash data file
    cash_imp = ImportFile(filename="cash.xlsx", data_source="cash", upload_status="parsed")
    db_session.add(cash_imp)
    db_session.commit()
    
    raw3 = RawData(
        import_file_id=cash_imp.id,
        row_index=1,
        data_source="cash",
        content={
            "日期": "2026-07-13",
            "店名": "杨一店",
            "付款方式": "现金",
            "实收": "20.00",
            "_detected_mappings": detected_maps,
        }
    )
    
    db_session.add_all([raw1, raw2, raw3])
    db_session.commit()
    
    # 3. Clean files data
    clean_import_file_data(db_session, imp_file.id)
    clean_import_file_data(db_session, sales_imp.id)
    clean_import_file_data(db_session, cash_imp.id)
    
    # Verify clean_data rows
    clean_rows = db_session.query(CleanData).all()
    assert len(clean_rows) == 3
    for cr in clean_rows:
        assert cr.standard_store_name == "杨一一店"
        
    # 4. Run reconciler
    reconciled = run_reconciliation_for_date(db_session, date(2026, 7, 13))
    assert len(reconciled) == 1
    
    res = reconciled[0]
    assert res.tonglian_amount == Decimal("100.00")
    assert res.sales_amount == Decimal("120.00")
    assert res.cash_amount == Decimal("20.00")
    assert res.expected_amount == Decimal("100.00")  # expected = tonglian + meituan + douyin = 100 + 0 + 0 = 100
    assert res.actual_amount == Decimal("100.00")    # actual = sales - cash = 120 - 20 = 100
    assert res.difference == Decimal("0.00")
    assert res.status == "consistent"
