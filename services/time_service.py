"""Parsing and validating dates/times. Time values are minutes, never floats."""
from __future__ import annotations
from datetime import date, datetime

def parse_date(value: str) -> date:
    value = value.strip().replace("-", "/")
    for fmt in ("%Y/%m/%d", "%Y%m%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            pass
    raise ValueError("日付は YYYYMMDD または YYYY/MM/DD で入力してください。")

def parse_time(value: str) -> int:
    try:
        hour, minute = (int(part) for part in value.strip().split(":"))
    except ValueError as error:
        raise ValueError("時刻は HH:MM で入力してください。") from error
    if not 0 <= hour <= 23 or not 0 <= minute <= 59:
        raise ValueError("時刻は 00:00〜23:59 で入力してください。")
    return hour * 60 + minute

def format_minutes(minutes: int) -> str:
    return f"{minutes // 60}時間{minutes % 60:02d}分"

def minimum_break_minutes(work_minutes: int) -> int:
    """Labour Standards Act baseline: >6h 45m, >8h 60m."""
    return 60 if work_minutes > 480 else 45 if work_minutes > 360 else 0
