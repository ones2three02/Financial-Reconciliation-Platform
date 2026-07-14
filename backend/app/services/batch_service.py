from datetime import date

from sqlalchemy.orm import Session

from backend.app.models.batch import ReconciliationBatch


def get_or_create_batch(
    db: Session,
    business_date: date,
    actor: str,
) -> ReconciliationBatch:
    clean_actor = actor.strip()
    if not clean_actor:
        raise ValueError("创建批次必须提供操作人")

    existing = (
        db.query(ReconciliationBatch)
        .filter(ReconciliationBatch.business_date == business_date)
        .first()
    )
    if existing is not None:
        return existing

    batch = ReconciliationBatch(
        business_date=business_date,
        status="draft",
        version=1,
        created_by=clean_actor,
    )
    db.add(batch)
    db.flush()
    return batch
