from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from backend.app.core.db import get_db
from backend.app.schemas.import_file import ImportFile
from backend.app.crud import import_file as crud_import_file
from backend.app.services.parser import parse_excel_file
from backend.app.services.cleaner import clean_import_file_data
from backend.app.services.reconciler import run_reconciliation_for_import_file
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/", response_model=List[ImportFile])
def list_import_files(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud_import_file.get_import_files(db, skip=skip, limit=limit)

@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    data_source: str = Form(...),  # "tonglian", "meituan", "douyin", "cash", "sales"
    db: Session = Depends(get_db)
):
    if data_source not in ["tonglian", "meituan", "douyin", "cash", "sales"]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid data source '{data_source}'. Must be one of: tonglian, meituan, douyin, cash, sales."
        )
        
    try:
        content = await file.read()
        
        # 1. Parse Excel to raw tables
        import_file_record, _ = parse_excel_file(
            db=db,
            file_content=content,
            filename=file.filename,
            data_source=data_source
        )
        
        # 2. Run Cleaner (RawData -> CleanData)
        clean_summary = clean_import_file_data(db, import_file_id=import_file_record.id)
        
        # 3. Run Reconciler (CleanData -> ReconciliationResult)
        reconciled_rows = run_reconciliation_for_import_file(db, import_file_id=import_file_record.id)
        
        return {
            "file": import_file_record,
            "cleaning_summary": clean_summary,
            "reconciliation_count": len(reconciled_rows)
        }
        
    except Exception as e:
        logger.exception("Upload and processing failed")
        raise HTTPException(
            status_code=500,
            detail=f"File processing failed: {str(e)}"
        )

@router.post("/{file_id}/reprocess")
def reprocess_file(file_id: int, db: Session = Depends(get_db)):
    """
    Reprocesses an already uploaded file (cleans and reconciles it again).
    Useful after field mappings or store mappings have changed.
    """
    import_file_record = crud_import_file.get_import_file(db, file_id=file_id)
    if not import_file_record:
        raise HTTPException(status_code=404, detail="Import record not found")
        
    try:
        # 1. Run Cleaner again
        clean_summary = clean_import_file_data(db, import_file_id=file_id)
        
        # 2. Run Reconciler again
        reconciled_rows = run_reconciliation_for_import_file(db, import_file_id=file_id)
        
        # Update import file status
        crud_import_file.update_import_file_status(
            db, 
            file_id=file_id, 
            status="parsed" if clean_summary["error"] == 0 else "failed",
            row_count=import_file_record.row_count
        )
        
        return {
            "status": "success",
            "cleaning_summary": clean_summary,
            "reconciliation_count": len(reconciled_rows)
        }
    except Exception as e:
        logger.exception(f"Reprocessing of file {file_id} failed")
        raise HTTPException(status_code=500, detail=str(e))
