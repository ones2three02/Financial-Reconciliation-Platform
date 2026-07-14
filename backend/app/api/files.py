from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from backend.app.core.db import get_db
from backend.app.schemas.import_file import ImportFile
from backend.app.crud import import_file as crud_import_file
from backend.app.services.parser import parse_excel_file
from backend.app.services.cleaner import clean_import_file_data
from backend.app.services.reconciler import run_reconciliation_for_import_file
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

class ConfirmMappingRequest(BaseModel):
    import_file_id: int
    mappings: Dict[str, str]

@router.get("/", response_model=List[ImportFile])
def list_import_files(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud_import_file.get_import_files(db, skip=skip, limit=limit)

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    data_source: str = Form(...),  # "tonglian", "meituan", "douyin", "cash", "sales"
    store_id: Optional[int] = Form(None),
    db: Session = Depends(get_db)
):
    if data_source not in ["tonglian", "meituan", "douyin", "cash", "sales"]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid data source '{data_source}'. Must be one of: tonglian, meituan, douyin, cash, sales."
        )
        
    try:
        content = await file.read()
        
        # Check if a file with the same name and data source already exists
        existing_query = db.query(ImportFile).filter(
            ImportFile.filename == file.filename,
            ImportFile.data_source == data_source
        )
        if store_id is not None:
            existing_query = existing_query.filter(ImportFile.store_id == store_id)
            
        existing_file = existing_query.first()
        overwritten = False
        if existing_file:
            logger.info(f"Duplicate upload detected for file '{file.filename}' under source '{data_source}'. Overwriting...")
            from backend.app.models.clean_data import CleanData
            from backend.app.services.reconciler import run_reconciliation_for_date
            
            # 1. Find all dates affected by this file's clean data
            dates_query = db.query(CleanData.trade_date).filter(
                CleanData.import_file_id == existing_file.id
            ).distinct().all()
            affected_dates = [d[0] for d in dates_query]
            
            # 2. Delete the old import file record (cascades raw_data and clean_data deletion)
            db.delete(existing_file)
            db.commit()
            
            # 3. Recalculate reconciliation for all affected dates
            for t_date in affected_dates:
                run_reconciliation_for_date(db, target_date=t_date)
            overwritten = True
            
        # 1. Parse Excel to raw tables
        import_file_record, raw_rows, detected_maps = parse_excel_file(
            db=db,
            file_content=content,
            filename=file.filename,
            data_source=data_source,
            store_id=store_id
        )
        
        # Check if we have all 3 standard fields mapped
        missing_fields = [f for f in ["trade_date", "store_name", "amount"] if f not in detected_maps]
        if missing_fields:
            # Update status to pending_mapping
            crud_import_file.update_import_file_status(
                db, 
                file_id=import_file_record.id, 
                status="pending_mapping",
                row_count=import_file_record.row_count
            )
            
            # Extract excel columns from the raw content of the first row (excluding metadata)
            cols = []
            if raw_rows:
                cols = [k for k in raw_rows[0].content.keys() if k != "_detected_mappings"]
                
            return {
                "status": "requires_column_mapping",
                "import_file_id": import_file_record.id,
                "filename": file.filename,
                "data_source": data_source,
                "columns": cols,
                "detected_mappings": detected_maps
            }
        
        # 2. Run Cleaner (RawData -> CleanData)
        clean_summary = clean_import_file_data(db, import_file_id=import_file_record.id)
        
        # 3. Run Reconciler (CleanData -> ReconciliationResult)
        reconciled_rows = run_reconciliation_for_import_file(db, import_file_id=import_file_record.id)
        
        return {
            "status": "success",
            "file": import_file_record,
            "cleaning_summary": clean_summary,
            "reconciliation_count": len(reconciled_rows),
            "overwritten": overwritten
        }
        
    except Exception as e:
        logger.exception("Upload and processing failed")
        raise HTTPException(
            status_code=500,
            detail=f"File processing failed: {str(e)}"
        )

@router.post("/confirm-mapping")
def confirm_mapping(req: ConfirmMappingRequest, db: Session = Depends(get_db)):
    """
    Called when frontend submits a manual column mapping for an upload.
    Saves mappings, updates raw rows, cleans and reconciles the dataset.
    """
    import_file_record = crud_import_file.get_import_file(db, file_id=req.import_file_id)
    if not import_file_record:
        raise HTTPException(status_code=404, detail="Import record not found")
        
    try:
        from backend.app.models.field_mapping import FieldMapping
        from backend.app.models.raw_data import RawData
        
        # Delete old mappings for this source
        db.query(FieldMapping).filter(
            FieldMapping.data_source == import_file_record.data_source
        ).delete()
        
        # Save new mappings
        for target, col in req.mappings.items():
            new_map = FieldMapping(
                data_source=import_file_record.data_source,
                target_field=target,
                source_column=col,
                is_active=True
            )
            db.add(new_map)
        db.commit()
        
        # Update raw data content detected mappings for this file so cleaner uses them!
        raw_rows = db.query(RawData).filter(RawData.import_file_id == req.import_file_id).all()
        for row in raw_rows:
            if row.content:
                content_copy = dict(row.content)
                content_copy["_detected_mappings"] = req.mappings
                row.content = content_copy
        db.commit()
        
        # Run Cleaner (RawData -> CleanData)
        clean_summary = clean_import_file_data(db, import_file_id=req.import_file_id)
        
        # Run Reconciler (CleanData -> ReconciliationResult)
        reconciled_rows = run_reconciliation_for_import_file(db, import_file_id=req.import_file_id)
        
        # Update status
        crud_import_file.update_import_file_status(
            db, 
            file_id=req.import_file_id, 
            status="parsed" if clean_summary["error"] == 0 else "failed",
            row_count=import_file_record.row_count
        )
        
        return {
            "status": "success",
            "cleaning_summary": clean_summary,
            "reconciliation_count": len(reconciled_rows)
        }
    except Exception as e:
        logger.exception(f"Reprocessing of file {req.import_file_id} failed")
        raise HTTPException(status_code=500, detail=str(e))

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
        # Run Cleaner again
        clean_summary = clean_import_file_data(db, import_file_id=file_id)
        
        # Run Reconciler again
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

@router.delete("/{file_id}", status_code=status.HTTP_200_OK)
def delete_file(file_id: int, db: Session = Depends(get_db)):
    """
    Deletes an imported file, all its raw/clean data, and recalculates affected trade dates.
    """
    import_file_record = crud_import_file.get_import_file(db, file_id=file_id)
    if not import_file_record:
        raise HTTPException(status_code=404, detail="Import record not found")
        
    try:
        from backend.app.models.clean_data import CleanData
        from backend.app.services.reconciler import run_reconciliation_for_date
        
        # 1. Find all dates affected by this file's clean data
        dates_query = db.query(CleanData.trade_date).filter(
            CleanData.import_file_id == file_id
        ).distinct().all()
        affected_dates = [d[0] for d in dates_query]
        
        # 2. Delete the import file (cascades raw_data and clean_data deletion)
        db.delete(import_file_record)
        db.commit()
        
        # 3. Recalculate reconciliation for all affected dates
        for t_date in affected_dates:
            run_reconciliation_for_date(db, target_date=t_date)
            
        return {"status": "success", "message": f"File {file_id} deleted and reconciliation recalculated."}
    except Exception as e:
        logger.exception(f"Deletion of file {file_id} failed")
        raise HTTPException(status_code=500, detail=str(e))
