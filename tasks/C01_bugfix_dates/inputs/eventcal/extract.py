"""從公告標題判斷是不是法說會（earnings conference）公告。規則式，刻意保守。"""
from __future__ import annotations

import re

from .models import Announcement, Event

INCLUDE = [
    r"法人說明會", r"法說會", r"業績發表會", r"財報說明會",
    r"earnings (?:conference )?call", r"earnings webcast", r"results presentation",
    r"決算説明会", r"실적\s*발표",
]
EXCLUDE = [
    r"取消", r"延期", r"更正", r"錄影檔", r"簡報檔(?:上傳|補充)", r"transcript",
    r"replay", r"cancel", r"postpone", r"股東會", r"annual general meeting",
]
_inc = re.compile("|".join(INCLUDE), re.IGNORECASE)
_exc = re.compile("|".join(EXCLUDE), re.IGNORECASE)
_time = re.compile(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2})?(?:[+-]\d{2}:\d{2}|Z)?)")


def is_earnings_event(title: str) -> bool:
    t = title.strip()
    if not t:
        return False
    return bool(_inc.search(t)) and not _exc.search(t)


def extract_event(a: Announcement) -> Event | None:
    """公告若為法說會，取出開會時間（標題中的 ISO 時間優先，否則用公告時間）。"""
    if not is_earnings_event(a.title):
        return None
    m = _time.search(a.title)
    ts = m.group(1) if m else a.published
    return Event(company=a.company, ts=ts, title=a.title)
