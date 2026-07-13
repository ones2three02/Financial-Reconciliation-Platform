from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from datetime import date
from typing import List, Optional
from backend.app.core.db import get_db
from backend.app.schemas.reconciliation import DashboardSummary
from backend.app.crud import reconciliation as crud_recon

router = APIRouter()

@router.get("/summary", response_model=DashboardSummary)
def read_dashboard_summary(
    trade_date: Optional[date] = None,
    db: Session = Depends(get_db)
):
    if not trade_date:
        trade_date = date.today()
    return crud_recon.get_dashboard_summary(db, target_date=trade_date)

@router.get("/trends")
def read_dashboard_trends(
    days: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db)
):
    return crud_recon.get_dashboard_trends(db, days=days)
