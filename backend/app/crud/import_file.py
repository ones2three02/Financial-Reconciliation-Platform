from sqlalchemy.orm import Session
from backend.app.models.import_file import ImportFile
from backend.app.schemas.import_file import ImportFileCreate
from typing import List, Optional

def get_import_file(db: Session, file_id: int) -> Optional[ImportFile]:
    return db.query(ImportFile).filter(ImportFile.id == file_id).first()

def get_import_files(db: Session, skip: int = 0, limit: int = 100) -> List[ImportFile]:
    return db.query(ImportFile).order_by(ImportFile.uploaded_at.desc()).offset(skip).limit(limit).all()

def create_import_file(db: Session, import_file: ImportFileCreate) -> ImportFile:
    db_file = ImportFile(**import_file.model_dump())
    db.add(db_file)
    db.commit()
    db.refresh(db_file)
    return db_file

def update_import_file_status(db: Session, file_id: int, status: str, row_count: int = 0, error_message: Optional[str] = None) -> Optional[ImportFile]:
    db_file = get_import_file(db, file_id)
    if not db_file:
        return None
    db_file.upload_status = status
    db_file.row_count = row_count
    db_file.error_message = error_message
    db.commit()
    db.refresh(db_file)
    return db_file
