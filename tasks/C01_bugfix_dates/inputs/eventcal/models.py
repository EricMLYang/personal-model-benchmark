from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class Company:
    code: str
    name: str
    market: str            # TW / US / JP / KR / HK / CN
    fy_start_month: int = 1


@dataclass(frozen=True)
class Announcement:
    company: str
    title: str
    published: str         # 帶時區的 ISO 時間字串


@dataclass(frozen=True)
class Event:
    company: str
    ts: str                # 法說會開始時間，帶時區的 ISO 字串
    title: str
    source: str = "announcement"


@dataclass
class SearchWindow:
    company: str
    quarter: str           # 例：2026Q2（日曆季度）
    fiscal: str            # 例：FY2027Q1
    start: date
    end: date
    reason: str            # history / cold_start
    anchors: list[str] = field(default_factory=list)
