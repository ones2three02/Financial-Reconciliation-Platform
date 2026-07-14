from sqlalchemy.orm import Session
from backend.app.models.raw_data import RawData
from backend.app.models.clean_data import CleanData
from backend.app.models.store import Store
from backend.app.crud.field_mapping import get_mappings_by_source
import re
from datetime import datetime, date
from decimal import Decimal
import logging
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

def clean_amount(val: Any) -> Decimal:
    """
    Cleans amount strings: removes currency symbols, commas, spaces, etc.
    Converts to Decimal.
    """
    if val is None:
        return Decimal("0.00")
    if isinstance(val, (int, float, Decimal)):
        return Decimal(str(val))
        
    s = str(val).strip()
    # Remove currency signs, commas, and percentage signs
    s = re.sub(r"[¥$,\s]", "", s)
    if not s:
        return Decimal("0.00")
        
    # Handle negative values in accounting formats like (1,234.56)
    if s.startswith("(") and s.endswith(")"):
        s = "-" + s[1:-1]
        
    try:
        return Decimal(s)
    except Exception:
        raise ValueError(f"Invalid amount format: {val}")

def clean_date(val: Any) -> date:
    """
    Parses dates from various string formats or ISO formats.
    """
    if val is None:
        raise ValueError("Date is null")
    if isinstance(val, date):
        return val
    if isinstance(val, datetime):
        return val.date()
        
    s = str(val).strip()
    # If ISO timestamp (e.g. from Pandas Timestamp)
    if "T" in s:
        s = s.split("T")[0]
        
    # Remove time part if any (e.g. "2026-07-13 12:00:00")
    if " " in s:
        s = s.split(" ")[0]
        
    # Try various formats
    formats = [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%Y%m%d",
        "%d/%m/%Y",
        "%m/%d/%Y"
    ]
    for fmt in formats:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
            
    # Handle Excel float serial numbers if loaded as string float
    try:
        f = float(s)
        if 30000 < f < 70000:
            import pandas as pd
            return pd.to_datetime(f, unit='D', origin='1899-12-30').date()
    except Exception:
        pass
        
    raise ValueError(f"Invalid date format: {val}")

def get_or_create_store_alias(db: Session, raw_name: str) -> Tuple[Optional[str], str]:
    """
    Looks up standard store name using raw store alias name.
    If no alias exists, inserts a new one in 'pending' status.
    Returns: (standard_store_name or None, clean_status)
    """
    from backend.app.services.store_resolution import resolve_store

    name_clean = str(raw_name).strip()
    if not name_clean:
        return None, "error"
    resolution = resolve_store(db, "legacy", name_clean)
    if resolution.status != "resolved" or resolution.store_id is None:
        return None, "pending_store_mapping"
    store = db.get(Store, resolution.store_id)
    return (store.name, "cleaned") if store is not None else (None, "error")

from backend.app.models.import_file import ImportFile

def clean_import_file_data(db: Session, import_file_id: int) -> Dict[str, int]:
    """
    Cleans all raw rows for a specific import file.
    Deletes any pre-existing clean_data for this import_file_id first to allow re-runs.
    """
    # 1. Clear existing clean data
    db.query(CleanData).filter(CleanData.import_file_id == import_file_id).delete()
    db.commit()
    
    # Get associated store_id from ImportFile to use as explicit fallback
    import_file = db.query(ImportFile).filter(ImportFile.id == import_file_id).first()
    default_store_name = None
    if import_file and import_file.store_id:
        store = db.query(Store).filter(Store.id == import_file.store_id).first()
        if store:
            default_store_name = store.name
            logger.info(f"Using explicitly specified store '{default_store_name}' for file ID {import_file_id}")
    
    # 2. Get all raw rows
    raw_rows = db.query(RawData).filter(RawData.import_file_id == import_file_id).all()
    
    summary = {
        "total": len(raw_rows),
        "cleaned": 0,
        "pending_store_mapping": 0,
        "error": 0
    }
    
    for row in raw_rows:
        content = row.content or {}
        detected_maps = content.get("_detected_mappings", {})
        
        col_date = detected_maps.get("trade_date")
        col_store = detected_maps.get("store_name")
        col_amount = detected_maps.get("amount")
        
        # --- CASH FILTER RULE ---
        # For cash dataset, only import records where payment method is "现金"
        if row.data_source == "cash":
            pay_method = content.get("付款方式") or content.get("支付方式")
            if not pay_method or str(pay_method).strip() != "现金":
                summary["total"] -= 1  # exclude this row from the dataset statistics
                continue
        
        error_msgs = []
        parsed_date = None
        parsed_amount = Decimal("0.00")
        raw_store_name = ""
        standard_store_name = None
        clean_status = "cleaned"
        
        # Parse Date
        if col_date and col_date in content:
            try:
                parsed_date = clean_date(content[col_date])
            except Exception as e:
                error_msgs.append(f"Date error: {str(e)}")
        else:
            error_msgs.append("Missing date column mapping")
            
        # Parse Store Name
        has_store_value = False
        if col_store and col_store in content:
            val_store = content[col_store]
            if val_store is not None:
                val_str = str(val_store).strip()
                if val_str and val_str.lower() not in ["nan", "none", "null"]:
                    raw_store_name = val_str
                    has_store_value = True
                    
        if has_store_value:
            standard_store_name, store_status = get_or_create_store_alias(db, raw_store_name)
            if store_status == "pending_store_mapping":
                clean_status = "pending_store_mapping"
        else:
            # Fallback to default store name if detected from filename
            if default_store_name:
                raw_store_name = default_store_name
                standard_store_name = default_store_name
            else:
                error_msgs.append("Store name is empty and could not be inferred from filename")
            
        # --- AMOUNT CALCULATION RULE ---
        if row.data_source == "meituan":
            # Meituan calculation logic: 总收入（元） + 商家营销费用（元）
            try:
                col_total_income = "总收入（元）"
                col_marketing = "商家营销费用（元）"
                val_total = content.get(col_total_income) if col_total_income in content else content.get(col_amount)
                val_mkt = content.get(col_marketing, 0)
                parsed_amount = clean_amount(val_total) + clean_amount(val_mkt)
            except Exception as e:
                error_msgs.append(f"Meituan amount parsing error: {str(e)}")
        else:
            # Standard amount parsing
            if col_amount and col_amount in content:
                try:
                    parsed_amount = clean_amount(content[col_amount])
                except Exception as e:
                    error_msgs.append(f"Amount error: {str(e)}")
            else:
                error_msgs.append("Missing amount column mapping")
            
        if error_msgs:
            clean_status = "error"
            
        # Create CleanData record
        db_clean = CleanData(
            raw_data_id=row.id,
            import_file_id=import_file_id,
            trade_date=parsed_date or date(1970, 1, 1),
            original_store_name=raw_store_name or "Unknown",
            standard_store_name=standard_store_name,
            amount=parsed_amount,
            source=row.data_source,
            is_valid=(clean_status != "error"),
            clean_status=clean_status,
            error_message="; ".join(error_msgs) if error_msgs else None
        )
        db.add(db_clean)
        
        # Track counts
        summary[clean_status] += 1
        
    db.commit()
    return summary
