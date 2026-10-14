"""記憶體內的狀態儲存，介面與正式版（資料庫）相同。"""
from __future__ import annotations

from .models import Company, Event
from .util import event_date_tw


class StateStore:
    def __init__(self) -> None:
        self._companies: dict[str, Company] = {}
        self._events: dict[str, list[Event]] = {}

    def add_company(self, c: Company) -> None:
        self._companies[c.code] = c
        self._events.setdefault(c.code, [])

    def company(self, code: str) -> Company:
        return self._companies[code]

    def companies(self) -> list[Company]:
        return list(self._companies.values())

    def add_event(self, e: Event) -> bool:
        """新增事件；同公司同一天（台灣日期）只保留第一筆。回傳是否有新增。"""
        events = self._events.setdefault(e.company, [])
        d = event_date_tw(e.ts)
        if any(event_date_tw(x.ts) == d for x in events):
            return False
        events.append(e)
        events.sort(key=lambda x: x.ts)
        return True

    def events(self, code: str) -> list[Event]:
        return list(self._events.get(code, []))

    def last_event(self, code: str) -> Event | None:
        ev = self._events.get(code) or []
        return max(ev, key=lambda x: event_date_tw(x.ts)) if ev else None
