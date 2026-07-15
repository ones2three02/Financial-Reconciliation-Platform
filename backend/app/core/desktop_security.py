import hmac

from backend.app.core.config import Settings


DESKTOP_TOKEN_HEADER = "X-FRP-Desktop-Token"


def desktop_request_is_authorized(
    config: Settings,
    method: str,
    provided_token: str | None,
) -> bool:
    if not config.FRP_DESKTOP or method.upper() == "OPTIONS":
        return True
    expected_token = config.FRP_DESKTOP_TOKEN
    if not expected_token or not provided_token:
        return False
    return hmac.compare_digest(expected_token, provided_token)
