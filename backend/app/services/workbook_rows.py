from collections.abc import Mapping

from backend.app.domain.extraction_profiles import ProfileDefinition
from backend.app.services.field_binding import bindings_from_raw_content


def is_summary_row(
    profile: ProfileDefinition,
    content: Mapping[str, object],
    bindings: Mapping[str, str] | None = None,
) -> bool:
    if not profile.summary_date_markers or profile.store_field is None:
        return False
    resolved = dict(bindings) if bindings is not None else bindings_from_raw_content(profile, content)
    date_value = content.get(resolved[profile.date_field])
    store_value = content.get(resolved[profile.store_field])
    raw_date = "" if date_value is None else str(date_value).strip()
    store_is_blank = store_value is None or (
        isinstance(store_value, str) and not store_value.strip()
    )
    return raw_date in profile.summary_date_markers and store_is_blank
