from datetime import date
from decimal import Decimal

import pytest

from backend.app.models.audit import AuditEvent
from backend.app.models.batch import ReconciliationBatch
from backend.app.models.coverage import SourceCoverage
from backend.app.models.quality_issue import DataQualityIssue
from backend.app.models.store import Store
from backend.app.services import reconciliation_service
from backend.app.services.closing_service import (
    BatchNotClosableError,
    close_batch,
    reopen_batch,
)
from backend.app.services.reconciliation_service import confirm_zero, reconcile_batch


BUSINESS_DATE = date(2026, 7, 10)
SOURCES = ("tonglian", "meituan", "douyin", "cash", "sales")


def setup_batch(db_session):
    store = Store(name="民院店", code="MD010", is_active=True)
    batch = ReconciliationBatch(
        business_date=BUSINESS_DATE,
        status="draft",
        version=1,
        created_by="admin",
    )
    db_session.add_all([store, batch])
    db_session.commit()
    return batch, store


def add_coverage(
    db_session,
    batch: ReconciliationBatch,
    store: Store,
    source: str,
    amount: Decimal,
    status: str = "present_data",
):
    coverage = SourceCoverage(
        batch_id=batch.id,
        business_date=batch.business_date,
        store_id=store.id,
        source_code=source,
        status=status,
        evidence_type="data_rows" if status == "present_data" else "file_scope",
        amount=amount,
        file_count=1,
        valid_row_count=1 if status == "present_data" else 0,
        error_row_count=0,
    )
    db_session.add(coverage)
    db_session.flush()
    return coverage


def add_balanced_coverage(db_session, batch, store):
    add_coverage(db_session, batch, store, "tonglian", Decimal("20480.00"))
    add_coverage(db_session, batch, store, "meituan", Decimal("9.90"))
    add_coverage(db_session, batch, store, "douyin", Decimal("296.00"))
    add_coverage(
        db_session,
        batch,
        store,
        "cash",
        Decimal("0.00"),
        status="present_zero",
    )
    add_coverage(db_session, batch, store, "sales", Decimal("20785.90"))
    db_session.commit()


def test_present_zero_and_missing_have_different_status(db_session):
    batch, store = setup_batch(db_session)
    for source in SOURCES:
        if source == "meituan":
            continue
        add_coverage(
            db_session,
            batch,
            store,
            source,
            Decimal("0.00"),
            status="present_zero",
        )
    db_session.commit()

    incomplete = reconcile_batch(db_session, batch.id)[0]
    assert incomplete.status == "incomplete"
    assert incomplete.completeness_status == "incomplete"

    confirm_zero(
        db_session,
        batch_id=batch.id,
        store_id=store.id,
        source_code="meituan",
        actor="admin",
    )
    complete = reconcile_batch(db_session, batch.id)[0]

    assert complete.status == "consistent"
    assert complete.completeness_status == "complete"
    meituan = db_session.query(SourceCoverage).filter_by(
        batch_id=batch.id,
        store_id=store.id,
        source_code="meituan",
    ).one()
    assert meituan.status == "present_zero"
    assert meituan.evidence_type == "manual_zero_confirmation"
    assert db_session.query(AuditEvent).filter_by(
        event_type="source_zero_confirmed"
    ).count() == 1


def test_balanced_example_becomes_ready_to_close(db_session):
    batch, store = setup_batch(db_session)
    add_balanced_coverage(db_session, batch, store)

    result = reconcile_batch(db_session, batch.id)[0]

    assert result.expected_amount == Decimal("20785.90")
    assert result.actual_amount == Decimal("20785.90")
    assert result.difference == Decimal("0.00")
    assert result.status == "consistent"
    assert batch.status == "ready_to_close"


def test_close_rejects_open_quality_issue(db_session):
    batch, store = setup_batch(db_session)
    add_balanced_coverage(db_session, batch, store)
    reconcile_batch(db_session, batch.id)
    db_session.add(
        DataQualityIssue(
            batch_id=batch.id,
            issue_type="unknown_store",
            source_code="meituan",
            raw_value="待确认门店",
            affected_row_count=1,
            affected_amount=Decimal("9.90"),
            status="open",
        )
    )
    db_session.commit()

    with pytest.raises(BatchNotClosableError, match="待确认门店"):
        close_batch(db_session, batch.id, actor="admin")


def test_single_user_close_and_audited_reopen(db_session):
    batch, store = setup_batch(db_session)
    add_balanced_coverage(db_session, batch, store)
    reconcile_batch(db_session, batch.id)

    closed = close_batch(db_session, batch.id, actor="admin")
    assert closed.status == "closed"
    assert closed.closed_by == "admin"

    with pytest.raises(ValueError, match="原因"):
        reopen_batch(db_session, batch.id, actor="admin", reason="   ")

    reopened = reopen_batch(
        db_session,
        batch.id,
        actor="admin",
        reason="补充遗漏文件",
    )
    db_session.commit()

    assert reopened.status == "attention_required"
    assert reopened.version == 2
    assert reopened.reopen_reason == "补充遗漏文件"
    assert [event.event_type for event in db_session.query(AuditEvent).order_by(AuditEvent.id)] == [
        "batch_closed",
        "batch_reopened",
    ]


def test_manual_zero_can_be_revoked_to_missing(db_session):
    batch, store = setup_batch(db_session)
    for source in SOURCES:
        confirm_zero(
            db_session,
            batch_id=batch.id,
            store_id=store.id,
            source_code=source,
            actor="finance",
        )
    reconcile_batch(db_session, batch.id)
    assert db_session.query(SourceCoverage).filter_by(
        batch_id=batch.id,
        store_id=store.id,
        source_code="meituan",
    ).one().status == "present_zero"

    coverage = reconciliation_service.revoke_zero(
        db_session,
        batch_id=batch.id,
        store_id=store.id,
        source_code="meituan",
        reason="误确认",
        actor="finance",
    )

    result = reconcile_batch(db_session, batch.id)[0]
    assert coverage.status == "missing"
    assert coverage.evidence_type is None
    assert result.status == "incomplete"
    audit = db_session.query(AuditEvent).filter_by(
        event_type="source_zero_confirmation_revoked"
    ).one()
    assert audit.actor == "finance"
    assert audit.event_data["reason"] == "误确认"


def test_file_scope_zero_cannot_be_revoked(db_session):
    batch, store = setup_batch(db_session)
    add_coverage(
        db_session,
        batch,
        store,
        "cash",
        Decimal("0.00"),
        status="present_zero",
    )
    db_session.commit()

    with pytest.raises(ValueError, match="只能撤销人工确认"):
        reconciliation_service.revoke_zero(
            db_session,
            batch_id=batch.id,
            store_id=store.id,
            source_code="cash",
            reason="误操作",
            actor="finance",
        )
