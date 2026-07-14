from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from backend.app.core.db import get_db
from backend.app.api.auth import require_finance
from backend.app.models.auth import AppUser
from backend.app.crud import import_file as crud_import_file
from backend.app.schemas.import_command import (
    ImportOutcomeRead,
    ImportVersionActionRead,
    InvalidateImportRequest,
    RestoreImportRequest,
)
from backend.app.schemas.import_file import ImportFile
from backend.app.services.import_pipeline import (
    BatchClosedError,
    ImportWorkbookCommand,
    import_workbook,
)
from backend.app.services.workbook_preflight import PreflightValidationError
from backend.app.api.upload_utils import read_upload_limited
from backend.app.services.import_version_service import (
    ImportVersionConflictError,
    ImportVersionNotFoundError,
    invalidate_import_file,
    replace_import_file,
    restore_import_file,
)


router = APIRouter()
LEGACY_DISABLED_MESSAGE = (
    "旧文件操作已停用，请使用批次化的 /files/preflight 和 /files/import 接口"
)


@router.get("/", response_model=list[ImportFile])
def list_import_files(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
    db: Session = Depends(get_db),
):
    return crud_import_file.get_import_files(db, skip=skip, limit=limit)


@router.post("/import", response_model=ImportOutcomeRead)
async def import_file(
    file: UploadFile = File(...),
    batch_id: int = Form(...),
    profile_code: str = Form(...),
    store_id: int | None = Form(None),
    current_user: AppUser = Depends(require_finance),
    db: Session = Depends(get_db),
):
    filename = (file.filename or "").strip()
    if not filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="当前仅支持 .xlsx 工作簿")
    content = await read_upload_limited(file)
    try:
        return import_workbook(
            db,
            ImportWorkbookCommand(
                batch_id=batch_id,
                filename=filename,
                content=content,
                profile_code=profile_code,
                store_id=store_id,
                actor=current_user.username,
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


@router.post("/{file_id}/replace", response_model=ImportOutcomeRead)
async def replace_file(
    file_id: int,
    file: UploadFile = File(...),
    reason: str = Form(..., min_length=1, max_length=500),
    current_user: AppUser = Depends(require_finance),
    db: Session = Depends(get_db),
):
    filename = (file.filename or "").strip()
    if not filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="当前仅支持 .xlsx 工作簿")
    content = await read_upload_limited(file)
    try:
        return replace_import_file(
            db,
            file_id=file_id,
            filename=filename,
            content=content,
            reason=reason,
            actor=current_user.username,
        )
    except ImportVersionNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ImportVersionConflictError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except (PreflightValidationError, ValueError) as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{file_id}/invalidate", response_model=ImportVersionActionRead)
def invalidate_file(
    file_id: int,
    payload: InvalidateImportRequest,
    current_user: AppUser = Depends(require_finance),
    db: Session = Depends(get_db),
):
    try:
        import_file = invalidate_import_file(
            db,
            file_id=file_id,
            reason=payload.reason,
            actor=current_user.username,
        )
        return ImportVersionActionRead(
            status="invalidated",
            batch_id=import_file.batch_id,
            file_id=import_file.id,
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


@router.post("/{file_id}/restore", response_model=ImportOutcomeRead)
def restore_file(
    file_id: int,
    payload: RestoreImportRequest,
    current_user: AppUser = Depends(require_finance),
    db: Session = Depends(get_db),
):
    try:
        return restore_import_file(
            db,
            file_id=file_id,
            reason=payload.reason,
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
