"""決定下一次要去找法說會公告的搜尋窗口。

- 有歷史（history）：上一次法說日（台灣日期）+ CYCLE_DAYS 為預期日，前後 WINDOW_DAYS 天。
- 冷啟動（cold_start）：沒有任何歷史 → 以「今天所在財季的季末」+ COLD_START_LAG 天為預期日。
- 窗口的 quarter 欄位是預期日所在的日曆季度；fiscal 欄位是預期日所在財季。
"""
from __future__ import annotations

from datetime import date, timedelta

from .models import SearchWindow
from .store import StateStore
from .util import (event_date_tw, fiscal_label, quarter_label, quarter_of)

CYCLE_DAYS = 91
WINDOW_DAYS = 14
COLD_START_LAG = {"TW": 45, "US": 30, "JP": 45, "KR": 40, "HK": 60, "CN": 30}


def fiscal_quarter_end(d: date, fy_start_month: int) -> date:
    """d 所在財季的最後一天。"""
    offset = (d.month - fy_start_month) % 12
    months_to_end = 2 - offset % 3
    y, m0 = divmod(d.year * 12 + d.month - 1 + months_to_end, 12)
    m = m0 + 1
    nxt = date(y + (m == 12), m % 12 + 1, 1)
    return nxt - timedelta(days=1)


def _window(code: str, expected: date, fy_start: int, reason: str, anchors: list[str]) -> SearchWindow:
    y, q = quarter_of(expected)
    return SearchWindow(
        company=code,
        quarter=quarter_label(y, q),
        fiscal=fiscal_label(expected, fy_start),
        start=expected - timedelta(days=WINDOW_DAYS),
        end=expected + timedelta(days=WINDOW_DAYS),
        reason=reason,
        anchors=anchors,
    )


def next_window(store: StateStore, code: str, today: date) -> SearchWindow:
    c = store.company(code)
    last = store.last_event(code)
    if last is not None:
        last_d = event_date_tw(last.ts)
        expected = last_d + timedelta(days=CYCLE_DAYS)
        while expected + timedelta(days=WINDOW_DAYS) < today:   # 錯過的窗口往後推
            expected += timedelta(days=CYCLE_DAYS)
        return _window(code, expected, c.fy_start_month, "history", [last_d.isoformat()])
    qend = fiscal_quarter_end(today, c.fy_start_month)
    expected = qend + timedelta(days=COLD_START_LAG.get(c.market, 45))
    return _window(code, expected, c.fy_start_month, "cold_start", [qend.isoformat()])


def plan_all(store: StateStore, today: date) -> list[SearchWindow]:
    return sorted((next_window(store, c.code, today) for c in store.companies()),
                  key=lambda w: (w.start, w.company))


def in_window(w: SearchWindow, d: date) -> bool:
    return w.start <= d <= w.end
