from collections.abc import Mapping

from backend.app.domain.extraction_profiles import ProfileDefinition


def is_summary_row(
    profile: ProfileDefinition,
    content: Mapping[str, object],
) -> bool:
    if not profile.summary_date_markers or profile.store_column is None:
        return False
    date_value = content.get(profile.date_column)
    store_value = content.get(profile.store_column)
    raw_date = "" if date_value is None else str(date_value).strip()
    store_is_blank = store_value is None or (
        isinstance(store_value, str) and not store_value.strip()
    )
    return raw_date in profile.summary_date_markers and store_is_blank
