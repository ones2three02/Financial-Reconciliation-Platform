from collections.abc import Mapping

from backend.app.domain.extraction_profiles import ProfileDefinition


def is_summary_row(
    profile: ProfileDefinition,
    content: Mapping[str, object],
) -> bool:
    if not profile.summary_date_markers or profile.store_column is None:
        return False
    raw_date = str(content.get(profile.date_column) or "").strip()
    raw_store = str(content.get(profile.store_column) or "").strip()
    return raw_date in profile.summary_date_markers and not raw_store
