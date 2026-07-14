from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.app.core.db import get_db
from backend.app.api.auth import require_finance
from backend.app.models.auth import AppUser
from backend.app.models.batch import ReconciliationBatch
from backend.app.models.coverage import SourceCoverage
from backend.app.models.import_file import ImportFile
from backend.app.models.quality_issue import DataQualityIssue
from backend.app.models.reconciliation import ReconciliationResult as ReconciliationResultModel
from backend.app.schemas.batch import (
    BatchCreate,
    BatchDetailRead,
    BatchRead,
    BatchReopenRequest,
    ConfirmZeroRequest,
)
from backend.app.schemas.reconciliation import ReconciliationResult
from backend.app.schemas.import_command import ResetBatchCurrentDataRequest
from backend.app.services.batch_service import get_or_create_batch
from backend.app.services.closing_service import (
    BatchNotClosableError,
    close_batch,
    reopen_batch,
)
from backend.app.services.reconciliation_service import confirm_zero, reconcile_batch
from backend.app.services.import_version_service import (
    ImportVersionConflictError,
    ImportVersionNotFoundError,
    reset_batch_current_data,
)


router = APIRouter()


@router.get("/", response_model=list[BatchRead])
def list_reconciliation_batches(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    return (
        db.query(ReconciliationBatch)
        .order_by(
            ReconciliationBatch.business_date.desc(),
            ReconciliationBatch.id.desc(),
        )
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.post("/", response_model=BatchRead)
def create_reconciliation_batch(
    payload: BatchCreate,
    current_user: AppUser = Depends(require_finance),
    db: Session = Depends(get_db),
):
    try:
        batch = get_or_create_batch(
            db,
            business_date=payload.business_date,
            actor=current_user.username,
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


@router.get("/{batch_id}/detail", response_model=BatchDetailRead)
def get_reconciliation_batch_detail(
    batch_id: int,
    db: Session = Depends(get_db),
) -> BatchDetailRead:
    batch = db.get(ReconciliationBatch, batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="对账批次不存在")
    import_files = (
        db.query(ImportFile)
        .filter(ImportFile.batch_id == batch_id)
        .order_by(ImportFile.is_current.desc(), ImportFile.id.desc())
        .all()
    )
    coverages = (
        db.query(SourceCoverage)
        .filter(SourceCoverage.batch_id == batch_id)
        .order_by(SourceCoverage.store_id, SourceCoverage.source_code)
        .all()
    )
    quality_issues = (
        db.query(DataQualityIssue)
        .filter(DataQualityIssue.batch_id == batch_id)
        .order_by(DataQualityIssue.status, DataQualityIssue.id)
        .all()
    )
    results = (
        db.query(ReconciliationResultModel)
        .filter(ReconciliationResultModel.batch_id == batch_id)
        .order_by(ReconciliationResultModel.store_id)
        .all()
    )
    return BatchDetailRead(
        batch=batch,
        import_files=import_files,
        coverages=coverages,
        quality_issues=quality_issues,
        results=results,
    )


@router.post("/{batch_id}/reset-current-data", response_model=BatchRead)
def reset_reconciliation_batch_current_data(
    batch_id: int,
    payload: ResetBatchCurrentDataRequest,
    current_user: AppUser = Depends(require_finance),
    db: Session = Depends(get_db),
):
    try:
        return reset_batch_current_data(
            db,
            batch_id=batch_id,
            reason=payload.reason,
            confirmation_date=payload.confirmation_date,
            actor=current_user.username,
        )
    except ImportVersionNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ImportVersionConflictError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{batch_id}/confirm-zero")
def confirm_batch_source_zero(
    batch_id: int,
    payload: ConfirmZeroRequest,
    current_user: AppUser = Depends(require_finance),
    db: Session = Depends(get_db),
):
    try:
        coverage = confirm_zero(
            db,
            batch_id=batch_id,
            store_id=payload.store_id,
            source_code=payload.source_code,
            actor=current_user.username,
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
    current_user: AppUser = Depends(require_finance),
    db: Session = Depends(get_db),
):
    del current_user
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
    current_user: AppUser = Depends(require_finance),
    db: Session = Depends(get_db),
):
    try:
        batch = close_batch(db, batch_id, actor=current_user.username)
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
    current_user: AppUser = Depends(require_finance),
    db: Session = Depends(get_db),
):
    try:
        batch = reopen_batch(
            db,
            batch_id,
            actor=current_user.username,
            reason=payload.reason,
        )
        db.commit()
        db.refresh(batch)
        return batch
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
