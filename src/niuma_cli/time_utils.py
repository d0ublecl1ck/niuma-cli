"""时间格式化工具。"""

from __future__ import annotations

from datetime import datetime


DATE_FORMAT = "%Y-%m-%d"


def now_text() -> str:
    """返回 SQLite 中统一保存的本地时间字符串。"""

    return datetime.now().replace(microsecond=0).isoformat(sep=" ")


def today_text() -> str:
    """返回当前本地日期。"""

    return datetime.now().strftime(DATE_FORMAT)


def validate_date(value: str | None) -> str:
    """校验日期参数并返回 YYYY-MM-DD 字符串。"""

    if value is None:
        return today_text()
    try:
        return datetime.strptime(value, DATE_FORMAT).strftime(DATE_FORMAT)
    except ValueError as exc:
        raise ValueError("日期格式必须是 YYYY-MM-DD") from exc
