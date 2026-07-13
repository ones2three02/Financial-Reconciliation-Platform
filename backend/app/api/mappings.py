from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from backend.app.core.db import get_db
from backend.app.schemas.field_mapping import FieldMapping, FieldMappingCreate, FieldMappingUpdate
from backend.app.crud import field_mapping as crud_field_mapping

router = APIRouter()

@router.get("/", response_model=List[FieldMapping])
def list_field_mappings(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud_field_mapping.get_field_mappings(db, skip=skip, limit=limit)

@router.get("/source/{data_source}", response_model=List[FieldMapping])
def read_mappings_by_source(
    data_source: str, 
    active_only: bool = False, 
    db: Session = Depends(get_db)
):
    return crud_field_mapping.get_mappings_by_source(db, data_source=data_source, is_active_only=active_only)

@router.post("/", response_model=FieldMapping, status_code=status.HTTP_201_CREATED)
def create_field_mapping(mapping: FieldMappingCreate, db: Session = Depends(get_db)):
    return crud_field_mapping.create_field_mapping(db, mapping=mapping)

@router.put("/{mapping_id}", response_model=FieldMapping)
def update_field_mapping(
    mapping_id: int, 
    mapping: FieldMappingUpdate, 
    db: Session = Depends(get_db)
):
    db_mapping = crud_field_mapping.update_field_mapping(db, mapping_id=mapping_id, mapping_in=mapping)
    if not db_mapping:
        raise HTTPException(status_code=404, detail="Field mapping not found")
    return db_mapping

@router.delete("/{mapping_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_field_mapping(mapping_id: int, db: Session = Depends(get_db)):
    success = crud_field_mapping.delete_field_mapping(db, mapping_id=mapping_id)
    if not success:
        raise HTTPException(status_code=404, detail="Field mapping not found")
    return None
