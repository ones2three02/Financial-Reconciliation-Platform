from datetime import date

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend.app.core.db import get_db
from backend.app.api.auth import require_finance
from backend.app.models.auth import AppUser
from backend.app.schemas.preflight import PreflightResult
from backend.app.services.workbook_preflight import (
    PreflightValidationError,
    preflight_workbook,
)
from backend.app.api.upload_utils import read_upload_limited


router = APIRouter()


@router.post("/preflight", response_model=PreflightResult)
async def preflight_file(
    file: UploadFile = File(...),
    profile_code: str = Form(...),
    business_date: date = Form(...),
    store_id: int | None = Form(None),
    current_user: AppUser = Depends(require_finance),
    db: Session = Depends(get_db),
):
    del current_user
    filename = (file.filename or "").strip()
    if not filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="当前仅支持 .xlsx 工作簿")
    content = await read_upload_limited(file)
    try:
        return preflight_workbook(
            content,
            profile_code=profile_code,
            business_date=business_date,
            store_id=store_id,
            db=db,
        )
    except PreflightValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
