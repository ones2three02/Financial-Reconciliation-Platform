from datetime import date
from decimal import Decimal

import pytest

from backend.app.crud.reconciliation import get_dashboard_summary, get_dashboard_trends
from backend.app.models.reconciliation import ReconciliationResult


def _result(*, store: str, status: str, expected: str, actual: str, difference: str):
    return ReconciliationResult(
        trade_date=date.today(),
        standard_store_name=store,
        tonglian_amount=Decimal("1.00"),
        meituan_amount=Decimal("2.00"),
        douyin_amount=Decimal("3.00"),
        cash_amount=Decimal("1.00"),
        sales_amount=Decimal("10.00"),
        expected_amount=Decimal(expected),
        actual_amount=Decimal(actual),
        difference=Decimal(difference),
        status=status,
    )


def test_dashboard_uses_new_incomplete_status_and_non_net_difference(db_session):
    db_session.add_all(
        [
            _result(store="一致店", status="consistent", expected="9.00", actual="9.00", difference="0.00"),
            _result(store="缺失店", status="incomplete", expected="6.00", actual="0.00", difference="6.00"),
            _result(store="差异店", status="discrepancy", expected="6.00", actual="8.00", difference="-2.00"),
        ]
    )
    db_session.commit()

    summary = get_dashboard_summary(db_session, date.today())

    assert summary.missing_data_count == 1
    assert summary.total_difference == Decimal("8.00")
    assert summary.total_tonglian == Decimal("21.00")


def test_dashboard_trend_compares_channel_total_with_sales_less_cash(db_session):
    db_session.add(
        _result(store="民院店", status="consistent", expected="9.00", actual="9.00", difference="0.00")
    )
    db_session.commit()

    today = next(row for row in get_dashboard_trends(db_session, days=1) if row["date"] == date.today().isoformat())

    assert today["tonglian_amount"] == 9.0
    assert today["sales_amount"] == 9.0


@pytest.mark.parametrize(
    ("start_date", "end_date", "message"),
    [
        (date(2026, 7, 1), None, "必须同时提供"),
        (None, date(2026, 7, 1), "必须同时提供"),
        (date(2026, 7, 2), date(2026, 7, 1), "不能晚于"),
        (date(2026, 1, 1), date(2026, 7, 1), "不能超过 180 天"),
    ],
)
def test_dashboard_trend_rejects_invalid_explicit_range(
    db_session,
    start_date,
    end_date,
    message,
):
    with pytest.raises(ValueError, match=message):
        get_dashboard_trends(
            db_session,
            start_date=start_date,
            end_date=end_date,
        )


def test_dashboard_trend_handles_date_max_without_overflow(db_session):
    rows = get_dashboard_trends(
        db_session,
        start_date=date.max,
        end_date=date.max,
    )

    assert [row["date"] for row in rows] == [date.max.isoformat()]
