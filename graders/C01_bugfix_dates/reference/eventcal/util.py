"""日期、季度、財年期間的共用工具。

規則（見 README）：
- 所有「日期」判斷一律以台灣時間（UTC+8，無日光節約）為準。
- 季度以日曆季度計：1–3 月 Q1、4–6 月 Q2、7–9 月 Q3、10–12 月 Q4。
- 財年以「結束年份」命名。
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

TW = timezone(timedelta(hours=8), name="Asia/Taipei")


def parse_ts(ts: str) -> datetime:
    """解析帶時區的 ISO 時間字串；沒有時區資訊的一律視為台灣時間。"""
    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=TW)
    return dt


def to_taipei(ts: str) -> datetime:
    """轉成台灣時間的 datetime。"""
    return parse_ts(ts).astimezone(TW)


def event_date_tw(ts: str) -> date:
    """事件發生日（台灣日期）。"""
    return to_taipei(ts).date()


def quarter_of(d: date) -> tuple[int, int]:
    """回傳 (年, 季)。"""
    return d.year, (d.month - 1) // 3 + 1


def quarter_label(year: int, q: int) -> str:
    return f"{year}Q{q}"


def prev_quarter(year: int, q: int) -> tuple[int, int]:
    return (year - 1, 4) if q == 1 else (year, q - 1)


def next_quarter(year: int, q: int) -> tuple[int, int]:
    return (year + 1, 1) if q == 4 else (year, q + 1)


def quarter_end(year: int, q: int) -> date:
    month = q * 3
    if month == 12:
        return date(year, 12, 31)
    return date(year, month + 1, 1) - timedelta(days=1)


def fiscal_period(d: date, fy_start_month: int = 1) -> tuple[int, int]:
    """回傳 (財年, 財季)。財年以結束年份命名。

    例：fy_start_month=4 時，2026-04-01 ~ 2027-03-31 為 FY2027；
        fy_start_month=1 時，財年 = 日曆年。
    """
    if not 1 <= fy_start_month <= 12:
        raise ValueError(f"fy_start_month 必須在 1–12：{fy_start_month}")
    offset = (d.month - fy_start_month) % 12
    fq = offset // 3 + 1
    start_year = d.year if d.month >= fy_start_month else d.year - 1
    end_year = start_year + (1 if fy_start_month != 1 else 0)
    return end_year, fq


def fiscal_label(d: date, fy_start_month: int = 1) -> str:
    fy, fq = fiscal_period(d, fy_start_month)
    return f"FY{fy}Q{fq}"


def add_business_days(d: date, n: int) -> date:
    """往後加 n 個工作天（週一至週五，不考慮國定假日）。"""
    step = 1 if n >= 0 else -1
    remaining = abs(n)
    cur = d
    while remaining:
        cur += timedelta(days=step)
        if cur.weekday() < 5:
            remaining -= 1
    return cur


def days_between(a: date, b: date) -> int:
    return (b - a).days
