from datetime import date

from sqlalchemy.orm import Session

from backend.app.models.batch import ReconciliationBatch
from backend.app.models.clean_data import CleanData
from backend.app.models.reconciliation import ReconciliationResult
from backend.app.services.batch_service import get_or_create_batch
from backend.app.services.reconciliation_service import reconcile_batch


def run_reconciliation_for_date(
    db: Session,
    target_date: date,
) -> list[ReconciliationResult]:
    """兼容旧调用入口；所有计算统一进入批次完整性对账。"""
    batch = (
        db.query(ReconciliationBatch)
        .filter(ReconciliationBatch.business_date == target_date)
        .first()
    )
    if batch is None:
        batch = get_or_create_batch(db, target_date, actor="system")
    return reconcile_batch(db, batch.id)


def run_reconciliation_for_import_file(
    db: Session,
    import_file_id: int,
) -> list[ReconciliationResult]:
    dates = [
        trade_date
        for (trade_date,) in (
            db.query(CleanData.trade_date)
            .filter(CleanData.import_file_id == import_file_id)
            .distinct()
            .all()
        )
    ]
    results: list[ReconciliationResult] = []
    for trade_date in dates:
        results.extend(run_reconciliation_for_date(db, trade_date))
    return results
