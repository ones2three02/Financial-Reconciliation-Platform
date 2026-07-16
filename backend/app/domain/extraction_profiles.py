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
    default_columns: tuple[tuple[str, str], ...]
    required_fields: tuple[str, ...]
    extractor: ExtractorName
    date_field: str
    store_field: str | None
    amount_fields: tuple[str, ...]
    output_sources: tuple[str, ...]
    payment_method_field: str | None = None
    requires_store_id: bool = False
    summary_date_markers: tuple[str, ...] = ()

    @property
    def default_bindings(self) -> dict[str, str]:
        bindings: dict[str, str] = {}
        for field, column in self.default_columns:
            bindings.setdefault(field, column)
        return bindings


class UnknownProfileError(ValueError):
    """请求了系统未声明的提取模板。"""


PROFILES: dict[str, ProfileDefinition] = {
    "store_finance_v1": ProfileDefinition(
        code="store_finance_v1",
        version=1,
        input_source="store_finance",
        sheet_names=("收入流水表",),
        header_row=1,
        default_columns=(
            ("trade_date", "日期"),
            ("amount", "金额"),
            ("payment_method", "付款方式"),
        ),
        required_fields=("trade_date", "amount", "payment_method"),
        extractor="sum_filtered_column",
        date_field="trade_date",
        store_field=None,
        amount_fields=("amount",),
        payment_method_field="payment_method",
        output_sources=("sales", "cash"),
        requires_store_id=True,
    ),
    "douyin_v1": ProfileDefinition(
        code="douyin_v1",
        version=1,
        input_source="douyin",
        sheet_names=("核销明细",),
        header_row=1,
        default_columns=(
            ("trade_date", "核销时间"),
            ("store_name", "核销门店"),
            ("amount", "订单实收"),
        ),
        required_fields=("trade_date", "store_name", "amount"),
        extractor="sum_column",
        date_field="trade_date",
        store_field="store_name",
        amount_fields=("amount",),
        output_sources=("douyin",),
    ),
    "meituan_v1": ProfileDefinition(
        code="meituan_v1",
        version=1,
        input_source="meituan",
        sheet_names=("收益明细表",),
        header_row=1,
        default_columns=(
            ("trade_date", "验券/退款/调整时间"),
            ("trade_date", "验券/退款/"),
            ("store_name", "消费门店"),
            ("amount", "总收入（元）"),
            ("marketing_fee", "商家营销费用（元）"),
        ),
        required_fields=("trade_date", "store_name", "amount", "marketing_fee"),
        extractor="sum_columns",
        date_field="trade_date",
        store_field="store_name",
        amount_fields=("amount", "marketing_fee"),
        output_sources=("meituan",),
    ),
    "tonglian_v1": ProfileDefinition(
        code="tonglian_v1",
        version=1,
        input_source="tonglian",
        sheet_names=("sheet1",),
        header_row=2,
        default_columns=(
            ("trade_date", "统计日期"),
            ("store_name", "门店名"),
            ("amount", "成功交易金额"),
        ),
        required_fields=("trade_date", "store_name", "amount"),
        extractor="sum_column",
        date_field="trade_date",
        store_field="store_name",
        amount_fields=("amount",),
        output_sources=("tonglian",),
        summary_date_markers=("汇总",),
    ),
}


def get_profile(profile_code: str) -> ProfileDefinition:
    try:
        return PROFILES[profile_code]
    except KeyError as exc:
        raise UnknownProfileError(f"未知提取模板: {profile_code}") from exc
