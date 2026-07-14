from datetime import date, datetime
from io import BytesIO

import pytest
from openpyxl import Workbook

from backend.app.services.workbook_preflight import (
    PreflightValidationError,
    TemplateMismatchError,
    preflight_workbook,
)


def workbook_bytes(sheet_name: str, headers: list[str], rows: list[list[object]]) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = sheet_name
    sheet.append(headers)
    for row in rows:
        sheet.append(row)
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


def test_finance_profile_requires_exact_sheet_and_store():
    content = workbook_bytes(
        "收入流水表",
        ["日期", "付款方式", "金额"],
        [
            [datetime(2026, 7, 10), "微信", 100],
            [datetime(2026, 7, 11), "现金", 20],
        ],
    )

    result = preflight_workbook(
        content,
        profile_code="store_finance_v1",
        business_date=date(2026, 7, 10),
        store_id=10,
    )

    assert result.sheet_name == "收入流水表"
    assert result.output_sources == ["sales", "cash"]
    assert result.matching_row_count == 1
    assert result.date_range_start == date(2026, 7, 10)
    assert result.date_range_end == date(2026, 7, 11)


def test_finance_profile_rejects_missing_file_store():
    content = workbook_bytes(
        "收入流水表",
        ["日期", "付款方式", "金额"],
        [[datetime(2026, 7, 10), "微信", 100]],
    )

    with pytest.raises(PreflightValidationError, match="标准门店"):
        preflight_workbook(
            content,
            profile_code="store_finance_v1",
            business_date=date(2026, 7, 10),
            store_id=None,
        )


def test_meituan_profile_rejects_missing_marketing_column():
    content = workbook_bytes(
        "收益明细表",
        ["验券/退款/", "消费门店", "总收入（元）"],
        [[datetime(2026, 7, 10), "脱敏门店", 100]],
    )

    with pytest.raises(TemplateMismatchError, match="商家营销费用（元）"):
        preflight_workbook(
            content,
            profile_code="meituan_v1",
            business_date=date(2026, 7, 10),
            store_id=None,
        )


def test_profile_does_not_guess_another_sheet():
    content = workbook_bytes(
        "其他明细",
        ["核销时间", "核销门店", "订单实收"],
        [[datetime(2026, 7, 10), "脱敏门店", 100]],
    )

    with pytest.raises(TemplateMismatchError, match="核销明细"):
        preflight_workbook(
            content,
            profile_code="douyin_v1",
            business_date=date(2026, 7, 10),
            store_id=None,
        )


def test_template_error_does_not_include_data_rows():
    content = workbook_bytes(
        "收益明细表",
        ["验券/退款/", "消费门店", "总收入（元）"],
        [[datetime(2026, 7, 10), "含敏感姓名张三的门店", 100]],
    )

    with pytest.raises(TemplateMismatchError) as exc_info:
        preflight_workbook(
            content,
            profile_code="meituan_v1",
            business_date=date(2026, 7, 10),
            store_id=None,
        )

    assert "张三" not in str(exc_info.value)
