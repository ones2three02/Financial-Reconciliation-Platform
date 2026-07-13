from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from backend.app.core.db import Base

class Store(Base):
    __tablename__ = "store"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    aliases = relationship("StoreAlias", back_populates="store", cascade="all, delete-orphan")

class StoreAlias(Base):
    __tablename__ = "store_alias"

    id = Column(Integer, primary_key=True, index=True)
    alias_name = Column(String(100), unique=True, nullable=False, index=True)
    store_id = Column(Integer, ForeignKey("store.id", ondelete="CASCADE"), nullable=True)
    status = Column(String(20), default="pending")  # "mapped", "pending"
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    store = relationship("Store", back_populates="aliases")
