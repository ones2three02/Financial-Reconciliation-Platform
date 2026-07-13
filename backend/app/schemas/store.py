from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List

# StoreAlias Schemas
class StoreAliasBase(BaseModel):
    alias_name: str
    store_id: Optional[int] = None
    status: Optional[str] = "pending"

class StoreAliasCreate(StoreAliasBase):
    pass

class StoreAliasUpdate(BaseModel):
    store_id: Optional[int] = None
    status: Optional[str] = None

class StoreAlias(StoreAliasBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Store Schemas
class StoreBase(BaseModel):
    name: str
    code: Optional[str] = None
    region: Optional[str] = None
    manager: Optional[str] = None
    phone: Optional[str] = None
    is_active: Optional[bool] = True

class StoreCreate(BaseModel):
    name: str
    code: Optional[str] = None
    region: Optional[str] = None
    manager: Optional[str] = None
    phone: Optional[str] = None
    is_active: Optional[bool] = True

class StoreUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    region: Optional[str] = None
    manager: Optional[str] = None
    phone: Optional[str] = None
    is_active: Optional[bool] = None

class Store(StoreBase):
    id: int
    created_at: datetime
    aliases: List[StoreAlias] = []

    class Config:
        from_attributes = True

# Extended schema to show alias with parent store details
class StoreAliasWithStore(StoreAlias):
    store: Optional[StoreBase] = None
