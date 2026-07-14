from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError

from backend.app.models.audit import AuditEvent
from backend.app.models.batch import ReconciliationBatch
from backend.app.models.coverage import SourceCoverage
from backend.app.models.store import Store, StoreAlias


def create_store(db_session, name: str = "民院店") -> Store:
    store = Store(name=name, code="MD010")
    db_session.add(store)
    db_session.commit()
    return store


def create_batch(db_session) -> ReconciliationBatch:
    batch = ReconciliationBatch(
        business_date=date(2026, 7, 10),
        status="draft",
        created_by="admin",
    )
    db_session.add(batch)
    db_session.commit()
    return batch


def test_one_batch_per_business_date(db_session):
    create_batch(db_session)
    db_session.add(
        ReconciliationBatch(
            business_date=date(2026, 7, 10),
            status="draft",
            created_by="other-user",
        )
    )

    with pytest.raises(IntegrityError):
        db_session.commit()


def test_source_coverage_unique_per_batch_store_source(db_session):
    store = create_store(db_session)
    batch = create_batch(db_session)
    db_session.add_all(
        [
            SourceCoverage(
                batch_id=batch.id,
                business_date=batch.business_date,
                store_id=store.id,
                source_code="cash",
                status="present_zero",
                evidence_type="file_scope",
                amount=0,
            ),
            SourceCoverage(
                batch_id=batch.id,
                business_date=batch.business_date,
                store_id=store.id,
                source_code="cash",
                status="missing",
                evidence_type=None,
                amount=0,
            ),
        ]
    )

    with pytest.raises(IntegrityError):
        db_session.commit()


def test_store_alias_is_unique_per_source(db_session):
    store = create_store(db_session)
    db_session.add_all(
        [
            StoreAlias(
                source_code="meituan",
                alias_name="曙光店",
                store_id=store.id,
                status="mapped",
                confirmed_by="admin",
            ),
            StoreAlias(
                source_code="douyin",
                alias_name="曙光店",
                store_id=None,
                status="pending",
            ),
        ]
    )
    db_session.commit()

    assert db_session.query(StoreAlias).count() == 2


def test_audit_event_does_not_cascade_delete_with_batch():
    foreign_key = next(iter(AuditEvent.__table__.c.batch_id.foreign_keys))

    assert foreign_key.ondelete != "CASCADE"
