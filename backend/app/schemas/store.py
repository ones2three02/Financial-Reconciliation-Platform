from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional, List

# StoreAlias Schemas
class StoreAliasBase(BaseModel):
    alias_name: str
    source_code: str = "legacy"
    store_id: Optional[int] = None
    status: Optional[str] = "pending"

class StoreAliasCreate(StoreAliasBase):
    pass

class StoreAliasUpdate(BaseModel):
    store_id: int
    reason: Optional[str] = Field(default=None, max_length=500)


class StoreAliasConfirm(BaseModel):
    store_id: int
    reason: Optional[str] = Field(default=None, max_length=500)

class StoreAlias(StoreAliasBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
    confirmed_by: Optional[str] = None
    confirmed_at: Optional[datetime] = None


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
    status_change_reason: Optional[str] = Field(default=None, max_length=500)

class Store(StoreBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    aliases: List[StoreAlias] = Field(default_factory=list)


# Extended schema to show alias with parent store details
class StoreAliasWithStore(StoreAlias):
    store: Optional[StoreBase] = None
