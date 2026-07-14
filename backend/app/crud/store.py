from sqlalchemy.orm import Session
from backend.app.models.store import Store, StoreAlias
from backend.app.schemas.store import StoreCreate, StoreUpdate, StoreAliasCreate
from typing import List, Optional

# --- Store CRUD ---

def get_store(db: Session, store_id: int) -> Optional[Store]:
    return db.query(Store).filter(Store.id == store_id).first()

def get_store_by_name(db: Session, name: str) -> Optional[Store]:
    return db.query(Store).filter(Store.name == name).first()

def get_stores(db: Session, skip: int = 0, limit: int = 100) -> List[Store]:
    return db.query(Store).offset(skip).limit(limit).all()

def generate_next_store_code(db: Session) -> str:
    # Look for highest MDxxx code
    last_store = db.query(Store).filter(Store.code.like("MD%")).order_by(Store.code.desc()).first()
    if last_store and last_store.code:
        try:
            num = int(last_store.code[2:])
            return f"MD{str(num + 1).zfill(3)}"
        except ValueError:
            pass
    # Fallback to store count + 1
    count = db.query(Store).count()
    return f"MD{str(count + 1).zfill(3)}"

def create_store(db: Session, store: StoreCreate) -> Store:
    # Auto generate code if not provided
    code = store.code.strip() if (store.code and store.code.strip()) else None
    if not code:
        code = generate_next_store_code(db)
        
    db_store = Store(
        name=store.name,
        code=code,
        region=store.region,
        manager=store.manager,
        phone=store.phone,
        is_active=store.is_active
    )
    db.add(db_store)
    db.commit()
    db.refresh(db_store)
    
    return db_store

def update_store(db: Session, store_id: int, store_in: StoreUpdate) -> Optional[Store]:
    db_store = get_store(db, store_id)
    if not db_store:
        return None
    for field, value in store_in.model_dump(exclude_unset=True).items():
        setattr(db_store, field, value)
    db.commit()
    db.refresh(db_store)
    return db_store

def delete_store(db: Session, store_id: int) -> bool:
    db_store = get_store(db, store_id)
    if not db_store:
        return False
    db_store.is_active = False
    db.commit()
    return True

# --- StoreAlias CRUD ---

def get_store_alias(db: Session, alias_id: int) -> Optional[StoreAlias]:
    return db.query(StoreAlias).filter(StoreAlias.id == alias_id).first()

def get_store_alias_by_name(
    db: Session,
    alias_name: str,
    source_code: str = "legacy",
) -> Optional[StoreAlias]:
    return (
        db.query(StoreAlias)
        .filter(
            StoreAlias.alias_name == alias_name,
            StoreAlias.source_code == source_code,
        )
        .first()
    )

def get_store_aliases(db: Session, status: Optional[str] = None, skip: int = 0, limit: int = 100) -> List[StoreAlias]:
    query = db.query(StoreAlias)
    if status:
        query = query.filter(StoreAlias.status == status)
    return query.offset(skip).limit(limit).all()

def create_store_alias(db: Session, alias: StoreAliasCreate) -> StoreAlias:
    db_alias = StoreAlias(
        alias_name=alias.alias_name,
        source_code=alias.source_code,
        store_id=None,
        status="pending",
    )
    db.add(db_alias)
    db.commit()
    db.refresh(db_alias)
    return db_alias
