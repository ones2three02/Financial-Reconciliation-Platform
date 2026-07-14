from datetime import UTC, datetime


def utc_now_naive() -> datetime:
    """兼容旧版无时区数据库列的 UTC 时间。"""
    return datetime.now(UTC).replace(tzinfo=None)
