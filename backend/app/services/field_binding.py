from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence

from backend.app.domain.extraction_profiles import PROFILES, ProfileDefinition


FIELD_BINDINGS_KEY = "_frp_field_bindings"

FIELD_LABELS = {
    "trade_date": "交易日期",
    "store_name": "门店名称",
    "amount": "主金额",
    "marketing_fee": "商家营销费用",
    "payment_method": "付款方式",
}


class FieldBindingError(ValueError):
    """字段映射不能确定地绑定到 Excel 表头。"""


class FieldBindingMissingError(FieldBindingError):
    """必需标准字段没有命中任何已配置列名。"""


class FieldBindingConflictError(FieldBindingError):
    """标准字段命中多个物理列或保留字段发生冲突。"""


def allowed_target_fields(data_source: str) -> tuple[str, ...]:
    for profile in PROFILES.values():
        if profile.input_source == data_source:
            return profile.required_fields
    raise ValueError(f"不支持的数据来源: {data_source}")


def validate_field_mapping_values(
    data_source: str,
    target_field: str,
    source_column: str,
) -> tuple[str, str, str]:
    clean_source = data_source.strip()
    clean_target = target_field.strip()
    clean_column = source_column.strip()
    allowed = allowed_target_fields(clean_source)
    if clean_target not in allowed:
        raise ValueError(
            f"数据来源 {clean_source} 不支持的目标字段: {clean_target}"
        )
    if not clean_column:
        raise ValueError("Excel 原始列标题不能为空")
    if clean_column == FIELD_BINDINGS_KEY:
        raise ValueError(f"Excel 原始列标题不能使用系统保留字段: {FIELD_BINDINGS_KEY}")
    return clean_source, clean_target, clean_column


def _mapping_candidates(
    profile: ProfileDefinition,
    mappings: Sequence[object],
) -> dict[str, list[str]]:
    source_mappings = [
        item
        for item in mappings
        if getattr(item, "data_source", None) == profile.input_source
    ]
    if not source_mappings:
        candidates: dict[str, list[str]] = defaultdict(list)
        for field, column in profile.default_columns:
            if column not in candidates[field]:
                candidates[field].append(column)
        return dict(candidates)

    candidates: dict[str, list[str]] = defaultdict(list)
    for item in source_mappings:
        if not getattr(item, "is_active", False):
            continue
        target = str(getattr(item, "target_field", "")).strip()
        column = str(getattr(item, "source_column", "")).strip()
        if target in profile.required_fields and column and column not in candidates[target]:
            candidates[target].append(column)
    return dict(candidates)


def resolve_field_bindings(
    profile: ProfileDefinition,
    headers: Sequence[str],
    mappings: Sequence[object],
) -> dict[str, str]:
    clean_headers = [str(header).strip() for header in headers]
    if FIELD_BINDINGS_KEY in clean_headers:
        raise FieldBindingConflictError(
            f"Excel 表头包含系统保留字段: {FIELD_BINDINGS_KEY}"
        )
    header_counts = Counter(clean_headers)
    candidates = _mapping_candidates(profile, mappings)
    bindings: dict[str, str] = {}

    for field in profile.required_fields:
        aliases = candidates.get(field, [])
        matches = [alias for alias in aliases if header_counts[alias] > 0]
        duplicate_matches = [alias for alias in matches if header_counts[alias] > 1]
        label = FIELD_LABELS.get(field, field)
        if duplicate_matches:
            raise FieldBindingConflictError(
                f"数据来源 {profile.input_source} 的{label}字段存在重复物理表头: "
                f"{'、'.join(duplicate_matches)}"
            )
        if len(matches) > 1:
            raise FieldBindingConflictError(
                f"数据来源 {profile.input_source} 的{label}字段同时命中多个列: "
                f"{'、'.join(matches)}"
            )
        if not matches:
            allowed = "、".join(aliases) if aliases else "未配置启用列名"
            raise FieldBindingMissingError(
                f"数据来源 {profile.input_source} 缺少{label}字段，允许列名: {allowed}"
            )
        bindings[field] = matches[0]
    return bindings


def bindings_from_raw_content(
    profile: ProfileDefinition,
    content: Mapping[str, object],
) -> dict[str, str]:
    raw_bindings = content.get(FIELD_BINDINGS_KEY)
    if raw_bindings is None:
        return profile.default_bindings
    if not isinstance(raw_bindings, Mapping):
        raise FieldBindingError("原始数据中的字段绑定快照格式无效")
    bindings = {
        str(field): str(column)
        for field, column in raw_bindings.items()
        if isinstance(field, str) and isinstance(column, str)
    }
    if set(bindings) != set(profile.required_fields):
        raise FieldBindingError("原始数据中的字段绑定快照字段不完整")
    if any(not value.strip() for value in bindings.values()):
        raise FieldBindingError("原始数据中的字段绑定快照包含空列名")
    missing_columns = [column for column in bindings.values() if column not in content]
    if missing_columns:
        raise FieldBindingError(
            f"原始数据中的字段绑定列不存在: {'、'.join(missing_columns)}"
        )
    return bindings
