from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from backend.app.core.db import Base

class RawData(Base):
    __tablename__ = "raw_data"

    id = Column(Integer, primary_key=True, index=True)
    import_file_id = Column(Integer, ForeignKey("import_file.id", ondelete="CASCADE"), nullable=False)
    row_index = Column(Integer, nullable=False)
    data_source = Column(String(50), nullable=False, index=True)
    content = Column(JSON, nullable=False)  # Raw key-values from Excel row
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    import_file = relationship("ImportFile", back_populates="raw_rows")
    clean_rows = relationship("CleanData", back_populates="raw_data", cascade="all, delete-orphan")
