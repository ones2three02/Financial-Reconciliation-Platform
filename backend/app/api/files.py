from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend.app.core.db import get_db
from backend.app.crud import import_file as crud_import_file
from backend.app.schemas.import_command import ImportOutcomeRead
from backend.app.schemas.import_file import ImportFile
from backend.app.services.import_pipeline import (
    BatchClosedError,
    ImportWorkbookCommand,
    import_workbook,
)
from backend.app.services.workbook_preflight import PreflightValidationError


router = APIRouter()
LEGACY_DISABLED_MESSAGE = (
    "旧文件操作已停用，请使用批次化的 /files/preflight 和 /files/import 接口"
)


@router.get("/", response_model=list[ImportFile])
def list_import_files(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    return crud_import_file.get_import_files(db, skip=skip, limit=limit)


@router.post("/import", response_model=ImportOutcomeRead)
async def import_file(
    file: UploadFile = File(...),
    batch_id: int = Form(...),
    profile_code: str = Form(...),
    store_id: int | None = Form(None),
    actor: str = Form(...),
    db: Session = Depends(get_db),
):
    filename = (file.filename or "").strip()
    if not filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="当前仅支持 .xlsx 工作簿")
    content = await file.read()
    try:
        return import_workbook(
            db,
            ImportWorkbookCommand(
                batch_id=batch_id,
                filename=filename,
                content=content,
                profile_code=profile_code,
                store_id=store_id,
                actor=actor,
            ),
        )
    except BatchClosedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except PreflightValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/upload")
async def upload_file():
    raise HTTPException(status_code=409, detail=LEGACY_DISABLED_MESSAGE)


@router.post("/confirm-mapping")
def confirm_mapping():
    raise HTTPException(status_code=409, detail=LEGACY_DISABLED_MESSAGE)


@router.post("/{file_id}/reprocess")
def reprocess_file(file_id: int):
    del file_id
    raise HTTPException(status_code=409, detail=LEGACY_DISABLED_MESSAGE)


@router.delete("/{file_id}")
def delete_file(file_id: int, db: Session = Depends(get_db)):
    del file_id, db
    raise HTTPException(
        status_code=409,
        detail="导入和原始数据不可物理删除；请新建当前文件版本后重新提取",
    )
