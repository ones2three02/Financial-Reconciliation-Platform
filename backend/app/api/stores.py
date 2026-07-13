from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from backend.app.core.db import get_db
from backend.app.schemas.store import Store, StoreCreate, StoreUpdate, StoreAlias, StoreAliasCreate, StoreAliasUpdate, StoreAliasWithStore
from backend.app.crud import store as crud_store

router = APIRouter()

# --- Standard Stores ---

@router.get("/", response_model=List[Store])
def list_stores(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud_store.get_stores(db, skip=skip, limit=limit)

@router.post("/", response_model=Store, status_code=status.HTTP_201_CREATED)
def create_store(store: StoreCreate, db: Session = Depends(get_db)):
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
def update_store(store_id: int, store: StoreUpdate, db: Session = Depends(get_db)):
    db_store = crud_store.update_store(db, store_id=store_id, store_in=store)
    if not db_store:
        raise HTTPException(status_code=404, detail="Store not found")
    return db_store

@router.delete("/{store_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_store(store_id: int, db: Session = Depends(get_db)):
    success = crud_store.delete_store(db, store_id=store_id)
    if not success:
        raise HTTPException(status_code=404, detail="Store not found")
    return None


# --- Store Aliases (Mappings) ---

@router.get("/aliases/list", response_model=List[StoreAliasWithStore])
def list_store_aliases(
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    return crud_store.get_store_aliases(db, status=status, skip=skip, limit=limit)

@router.post("/aliases/create", response_model=StoreAlias, status_code=status.HTTP_201_CREATED)
def create_store_alias(alias: StoreAliasCreate, db: Session = Depends(get_db)):
    db_alias = crud_store.get_store_alias_by_name(db, alias_name=alias.alias_name)
    if db_alias:
        # If it exists, let's just update the store_id and status instead of throwing error
        return crud_store.update_store_alias(
            db, 
            alias_id=db_alias.id, 
            alias_in=StoreAliasUpdate(store_id=alias.store_id)
        )
    return crud_store.create_store_alias(db, alias=alias)

@router.put("/aliases/{alias_id}", response_model=StoreAlias)
def update_store_alias(alias_id: int, alias: StoreAliasUpdate, db: Session = Depends(get_db)):
    db_alias = crud_store.update_store_alias(db, alias_id=alias_id, alias_in=alias)
    if not db_alias:
        raise HTTPException(status_code=404, detail="Store alias mapping not found")
    return db_alias
