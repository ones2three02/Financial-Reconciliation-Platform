from datetime import date
from decimal import Decimal
import importlib

import pytest

from backend.app.crud.field_mapping import create_field_mapping, delete_field_mapping
from backend.app.crud.reconciliation import update_reconciliation_result
from backend.app.crud.store import delete_store
from backend.app.models.audit import AuditEvent
from backend.app.models.batch import ReconciliationBatch
from backend.app.models.clean_data import CleanData
from backend.app.models.coverage import SourceCoverage
from backend.app.models.extraction import ExtractionRun
from backend.app.models.field_mapping import FieldMapping
from backend.app.models.import_file import ImportFile
from backend.app.models.raw_data import RawData
from backend.app.models.reconciliation import ReconciliationResult
from backend.app.models.store import Store
from backend.app.schemas.reconciliation import ReconciliationResultUpdate
from backend.app.schemas.field_mapping import FieldMappingCreate


def master_data_service():
    return importlib.import_module("backend.app.services.master_data_service")


def test_store_delete_endpoint_semantics_are_soft_deactivation(db_session):
    store = Store(name="民院店", code="MD010", is_active=True)
    db_session.add(store)
    db_session.commit()

    assert delete_store(db_session, store.id) is True

    preserved = db_session.get(Store, store.id)
    assert preserved is not None
    assert preserved.is_active is False


def test_field_mapping_delete_semantics_are_soft_deactivation(db_session):
    mapping = FieldMapping(
        data_source="legacy",
        target_field="amount",
        source_column="金额",
        is_active=True,
    )
    db_session.add(mapping)
    db_session.commit()

    assert delete_field_mapping(db_session, mapping.id) is True

    preserved = db_session.get(FieldMapping, mapping.id)
    assert preserved is not None
    assert preserved.is_active is False


def test_duplicate_create_does_not_silently_reactivate_mapping(db_session):
    mapping = FieldMapping(
        data_source="meituan",
        target_field="amount",
        source_column="总收入（元）",
        is_active=False,
    )
    db_session.add(mapping)
    db_session.commit()

    existing = create_field_mapping(
        db_session,
        FieldMappingCreate(
            data_source="meituan",
            target_field="amount",
            source_column="总收入（元）",
        ),
    )

    assert existing.id == mapping.id
    assert existing.is_active is False
    assert db_session.query(AuditEvent).count() == 0


def test_field_mapping_rejects_target_not_supported_by_source(db_session):
    with pytest.raises(ValueError, match="不支持的目标字段"):
        create_field_mapping(
            db_session,
            FieldMappingCreate(
                data_source="tonglian",
                target_field="payment_method",
                source_column="付款方式",
            ),
        )


def test_field_mapping_rejects_legacy_output_source(db_session):
    with pytest.raises(ValueError, match="不支持的数据来源"):
        create_field_mapping(
            db_session,
            FieldMappingCreate(
                data_source="cash",
                target_field="amount",
                source_column="金额",
            ),
        )


def test_store_with_current_open_batch_data_cannot_be_disabled(db_session):
    store = Store(name="民院店", code="MD010", is_active=True)
    batch = ReconciliationBatch(
        business_date=date(2026, 7, 10),
        status="attention_required",
        created_by="admin",
    )
    db_session.add_all([store, batch])
    db_session.flush()
    import_file = ImportFile(
        filename="收入.xlsx",
        data_source="sales",
        upload_status="processed",
        batch_id=batch.id,
        profile_code="store_finance_v1",
        profile_version=1,
        store_id=store.id,
        is_current=True,
    )
    db_session.add(import_file)
    db_session.flush()
    raw = RawData(
        import_file_id=import_file.id,
        row_index=2,
        data_source="sales",
        content={"金额": "100"},
    )
    run = ExtractionRun(
        import_file_id=import_file.id,
        profile_code="store_finance_v1",
        profile_version=1,
        status="completed",
        is_current=True,
    )
    db_session.add_all([raw, run])
    db_session.flush()
    db_session.add(
        CleanData(
            raw_data_id=raw.id,
            import_file_id=import_file.id,
            trade_date=batch.business_date,
            original_store_name=store.name,
            standard_store_name=store.name,
            amount=Decimal("100.00"),
            source="sales",
            is_valid=True,
            clean_status="cleaned",
            batch_id=batch.id,
            store_id=store.id,
            extraction_run_id=run.id,
            profile_code="store_finance_v1",
            profile_version=1,
            is_current=True,
        )
    )
    db_session.commit()

    with pytest.raises(ValueError, match="当前未关账批次仍有数据"):
        master_data_service().set_store_active(
            db_session,
            store_id=store.id,
            is_active=False,
            actor="admin",
            reason="暂停营业",
        )

    assert db_session.get(Store, store.id).is_active is True


