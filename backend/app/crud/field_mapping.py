from sqlalchemy.orm import Session
from backend.app.models.field_mapping import FieldMapping
from backend.app.schemas.field_mapping import FieldMappingCreate, FieldMappingUpdate
from backend.app.services.field_binding import validate_field_mapping_values
from typing import List, Optional

def get_field_mapping(db: Session, mapping_id: int) -> Optional[FieldMapping]:
    return db.query(FieldMapping).filter(FieldMapping.id == mapping_id).first()

def get_field_mappings(db: Session, skip: int = 0, limit: int = 100) -> List[FieldMapping]:
    return db.query(FieldMapping).offset(skip).limit(limit).all()

def get_mappings_by_source(db: Session, data_source: str, is_active_only: bool = True) -> List[FieldMapping]:
    query = db.query(FieldMapping).filter(FieldMapping.data_source == data_source)
    if is_active_only:
        query = query.filter(FieldMapping.is_active == True)
    return query.all()

def create_field_mapping(db: Session, mapping: FieldMappingCreate) -> FieldMapping:
    data_source, target_field, source_column = validate_field_mapping_values(
        mapping.data_source,
        mapping.target_field,
        mapping.source_column,
    )
    # Check if a mapping with the same source, target field and source column already exists
    existing = db.query(FieldMapping).filter(
        FieldMapping.data_source == data_source,
        FieldMapping.target_field == target_field,
        FieldMapping.source_column == source_column,
    ).first()
    if existing:
        # 已停用映射只能通过显式“重新启用”流程恢复，避免绕过原因和审计。
        return existing

    db_mapping = FieldMapping(
        data_source=data_source,
        target_field=target_field,
        source_column=source_column,
        is_active=mapping.is_active,
    )
    db.add(db_mapping)
    db.commit()
    db.refresh(db_mapping)
    return db_mapping

def update_field_mapping(db: Session, mapping_id: int, mapping_in: FieldMappingUpdate) -> Optional[FieldMapping]:
    db_mapping = get_field_mapping(db, mapping_id)
    if not db_mapping:
        return None
    values = mapping_in.model_dump(exclude_unset=True)
    values.pop("status_change_reason", None)
    data_source, target_field, source_column = validate_field_mapping_values(
        values.get("data_source", db_mapping.data_source),
        values.get("target_field", db_mapping.target_field),
        values.get("source_column", db_mapping.source_column),
    )
    values.update(
        data_source=data_source,
        target_field=target_field,
        source_column=source_column,
    )
    duplicate = db.query(FieldMapping).filter(
        FieldMapping.id != mapping_id,
        FieldMapping.data_source == data_source,
        FieldMapping.target_field == target_field,
        FieldMapping.source_column == source_column,
    ).first()
    if duplicate:
        raise ValueError("相同字段映射已存在")
    for field, value in values.items():
        setattr(db_mapping, field, value)
    db.commit()
    db.refresh(db_mapping)
    return db_mapping

def delete_field_mapping(db: Session, mapping_id: int) -> bool:
    db_mapping = get_field_mapping(db, mapping_id)
    if not db_mapping:
        return False
    db_mapping.is_active = False
    db.commit()
    return True
