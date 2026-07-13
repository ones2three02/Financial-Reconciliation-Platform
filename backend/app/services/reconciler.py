from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.app.models.clean_data import CleanData
from backend.app.models.reconciliation import ReconciliationResult
from datetime import date
from decimal import Decimal
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

def run_reconciliation_for_date(db: Session, target_date: date) -> List[ReconciliationResult]:
    """
    Computes reconciliation for all standard stores on a specific date.
    Formula: expected (tonglian + meituan + douyin) == actual (sales - cash)
    Difference = expected - actual
    """
    # 1. Find all standard store names that have cleaned transactions on this date
    stores_query = db.query(CleanData.standard_store_name).filter(
        CleanData.trade_date == target_date,
        CleanData.standard_store_name != None,
        CleanData.is_valid == True
    ).distinct().all()
    
    standard_stores = [s[0] for s in stores_query]
    
    results = []
    
    for store_name in standard_stores:
        # Sum by source for this date and store
        source_sums = db.query(
            CleanData.source,
            func.sum(CleanData.amount).label("total")
        ).filter(
            CleanData.trade_date == target_date,
            CleanData.standard_store_name == store_name,
            CleanData.is_valid == True
        ).group_by(
            CleanData.source
        ).all()
        
        sums = {source: Decimal("0.00") for source in ["tonglian", "meituan", "douyin", "cash", "sales"]}
        for src, total in source_sums:
            if src in sums:
                sums[src] = Decimal(str(total or 0.00))
                
        tonglian = sums["tonglian"]
        meituan = sums["meituan"]
        douyin = sums["douyin"]
        cash = sums["cash"]
        sales = sums["sales"]
        
        expected = tonglian + meituan + douyin
        actual = sales - cash
        difference = expected - actual
        
        # Determine status
        if difference == Decimal("0.00"):
            status = "consistent"
        elif sales == Decimal("0.00") or (tonglian == Decimal("0.00") and meituan == Decimal("0.00") and douyin == Decimal("0.00")):
            # If sales sheet or all 3 payment sheets are missing, it's missing data
            status = "missing_data"
        else:
            status = "discrepancy"
            
        # 2. Check if a reconciliation result already exists
        existing = db.query(ReconciliationResult).filter(
            ReconciliationResult.trade_date == target_date,
            ReconciliationResult.standard_store_name == store_name
        ).first()
        
        if existing:
            # Update fields
            existing.tonglian_amount = tonglian
            existing.meituan_amount = meituan
            existing.douyin_amount = douyin
            existing.cash_amount = cash
            existing.sales_amount = sales
            existing.expected_amount = expected
            existing.actual_amount = actual
            existing.difference = difference
            
            # If status becomes consistent, clear the manual resolution flag
            if status == "consistent":
                existing.status = "consistent"
                existing.is_resolved = False
                existing.remarks = None
                existing.resolved_by = None
                existing.resolved_at = None
            else:
                existing.status = status
                # Keep is_resolved, remarks, resolved_by, etc. if difference is still non-zero
                
            db.commit()
            db.refresh(existing)
            results.append(existing)
        else:
            # Create new record
            new_res = ReconciliationResult(
                trade_date=target_date,
                standard_store_name=store_name,
                tonglian_amount=tonglian,
                meituan_amount=meituan,
                douyin_amount=douyin,
                cash_amount=cash,
                sales_amount=sales,
                expected_amount=expected,
                actual_amount=actual,
                difference=difference,
                status=status
            )
            db.add(new_res)
            db.commit()
            db.refresh(new_res)
            results.append(new_res)
            
    return results

def run_reconciliation_for_import_file(db: Session, import_file_id: int) -> List[ReconciliationResult]:
    """
    Computes reconciliation for all dates found in the clean data of the imported file.
    """
    dates_query = db.query(CleanData.trade_date).filter(
        CleanData.import_file_id == import_file_id
    ).distinct().all()
    
    trade_dates = [d[0] for d in dates_query]
    
    all_results = []
    for t_date in trade_dates:
        res = run_reconciliation_for_date(db, t_date)
        all_results.extend(res)
        
    return all_results
