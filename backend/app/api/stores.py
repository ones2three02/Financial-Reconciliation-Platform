from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from backend.app.core.db import get_db
from backend.app.api.auth import require_admin
from backend.app.models.auth import AppUser
from backend.app.schemas.store import (
    Store,
    StoreAlias,
    StoreAliasConfirm,
    StoreAliasCreate,
    StoreAliasUpdate,
    StoreAliasWithStore,
    StoreCreate,
    StoreUpdate,
)
from backend.app.crud import store as crud_store
from backend.app.services.store_resolution import confirm_alias
from backend.app.services.master_data_service import set_store_active

router = APIRouter()


# --- Store Aliases (Mappings) ---

@router.get("/aliases/list", response_model=List[StoreAliasWithStore])
def list_store_aliases(
    status: Optional[str] = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
    db: Session = Depends(get_db)
):
    return crud_store.get_store_aliases(db, status=status, skip=skip, limit=limit)


@router.post("/aliases/create", response_model=StoreAlias, status_code=status.HTTP_201_CREATED)
def create_store_alias(
    alias: StoreAliasCreate,
    current_user: AppUser = Depends(require_admin),
    db: Session = Depends(get_db),
):
    db_alias = crud_store.get_store_alias_by_name(
        db,
        alias_name=alias.alias_name,
        source_code=alias.source_code,
    )
    if db_alias is None:
        db_alias = crud_store.create_store_alias(db, alias=alias)
    if alias.store_id is not None:
        try:
            db_alias = confirm_alias(
                db,
                alias_id=db_alias.id,
                store_id=alias.store_id,
                actor=current_user.username,
            )
            db.commit()
            db.refresh(db_alias)
        except ValueError as exc:
            db.rollback()
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    return db_alias


@router.post("/aliases/{alias_id}/confirm", response_model=StoreAlias)
def confirm_store_alias(
    alias_id: int,
    confirmation: StoreAliasConfirm,
    current_user: AppUser = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        alias = confirm_alias(
            db,
            alias_id=alias_id,
            store_id=confirmation.store_id,
            actor=current_user.username,
            reason=confirmation.reason,
        )
        db.commit()
        db.refresh(alias)
        return alias
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/aliases/{alias_id}", response_model=StoreAlias)
def update_store_alias(
    alias_id: int,
    alias: StoreAliasUpdate,
    current_user: AppUser = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return confirm_store_alias(
        alias_id=alias_id,
        confirmation=StoreAliasConfirm(store_id=alias.store_id, reason=alias.reason),
        current_user=current_user,
        db=db,
    )


# --- Standard Stores ---

@router.get("/", response_model=List[Store])
def list_stores(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
    db: Session = Depends(get_db),
):
    return crud_store.get_stores(db, skip=skip, limit=limit)

@router.post("/", response_model=Store, status_code=status.HTTP_201_CREATED)
def create_store(
    store: StoreCreate,
    current_user: AppUser = Depends(require_admin),
    db: Session = Depends(get_db),
):
    del current_user
    db_store = crud_store.get_store_by_name(db, name=store.name)
    if db_store:
        raise HTTPException(
            status_code=400,
            detail=f"Store with name '{store.name}' already exists."
        )
    return crud_store.create_store(db, store=store)

@router.get("/{store_id}", response_model=Store)
def read_store(store_id: int, db: Session = Depends(get_db)):
    db_store = crud_store.get_store(db, store_id=store_id)
    if not db_store:
        raise HTTPException(status_code=404, detail="Store not found")
    return db_store

@router.put("/{store_id}", response_model=Store)
def update_store(
    store_id: int,
    store: StoreUpdate,
    current_user: AppUser = Depends(require_admin),
    db: Session = Depends(get_db),
):
    db_store = crud_store.get_store(db, store_id=store_id)
    if db_store is None:
        raise HTTPException(status_code=404, detail="Store not found")
    values = store.model_dump(exclude_unset=True)
    reason = values.pop("status_change_reason", None)
    requested_active = values.pop("is_active", None)
    try:
        if requested_active is not None and bool(db_store.is_active) != requested_active:
            set_store_active(
                db,
                store_id=store_id,
                is_active=requested_active,
                actor=current_user.username,
                reason=reason or "",
            )
        for field, value in values.items():
            setattr(db_store, field, value)
        db.commit()
        db.refresh(db_store)
        return db_store
    except ValueError as exc:
        db.rollback()
        status_code = 409 if "仍有数据" in str(exc) else 400
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc

@router.delete("/{store_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_store(
    store_id: int,
    current_user: AppUser = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if crud_store.get_store(db, store_id=store_id) is None:
        raise HTTPException(status_code=404, detail="Store not found")
    try:
        set_store_active(
            db,
            store_id=store_id,
            is_active=False,
            actor=current_user.username,
            reason="通过兼容接口停用门店",
        )
        db.commit()
        return None
    except ValueError as exc:
        db.rollback()
        status_code = 409 if "仍有数据" in str(exc) else 400
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