def test_store_with_manual_zero_in_open_batch_cannot_be_disabled(db_session):
    store = Store(name="民院店", code="MD010", is_active=True)
    batch = ReconciliationBatch(
        business_date=date(2026, 7, 10),
        status="attention_required",
        created_by="admin",
    )
    db_session.add_all([store, batch])
    db_session.flush()
    db_session.add(
        SourceCoverage(
            batch_id=batch.id,
            business_date=batch.business_date,
            store_id=store.id,
            source_code="meituan",
            status="present_zero",
            evidence_type="manual_zero_confirmation",
            amount=Decimal("0.00"),
            file_count=0,
            valid_row_count=0,
            error_row_count=0,
        )
    )
    db_session.commit()

    with pytest.raises(ValueError, match="当前未关账批次仍有数据"):
        master_data_service().set_store_active(
            db_session,
            store_id=store.id,
            is_active=False,
            actor="admin",
            reason="暂停营业",
        )

    assert db_session.get(Store, store.id).is_active is True


def test_store_and_mapping_status_changes_are_audited(db_session):
    store = Store(name="民院店", code="MD010", is_active=True)
    mapping = FieldMapping(
        data_source="meituan",
        target_field="amount",
        source_column="总收入（元）",
        is_active=True,
    )
    db_session.add_all([store, mapping])
    db_session.commit()

    master_data_service().set_store_active(
        db_session,
        store_id=store.id,
        is_active=False,
        actor="admin",
        reason="门店已停业",
    )
    master_data_service().set_field_mapping_active(
        db_session,
        mapping_id=mapping.id,
        is_active=False,
        actor="admin",
        reason="平台列名已停用",
    )
    db_session.commit()

    events = db_session.query(AuditEvent).order_by(AuditEvent.id).all()
    assert [event.event_type for event in events] == [
        "store_deactivated",
        "field_mapping_deactivated",
    ]
    assert events[0].event_data["reason"] == "门店已停业"
    assert events[1].event_data["reason"] == "平台列名已停用"


def test_reconciliation_resolution_update_is_audited(db_session):
    batch = ReconciliationBatch(
        business_date=date(2026, 7, 10),
        status="attention_required",
        created_by="admin",
    )
    result = ReconciliationResult(
        trade_date=batch.business_date,
        standard_store_name="民院店",
        difference=Decimal("10.00"),
        status="discrepancy",
        remarks="待确认",
        is_resolved=False,
    )
    db_session.add(batch)
    db_session.flush()
    result.batch_id = batch.id
    db_session.add(result)
    db_session.commit()

    update_reconciliation_result(
        db_session,
        result.id,
        ReconciliationResultUpdate(is_resolved=True, remarks="已核实"),
        actor="finance",
    )

    audit = db_session.query(AuditEvent).filter_by(
        event_type="reconciliation_result_updated"
    ).one()
    assert audit.actor == "finance"
    assert audit.event_data["previous_is_resolved"] is False
    assert audit.event_data["new_is_resolved"] is True
    assert audit.event_data["previous_remarks"] == "待确认"
    assert audit.event_data["new_remarks"] == "已核实"
