from dataclasses import dataclass
from typing import Literal


ExtractorName = Literal["sum_column", "sum_filtered_column", "sum_columns"]


@dataclass(frozen=True)
class ProfileDefinition:
    code: str
    version: int
    input_source: str
    sheet_names: tuple[str, ...]
    header_row: int
    required_columns: tuple[str, ...]
    extractor: ExtractorName
    date_column: str
    store_column: str | None
    amount_columns: tuple[str, ...]
    output_sources: tuple[str, ...]
    requires_store_id: bool = False
    summary_date_markers: tuple[str, ...] = ()


class UnknownProfileError(ValueError):
    """请求了系统未声明的提取模板。"""


PROFILES: dict[str, ProfileDefinition] = {
    "store_finance_v1": ProfileDefinition(
        code="store_finance_v1",
        version=1,
        input_source="store_finance",
        sheet_names=("收入流水表",),
        header_row=1,
        required_columns=("日期", "付款方式", "金额"),
        extractor="sum_filtered_column",
        date_column="日期",
        store_column=None,
        amount_columns=("金额",),
        output_sources=("sales", "cash"),
        requires_store_id=True,
    ),
    "douyin_v1": ProfileDefinition(
        code="douyin_v1",
        version=1,
        input_source="douyin",
        sheet_names=("核销明细",),
        header_row=1,
        required_columns=("核销时间", "核销门店", "订单实收"),
        extractor="sum_column",
        date_column="核销时间",
        store_column="核销门店",
        amount_columns=("订单实收",),
        output_sources=("douyin",),
    ),
    "meituan_v1": ProfileDefinition(
        code="meituan_v1",
        version=1,
        input_source="meituan",
        sheet_names=("收益明细表",),
        header_row=1,
        required_columns=(
            "验券/退款/",
            "消费门店",
            "总收入（元）",
            "商家营销费用（元）",
        ),
        extractor="sum_columns",
        date_column="验券/退款/",
        store_column="消费门店",
        amount_columns=("总收入（元）", "商家营销费用（元）"),
        output_sources=("meituan",),
    ),
    "tonglian_v1": ProfileDefinition(
        code="tonglian_v1",
        version=1,
        input_source="tonglian",
        sheet_names=("sheet1",),
        header_row=2,
        required_columns=("统计日期", "门店名", "成功交易金额"),
        extractor="sum_column",
        date_column="统计日期",
        store_column="门店名",
        amount_columns=("成功交易金额",),
        output_sources=("tonglian",),
        summary_date_markers=("汇总",),
    ),
}


def get_profile(profile_code: str) -> ProfileDefinition:
    try:
        return PROFILES[profile_code]
    except KeyError as exc:
        raise UnknownProfileError(f"未知提取模板: {profile_code}") from exc
