from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, Integer
from backend.app.models.reconciliation import ReconciliationResult
from backend.app.schemas.reconciliation import ReconciliationResultUpdate, DashboardSummary
from datetime import date, datetime, timedelta
from typing import List, Optional
from decimal import Decimal

def get_reconciliation_result(db: Session, result_id: int) -> Optional[ReconciliationResult]:
    return db.query(ReconciliationResult).filter(ReconciliationResult.id == result_id).first()

def get_reconciliation_result_by_date_and_store(db: Session, trade_date: date, store_name: str) -> Optional[ReconciliationResult]:
    return db.query(ReconciliationResult).filter(
        ReconciliationResult.trade_date == trade_date,
        ReconciliationResult.standard_store_name == store_name
    ).first()

def list_reconciliation_results(
    db: Session,
    trade_date: Optional[date] = None,
    status: Optional[str] = None,
    is_resolved: Optional[bool] = None,
    skip: int = 0,
    limit: int = 100
) -> List[ReconciliationResult]:
    query = db.query(ReconciliationResult)
    if trade_date:
        query = query.filter(ReconciliationResult.trade_date == trade_date)
    if status:
        query = query.filter(ReconciliationResult.status == status)
    if is_resolved is not None:
        query = query.filter(ReconciliationResult.is_resolved == is_resolved)
    
    return query.order_by(ReconciliationResult.trade_date.desc(), ReconciliationResult.difference.desc()).offset(skip).limit(limit).all()

def update_reconciliation_result(
    db: Session,
    result_id: int,
    result_in: ReconciliationResultUpdate
) -> Optional[ReconciliationResult]:
    db_result = get_reconciliation_result(db, result_id)
    if not db_result:
        return None
    for field, value in result_in.model_dump(exclude_unset=True).items():
        setattr(db_result, field, value)
    
    # If resolving, set timestamp
    if result_in.is_resolved is True:
        db_result.resolved_at = datetime.utcnow()
    elif result_in.is_resolved is False:
        db_result.resolved_at = None
        db_result.resolved_by = None

    db.commit()
    db.refresh(db_result)
    return db_result

def get_dashboard_summary(db: Session, target_date: date) -> DashboardSummary:
    results = db.query(ReconciliationResult).filter(ReconciliationResult.trade_date == target_date).all()
    
    total_stores = len(results)
    consistent_count = sum(1 for r in results if r.status == "consistent")
    discrepancy_count = sum(1 for r in results if r.status == "discrepancy")
    missing_data_count = sum(1 for r in results if r.status == "missing_data")
    
    total_sales = sum((r.sales_amount for r in results), Decimal("0.00"))
    total_tonglian = sum((r.tonglian_amount for r in results), Decimal("0.00"))
    total_difference = sum((r.difference for r in results), Decimal("0.00"))
    
    return DashboardSummary(
        total_stores=total_stores,
        consistent_count=consistent_count,
        discrepancy_count=discrepancy_count,
        missing_data_count=missing_data_count,
        total_sales=total_sales,
        total_tonglian=total_tonglian,
        total_difference=total_difference
    )

def get_dashboard_trends(db: Session, days: int = 7) -> List[dict]:
    end_date = date.today()
    start_date = end_date - timedelta(days=days - 1)
    
    # Run a group-by query for dates
    db_trends = db.query(
        ReconciliationResult.trade_date,
        func.sum(ReconciliationResult.sales_amount).label("sales"),
        func.sum(ReconciliationResult.tonglian_amount).label("tonglian"),
        func.sum(func.abs(ReconciliationResult.difference)).label("abs_difference"),
        func.count(ReconciliationResult.id).label("total_stores"),
        func.sum(func.cast(ReconciliationResult.status == "discrepancy", Integer)).label("discrepancies")
    ).filter(
        ReconciliationResult.trade_date.between(start_date, end_date)
    ).group_by(
        ReconciliationResult.trade_date
    ).order_by(
        ReconciliationResult.trade_date.asc()
    ).all()
    
    trends = []
    # Fill in potential missing dates with 0s
    date_map = {t[0]: t for t in db_trends}
    curr = start_date
    while curr <= end_date:
        if curr in date_map:
            t = date_map[curr]
            trends.append({
                "date": curr.isoformat(),
                "sales_amount": float(t.sales or 0),
                "tonglian_amount": float(t.tonglian or 0),
                "difference": float(t.abs_difference or 0),
                "total_stores": int(t.total_stores or 0),
                "discrepancies": int(t.discrepancies or 0)
            })
        else:
            trends.append({
                "date": curr.isoformat(),
                "sales_amount": 0.0,
                "tonglian_amount": 0.0,
                "difference": 0.0,
                "total_stores": 0,
                "discrepancies": 0
            })
        curr += timedelta(days=1)
        
    return trends
