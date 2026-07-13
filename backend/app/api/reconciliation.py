from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
from backend.app.core.db import get_db
from backend.app.schemas.reconciliation import ReconciliationResult, ReconciliationResultUpdate
from backend.app.crud import reconciliation as crud_recon
from backend.app.services.reconciler import run_reconciliation_for_date
import pandas as pd
import io
import urllib.parse

router = APIRouter()

@router.get("/", response_model=List[ReconciliationResult])
def list_reconciliation_results(
    trade_date: Optional[date] = Query(None),
    status: Optional[str] = Query(None),
    is_resolved: Optional[bool] = Query(None),
    skip: int = Query(0),
    limit: int = Query(100),
    db: Session = Depends(get_db)
):
    return crud_recon.list_reconciliation_results(
        db,
        trade_date=trade_date,
        status=status,
        is_resolved=is_resolved,
        skip=skip,
        limit=limit
    )

@router.put("/{result_id}", response_model=ReconciliationResult)
def update_reconciliation_result(
    result_id: int,
    result_in: ReconciliationResultUpdate,
    db: Session = Depends(get_db)
):
    db_result = crud_recon.update_reconciliation_result(db, result_id=result_id, result_in=result_in)
    if not db_result:
        raise HTTPException(status_code=404, detail="Reconciliation result not found")
    return db_result

@router.post("/recalculate")
def recalculate_date(trade_date: date, db: Session = Depends(get_db)):
    """
    Force run the reconciliation engine for a specific date.
    Useful if mapping configurations changed and we want to refresh calculations.
    """
    try:
        results = run_reconciliation_for_date(db, target_date=trade_date)
        return {"status": "success", "count": len(results)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Recalculation failed: {str(e)}")

@router.get("/export")
def export_reconciliation(
    trade_date: date,
    db: Session = Depends(get_db)
):
    """
    Exports reconciliation results for a date to an Excel sheet.
    """
    results = db.query(crud_recon.ReconciliationResult).filter(
        crud_recon.ReconciliationResult.trade_date == trade_date
    ).all()
    
    if not results:
        raise HTTPException(
            status_code=404, 
            detail=f"No reconciliation results found for date {trade_date}"
        )
        
    data = []
    for r in results:
        data.append({
            "对账日期": r.trade_date.isoformat(),
            "标准门店": r.standard_store_name,
            "通联后台金额": float(r.tonglian_amount),
            "美团金额": float(r.meituan_amount),
            "抖音金额": float(r.douyin_amount),
            "现金汇总": float(r.cash_amount),
            "销售汇总": float(r.sales_amount),
            "预计收入 (通联+美团+抖音)": float(r.expected_amount),
            "实际收入 (销售-现金)": float(r.actual_amount),
            "差异金额": float(r.difference),
            "状态": "一致" if r.status == "consistent" else ("未对齐" if r.status == "discrepancy" else "缺少数据"),
            "是否解决": "是" if r.is_resolved else "否",
            "备注": r.remarks or ""
        })
        
    df = pd.DataFrame(data)
    
    # Save to buffer
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='对账结果')
        
    output.seek(0)
    
    filename = f"对账结果_{trade_date.isoformat()}.xlsx"
    # URL encode filename for Content-Disposition header
    encoded_filename = urllib.parse.quote(filename)
    
    headers = {
        'Content-Disposition': f"attachment; filename*=UTF-8''{encoded_filename}"
    }
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers
    )
