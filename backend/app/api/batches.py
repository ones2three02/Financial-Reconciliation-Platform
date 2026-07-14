from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.core.db import get_db
from backend.app.models.batch import ReconciliationBatch
from backend.app.schemas.batch import (
    BatchActorRequest,
    BatchCreate,
    BatchRead,
    BatchReopenRequest,
    ConfirmZeroRequest,
)
from backend.app.schemas.reconciliation import ReconciliationResult
from backend.app.services.batch_service import get_or_create_batch
from backend.app.services.closing_service import (
    BatchNotClosableError,
    close_batch,
    reopen_batch,
)
from backend.app.services.reconciliation_service import confirm_zero, reconcile_batch


router = APIRouter()


@router.post("/", response_model=BatchRead)
def create_reconciliation_batch(
    payload: BatchCreate,
    db: Session = Depends(get_db),
):
    try:
        batch = get_or_create_batch(
            db,
            business_date=payload.business_date,
            actor=payload.actor,
        )
        db.commit()
        db.refresh(batch)
        return batch
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{batch_id}", response_model=BatchRead)
def get_reconciliation_batch(batch_id: int, db: Session = Depends(get_db)):
    batch = db.get(ReconciliationBatch, batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="对账批次不存在")
    return batch


@router.post("/{batch_id}/confirm-zero")
def confirm_batch_source_zero(
    batch_id: int,
    payload: ConfirmZeroRequest,
    db: Session = Depends(get_db),
):
    try:
        coverage = confirm_zero(
            db,
            batch_id=batch_id,
            store_id=payload.store_id,
            source_code=payload.source_code,
            actor=payload.actor,
        )
        db.commit()
        return {
            "batch_id": coverage.batch_id,
            "store_id": coverage.store_id,
            "source_code": coverage.source_code,
            "status": coverage.status,
            "evidence_type": coverage.evidence_type,
        }
    except ValueError as exc:
        db.rollback()
        status_code = 409 if "已关账" in str(exc) else 400
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc


@router.post("/{batch_id}/reconcile", response_model=list[ReconciliationResult])
def reconcile_reconciliation_batch(
    batch_id: int,
    db: Session = Depends(get_db),
):
    try:
        results = reconcile_batch(db, batch_id)
        db.commit()
        return results
    except ValueError as exc:
        db.rollback()
        status_code = 409 if "已关账" in str(exc) else 400
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc


@router.post("/{batch_id}/close", response_model=BatchRead)
def close_reconciliation_batch(
    batch_id: int,
    payload: BatchActorRequest,
    db: Session = Depends(get_db),
):
    try:
        batch = close_batch(db, batch_id, actor=payload.actor)
        db.commit()
        db.refresh(batch)
        return batch
    except BatchNotClosableError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{batch_id}/reopen", response_model=BatchRead)
def reopen_reconciliation_batch(
    batch_id: int,
    payload: BatchReopenRequest,
    db: Session = Depends(get_db),
):
    try:
        batch = reopen_batch(
            db,
            batch_id,
            actor=payload.actor,
            reason=payload.reason,
        )
        db.commit()
        db.refresh(batch)
        return batch
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
