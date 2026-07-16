from types import SimpleNamespace

import pytest

from backend.app.domain.extraction_profiles import get_profile
from backend.app.services.field_binding import (
    FIELD_BINDINGS_KEY,
    FieldBindingError,
    FieldBindingConflictError,
    FieldBindingMissingError,
    bindings_from_raw_content,
    resolve_field_bindings,
)


def mapping(source: str, target: str, column: str, *, active: bool = True):
    return SimpleNamespace(
        data_source=source,
        target_field=target,
        source_column=column,
        is_active=active,
    )


def test_profile_defaults_bind_all_tonglian_fields():
    profile = get_profile("tonglian_v1")

    assert resolve_field_bindings(
        profile,
        ["统计日期", "门店名", "成功交易金额"],
        [],
    ) == {
        "trade_date": "统计日期",
        "store_name": "门店名",
        "amount": "成功交易金额",
    }


def test_tonglian_custom_store_alias_replaces_default():
    profile = get_profile("tonglian_v1")
    mappings = [
        mapping("tonglian", "trade_date", "统计日期"),
        mapping("tonglian", "store_name", "门店名称"),
        mapping("tonglian", "amount", "成功交易金额"),
    ]

    assert resolve_field_bindings(
        profile,
        ["统计日期", "门店名称", "成功交易金额"],
        mappings,
    )["store_name"] == "门店名称"


def test_source_configuration_does_not_fall_back_to_profile_defaults():
    profile = get_profile("tonglian_v1")
    mappings = [
        mapping("tonglian", "trade_date", "交易日"),
        mapping("tonglian", "store_name", "门店名称"),
        mapping("tonglian", "amount", "交易金额"),
    ]

    with pytest.raises(FieldBindingMissingError, match="交易日期"):
        resolve_field_bindings(
            profile,
            ["统计日期", "门店名称", "交易金额"],
            mappings,
        )


def test_disabled_alias_does_not_match():
    profile = get_profile("tonglian_v1")
    mappings = [
        mapping("tonglian", "trade_date", "统计日期"),
        mapping("tonglian", "store_name", "门店名", active=False),
        mapping("tonglian", "store_name", "门店名称"),
        mapping("tonglian", "amount", "成功交易金额"),
    ]

    with pytest.raises(FieldBindingMissingError, match="门店名称"):
        resolve_field_bindings(
            profile,
            ["统计日期", "门店名", "成功交易金额"],
            mappings,
        )


def test_two_store_aliases_in_same_file_are_rejected():
    profile = get_profile("tonglian_v1")
    mappings = [
        mapping("tonglian", "trade_date", "统计日期"),
        mapping("tonglian", "store_name", "门店名"),
        mapping("tonglian", "store_name", "门店名称"),
        mapping("tonglian", "amount", "成功交易金额"),
    ]

    with pytest.raises(FieldBindingConflictError, match="门店名.*门店名称"):
        resolve_field_bindings(
            profile,
            ["统计日期", "门店名", "门店名称", "成功交易金额"],
            mappings,
        )


def test_duplicate_physical_header_is_rejected():
    profile = get_profile("tonglian_v1")

    with pytest.raises(FieldBindingConflictError, match="重复"):
        resolve_field_bindings(
            profile,
            ["统计日期", "门店名", "门店名", "成功交易金额"],
            [],
        )


@pytest.mark.parametrize("date_column", ["验券/退款/调整时间", "验券/退款/"])
def test_meituan_date_aliases_are_explicitly_supported(date_column):
    profile = get_profile("meituan_v1")
    mappings = [
        mapping("meituan", "trade_date", "验券/退款/调整时间"),
        mapping("meituan", "trade_date", "验券/退款/"),
        mapping("meituan", "store_name", "消费门店"),
        mapping("meituan", "amount", "总收入（元）"),
        mapping("meituan", "marketing_fee", "商家营销费用（元）"),
    ]

    result = resolve_field_bindings(
        profile,
        [date_column, "消费门店", "总收入（元）", "商家营销费用（元）"],
        mappings,
    )

    assert result["trade_date"] == date_column


def test_reserved_binding_header_is_rejected():
    profile = get_profile("douyin_v1")

    with pytest.raises(FieldBindingConflictError, match="保留字段"):
        resolve_field_bindings(
            profile,
            ["核销时间", "核销门店", "订单实收", FIELD_BINDINGS_KEY],
            [],
        )


def test_raw_snapshot_is_used_and_legacy_rows_use_defaults():
    profile = get_profile("tonglian_v1")
    snapshot = {
        "trade_date": "交易日",
        "store_name": "门店名称",
        "amount": "交易金额",
    }

    assert bindings_from_raw_content(
        profile,
        {
            "交易日": "2026-07-10",
            "门店名称": "民院店",
            "交易金额": 100,
            FIELD_BINDINGS_KEY: snapshot,
        },
    ) == snapshot
    assert bindings_from_raw_content(profile, {}) == {
        "trade_date": "统计日期",
        "store_name": "门店名",
        "amount": "成功交易金额",
    }


def test_raw_snapshot_rejects_binding_to_missing_physical_column():
    profile = get_profile("tonglian_v1")

    with pytest.raises(FieldBindingError, match="绑定列不存在"):
        bindings_from_raw_content(
            profile,
            {
                "统计日期": "2026-07-10",
                "门店名称": "民院店",
                "成功交易金额": 100,
                FIELD_BINDINGS_KEY: {
                    "trade_date": "统计日期",
                    "store_name": "不存在的门店列",
                    "amount": "成功交易金额",
                },
            },
        )
