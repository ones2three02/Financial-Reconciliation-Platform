import pandas as pd
import json
import logging
from sqlalchemy.orm import Session
from backend.app.models.import_file import ImportFile
from backend.app.models.raw_data import RawData
from backend.app.models.field_mapping import FieldMapping
from backend.app.crud.field_mapping import get_mappings_by_source
from typing import Dict, List, Any, Tuple, Optional
import io

logger = logging.getLogger(__name__)

# --- MONKEYPATCH FOR OPENPYXL FILTER BUG ---
try:
    from openpyxl.worksheet.filters import CustomFilterValueDescriptor
    def patched_set(self, instance, value):
        instance.__dict__[self.name] = value
    CustomFilterValueDescriptor.__set__ = patched_set
    logger.info("Successfully monkeypatched openpyxl CustomFilterValueDescriptor")
except Exception as patch_err:
    logger.warning(f"Could not patch openpyxl filter descriptor: {patch_err}")

# Fallback column search keywords (lowercased)
FALLBACK_KEYWORDS = {
    "trade_date": ["日期", "交易日期", "账期", "交易时间", "时间", "date", "trade_date", "交易账期", "核销时间", "验券/退款/"],
    "store_name": ["商户名称", "门店", "门店名称", "店铺", "店铺名称", "分店", "分店名称", "商户", "终端名称", "店名", "store", "store_name", "消费门店", "门店名", "核销门店"],
    "amount": ["金额", "交易金额", "金额(元)", "销售额", "销售金额", "实收金额", "收入", "应收金额", "实收", "amount", "total_amount", "交易净额", "成功交易金额", "订单实收", "总收入（元）"]
}

def detect_column_mappings(df_cols: List[str], db_mappings: List[FieldMapping], data_source: str) -> Dict[str, str]:
    """
    Detect column names from Excel that map to standard fields.
    Prioritizes DB mappings, falls back to keyword matching.
    """
    mappings = {}
    
    # 1. Apply database mappings first
    db_map_dict = {m.target_field: m.source_column for m in db_mappings if m.is_active}
    
    for standard_field in ["trade_date", "store_name", "amount"]:
        if standard_field in db_map_dict:
            # Check if this exact column exists in the DataFrame
            col_name = db_map_dict[standard_field]
            if col_name in df_cols:
                mappings[standard_field] = col_name
                continue
                
        # 2. Fallback to keyword matching
        keywords = FALLBACK_KEYWORDS.get(standard_field, [])
        for col in df_cols:
            col_clean = str(col).strip().lower()
            if any(kw in col_clean for kw in keywords):
                mappings[standard_field] = col
                break
                
    return mappings

def parse_excel_file(
    db: Session, 
    file_content: bytes, 
    filename: str, 
    data_source: str
) -> Tuple[ImportFile, List[RawData]]:
    """
    Parses Excel and saves rows into import_file and raw_data tables.
    Returns the created ImportFile object and list of RawData.
    """
    # 1. Create ImportFile record
    db_file = ImportFile(
        filename=filename,
        data_source=data_source,
        upload_status="pending"
    )
    db.add(db_file)
    db.commit()
    db.refresh(db_file)
    
    try:
        # 2. Read Excel into Pandas
        xl = pd.ExcelFile(io.BytesIO(file_content))
        sheet_names = xl.sheet_names
        
        # Smart sheet selection
        selected_sheet = sheet_names[0]
        # Prioritize matching typical transaction detail sheets
        target_keywords = ["流水", "明细", "核销"]
        for kw in target_keywords:
            matched = [s for s in sheet_names if kw in s]
            if matched:
                selected_sheet = matched[0]
                break
                
        logger.info(f"Parsing file {filename} sheet '{selected_sheet}' for data source {data_source}")
        df = xl.parse(selected_sheet)
        
        # Clean columns: strip whitespace
        df.columns = [str(c).strip() for c in df.columns]
        df_cols = list(df.columns)
        
        # 3. Retrieve DB field mapping config
        db_mappings = get_mappings_by_source(db, data_source=data_source)
        detected_maps = detect_column_mappings(df_cols, db_mappings, data_source)
        
        # Verify that we can at least map basic fields
        missing_fields = []
        for field in ["trade_date", "store_name", "amount"]:
            if field not in detected_maps:
                missing_fields.append(field)
        
        if missing_fields:
            # If mapping fails, let's still parse, but log columns so user can map them
            logger.warning(f"Could not map standard fields {missing_fields} in file {filename}. Available columns: {df_cols}")
            
        # 4. Insert into raw_data
        raw_rows = []
        for idx, row in df.iterrows():
            # Convert row to dictionary, handle NaN values
            row_dict = {}
            for col in df_cols:
                val = row[col]
                # Check for NaN/Null
                if pd.isna(val):
                    val = None
                else:
                    # Convert to standard serializable types
                    if isinstance(val, (int, float)):
                        pass
                    elif isinstance(val, (pd.Timestamp, datetime)):
                        val = val.isoformat()
                    else:
                        val = str(val)
                row_dict[col] = val
                
            # Add metadata field storing the detected mapping for this import
            # This allows the cleaning engine to know which raw keys correspond to standard fields
            row_dict["_detected_mappings"] = detected_maps
            
            raw_data = RawData(
                import_file_id=db_file.id,
                row_index=int(idx + 1),  # Excel rows are 1-indexed (headers at row 1 usually)
                data_source=data_source,
                content=row_dict
            )
            db.add(raw_data)
            raw_rows.append(raw_data)
            
        db_file.upload_status = "parsed"
        db_file.row_count = len(raw_rows)
        db.commit()
        db.refresh(db_file)
        
        # Auto-create mappings in FieldMapping if we detected mappings that are not in DB yet
        for target, col in detected_maps.items():
            # Check if this mapping is already saved
            exists = db.query(FieldMapping).filter(
                FieldMapping.data_source == data_source,
                FieldMapping.target_field == target,
                FieldMapping.source_column == col
            ).first()
            if not exists:
                new_map = FieldMapping(
                    data_source=data_source,
                    target_field=target,
                    source_column=col,
                    is_active=True
                )
                db.add(new_map)
        db.commit()
        
        return db_file, raw_rows
        
    except Exception as e:
        logger.exception(f"Failed to parse Excel file {filename}")
        db_file.upload_status = "failed"
        db_file.error_message = str(e)
        db.commit()
        raise e
