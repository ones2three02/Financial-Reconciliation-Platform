from datetime import date

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend.app.core.db import get_db
from backend.app.schemas.preflight import PreflightResult
from backend.app.services.workbook_preflight import (
    PreflightValidationError,
    preflight_workbook,
)


router = APIRouter()


@router.post("/preflight", response_model=PreflightResult)
async def preflight_file(
    file: UploadFile = File(...),
    profile_code: str = Form(...),
    business_date: date = Form(...),
    store_id: int | None = Form(None),
    db: Session = Depends(get_db),
):
    del db  # 保持统一依赖入口；预检本身不写数据库。
    filename = (file.filename or "").strip()
    if not filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="当前仅支持 .xlsx 工作簿")
    content = await file.read()
    try:
        return preflight_workbook(
            content,
            profile_code=profile_code,
            business_date=business_date,
            store_id=store_id,
        )
    except PreflightValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
