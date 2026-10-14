# BENCH-GRADER-CANARY-7f3a9c1e
import unittest
from datetime import date

from eventcal import util
from eventcal.models import Company, Event
from eventcal.scheduler import next_window
from eventcal.store import StateStore


class TestTaipeiDate(unittest.TestCase):
    def test_us_evening_next_day(self):
        self.assertEqual(util.event_date_tw("2026-03-31T19:00:00-04:00"), date(2026, 4, 1))

    def test_utc_new_year(self):
        self.assertEqual(util.event_date_tw("2026-12-31T20:00:00Z"), date(2027, 1, 1))

    def test_japan_early_morning_previous_day(self):
        self.assertEqual(util.event_date_tw("2026-04-01T00:30:00+09:00"), date(2026, 3, 31))

    def test_naive_unchanged(self):
        self.assertEqual(util.event_date_tw("2026-04-01T00:30:00"), date(2026, 4, 1))

    def test_taipei_unchanged(self):
        self.assertEqual(util.event_date_tw("2026-06-30T23:59:00+08:00"), date(2026, 6, 30))


class TestDedupeAcrossZones(unittest.TestCase):
    def test_same_tw_day_deduped(self):
        s = StateStore()
        s.add_company(Company("NVCX", "NovaChip", "US"))
        self.assertTrue(s.add_event(Event("NVCX", "2026-04-01T09:00:00+08:00", "Earnings Call")))
        self.assertFalse(s.add_event(Event("NVCX", "2026-03-31T19:00:00-04:00", "Earnings Call")))

    def test_last_event_uses_tw_date(self):
        s = StateStore()
        s.add_company(Company("NVCX", "NovaChip", "US"))
        s.add_event(Event("NVCX", "2026-03-31T23:00:00+08:00", "Earnings Call"))
        s.add_event(Event("NVCX", "2026-03-31T13:30:00-04:00", "Earnings Call (2)"))  # 台灣 4/1 01:30
        self.assertEqual(util.event_date_tw(s.last_event("NVCX").ts), date(2026, 4, 1))


class TestHistoryWindow(unittest.TestCase):
    def test_us_event_window_quarter(self):
        s = StateStore()
        s.add_company(Company("NVCX", "NovaChip", "US"))
        s.add_event(Event("NVCX", "2026-03-31T19:00:00-04:00", "Earnings Call"))
        w = next_window(s, "NVCX", date(2026, 4, 10))
        self.assertEqual(w.anchors, ["2026-04-01"])
        self.assertEqual(w.quarter, "2026Q3")
        self.assertEqual(w.start, date(2026, 6, 17))

    def test_history_fiscal_april(self):
        s = StateStore()
        s.add_company(Company("7203X", "東嶺電機", "JP", 4))
        s.add_event(Event("7203X", "2026-08-05T10:00:00+09:00", "決算説明会"))
        w = next_window(s, "7203X", date(2026, 8, 20))
        self.assertEqual(w.quarter, "2026Q4")
        self.assertEqual(w.fiscal, "FY2027Q3")


class TestFiscal(unittest.TestCase):
    def check(self, d, fy, label):
        self.assertEqual(util.fiscal_label(d, fy), label, (d, fy))

    def test_april_start_boundary(self):
        self.check(date(2026, 4, 1), 4, "FY2027Q1")

    def test_april_before_start(self):
        self.check(date(2026, 3, 31), 4, "FY2026Q4")

    def test_april_december(self):
        self.check(date(2026, 12, 15), 4, "FY2027Q3")

    def test_april_january(self):
        self.check(date(2027, 1, 10), 4, "FY2027Q4")

    def test_july_start(self):
        self.check(date(2026, 7, 1), 7, "FY2027Q1")
        self.check(date(2026, 6, 30), 7, "FY2026Q4")

    def test_october_start(self):
        self.check(date(2026, 10, 1), 10, "FY2027Q1")
        self.check(date(2026, 9, 30), 10, "FY2026Q4")

    def test_calendar_unchanged(self):
        self.check(date(2026, 1, 1), 1, "FY2026Q1")
        self.check(date(2026, 12, 31), 1, "FY2026Q4")

    def test_fiscal_period_tuple(self):
        self.assertEqual(util.fiscal_period(date(2026, 5, 1), 4), (2027, 1))


class TestColdStart(unittest.TestCase):
    def test_japan_april_cold_start(self):
        s = StateStore()
        s.add_company(Company("7203X", "東嶺電機", "JP", 4))
        w = next_window(s, "7203X", date(2026, 5, 10))
        self.assertEqual(w.reason, "cold_start")
        self.assertEqual(w.anchors, ["2026-06-30"])
        self.assertEqual(w.quarter, "2026Q3")
        self.assertEqual(w.fiscal, "FY2027Q2")

    def test_us_calendar_cold_start(self):
        s = StateStore()
        s.add_company(Company("NVCX", "NovaChip", "US"))
        w = next_window(s, "NVCX", date(2026, 11, 3))
        self.assertEqual(w.anchors, ["2026-12-31"])
        self.assertEqual(w.fiscal, "FY2027Q1")


if __name__ == "__main__":
    unittest.main()
