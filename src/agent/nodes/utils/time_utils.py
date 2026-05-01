"""Beijing-time helper for prompt injection."""

from datetime import datetime, timezone, timedelta

_CN_TZ = timezone(timedelta(hours=8))


def get_beijing_time_now() -> str:
    """Return the current Beijing time as a human-readable string.

    Example: "2026-05-01 19:30:45 周五 (UTC+8)"
    """
    now = datetime.now(_CN_TZ)
    weekday_cn = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    wd = weekday_cn[now.weekday()]
    return f"{now.strftime('%Y-%m-%d %H:%M:%S')} {wd} (UTC+8)"
