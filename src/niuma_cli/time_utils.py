"""时间格式化工具。"""

from __future__ import annotations

import re
from datetime import datetime, time, timedelta


DATE_FORMAT = "%Y-%m-%d"
DATETIME_FORMAT = "%Y-%m-%d %H:%M"
TIME_FORMAT = "%H:%M"


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


def week_range(date_text: str | None = None) -> tuple[str, str]:
    """返回指定日期所在自然周的起止日期。"""

    day = datetime.strptime(validate_date(date_text), DATE_FORMAT)
    start = day - timedelta(days=day.weekday())
    end = start + timedelta(days=6)
    return start.strftime(DATE_FORMAT), end.strftime(DATE_FORMAT)


def month_range(date_text: str | None = None) -> tuple[str, str]:
    """返回指定日期所在月份的起止日期。"""

    day = datetime.strptime(validate_date(date_text), DATE_FORMAT)
    start = day.replace(day=1)
    if start.month == 12:
        next_month = start.replace(year=start.year + 1, month=1)
    else:
        next_month = start.replace(month=start.month + 1)
    end = next_month - timedelta(days=1)
    return start.strftime(DATE_FORMAT), end.strftime(DATE_FORMAT)


def minutes_between(started_at: str, ended_at: str) -> int:
    """计算两个本地时间字符串之间的分钟数，至少返回 1 分钟。"""

    started = datetime.fromisoformat(started_at)
    ended = datetime.fromisoformat(ended_at)
    seconds = max(0, int((ended - started).total_seconds()))
    return max(1, round(seconds / 60))


def parse_local_datetime(value: str) -> datetime:
    """解析用户输入的本地时间，支持 HH:MM 和 YYYY-MM-DD HH:MM。"""

    text = value.strip()
    if not text:
        raise ValueError("时间不能为空")
    for fmt in (DATETIME_FORMAT, TIME_FORMAT):
        try:
            parsed = datetime.strptime(text, fmt)
        except ValueError:
            continue
        if fmt == TIME_FORMAT:
            # 只输入几点时默认补录到今天，符合日常番茄钟补录习惯。
            return datetime.combine(datetime.now().date(), time(parsed.hour, parsed.minute))
        return parsed
    raise ValueError("时间格式必须是 HH:MM 或 YYYY-MM-DD HH:MM")


def parse_duration_minutes(value: str) -> int:
    """解析补录时长，支持 120、120m、2h、2小时、两小时、90分钟。"""

    text = value.strip().lower()
    if not text:
        raise ValueError("时长不能为空")
    text = _replace_chinese_duration_number(text)
    match = re.fullmatch(r"(\d+(?:\.\d+)?)(?:\s*)(h|hour|hours|小时|m|min|minute|minutes|分钟)?", text)
    if match is None:
        raise ValueError("时长格式必须是分钟数、120m、2h、2小时或90分钟")
    amount = float(match.group(1))
    unit = match.group(2) or "m"
    minutes = amount * 60 if unit in {"h", "hour", "hours", "小时"} else amount
    if minutes <= 0:
        raise ValueError("时长必须大于 0")
    return max(1, round(minutes))


def _replace_chinese_duration_number(value: str) -> str:
    """替换时长里的中文数字，避免十二被逐字替换成 102。"""

    match = re.fullmatch(r"([零〇一二两三四五六七八九十百半]+)(小时|分钟)", value)
    if match is None:
        return value
    return f"{_parse_chinese_number(match.group(1))}{match.group(2)}"


def _parse_chinese_number(value: str) -> float:
    """解析常见中文数字，覆盖补录时长所需的一百以内表达。"""

    if value == "半":
        return 0.5
    digits = {
        "零": 0,
        "〇": 0,
        "一": 1,
        "二": 2,
        "两": 2,
        "三": 3,
        "四": 4,
        "五": 5,
        "六": 6,
        "七": 7,
        "八": 8,
        "九": 9,
    }
    total = 0
    current = 0
    for char in value:
        if char in digits:
            current = digits[char]
        elif char == "十":
            total += (current or 1) * 10
            current = 0
        elif char == "百":
            total += (current or 1) * 100
            current = 0
        else:
            raise ValueError("时长格式必须是分钟数、120m、2h、2小时或90分钟")
    return total + current


def datetime_text(value: datetime) -> str:
    """将 datetime 转成 SQLite 统一保存的本地时间字符串。"""

    return value.replace(second=0, microsecond=0).isoformat(sep=" ")
