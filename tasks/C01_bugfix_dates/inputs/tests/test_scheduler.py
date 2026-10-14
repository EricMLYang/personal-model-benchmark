import unittest
from datetime import date

from eventcal.models import Company, Event
from eventcal.scheduler import fiscal_quarter_end, in_window, next_window, plan_all
from eventcal.store import StateStore


def _store():
    s = StateStore()
    s.add_company(Company("2330X", "台岳半導體", "TW"))
    s.add_company(Company("6789X", "北岸電子", "TW"))
    return s


class TestFiscalQuarterEnd(unittest.TestCase):
    def test_calendar(self):
        self.assertEqual(fiscal_quarter_end(date(2026, 2, 10), 1), date(2026, 3, 31))
        self.assertEqual(fiscal_quarter_end(date(2026, 12, 5), 1), date(2026, 12, 31))

    def test_april_start(self):
        self.assertEqual(fiscal_quarter_end(date(2026, 5, 10), 4), date(2026, 6, 30))
        self.assertEqual(fiscal_quarter_end(date(2027, 2, 1), 4), date(2027, 3, 31))


class TestHistory(unittest.TestCase):
    def test_window_from_last_event(self):
        s = _store()
        s.add_event(Event("2330X", "2026-07-16T14:00:00+08:00", "法說會"))
        w = next_window(s, "2330X", date(2026, 8, 1))
        self.assertEqual(w.reason, "history")
        self.assertEqual(w.anchors, ["2026-07-16"])
        self.assertEqual(w.start, date(2026, 10, 1))
        self.assertEqual(w.end, date(2026, 10, 29))
        self.assertEqual(w.quarter, "2026Q4")
        self.assertEqual(w.fiscal, "FY2026Q4")

    def test_missed_window_rolls_forward(self):
        s = _store()
        s.add_event(Event("2330X", "2026-01-15T14:00:00+08:00", "法說會"))
        w = next_window(s, "2330X", date(2026, 6, 1))
        self.assertTrue(in_window(w, date(2026, 7, 16)))

    def test_latest_event_used(self):
        s = _store()
        s.add_event(Event("2330X", "2026-04-16T14:00:00+08:00", "法說會"))
        s.add_event(Event("2330X", "2026-01-15T14:00:00+08:00", "法說會"))
        w = next_window(s, "2330X", date(2026, 5, 1))
        self.assertEqual(w.anchors, ["2026-04-16"])


class TestColdStart(unittest.TestCase):
    def test_tw_calendar_company(self):
        s = _store()
        w = next_window(s, "6789X", date(2026, 8, 20))
        self.assertEqual(w.reason, "cold_start")
        self.assertEqual(w.anchors, ["2026-09-30"])
        self.assertEqual(w.quarter, "2026Q4")
        self.assertEqual(w.fiscal, "FY2026Q4")

    def test_plan_all_sorted(self):
        s = _store()
        s.add_event(Event("2330X", "2026-07-16T14:00:00+08:00", "法說會"))
        ws = plan_all(s, date(2026, 8, 1))
        self.assertEqual([w.start for w in ws], sorted(w.start for w in ws))
        self.assertEqual(len(ws), 2)


if __name__ == "__main__":
    unittest.main()
