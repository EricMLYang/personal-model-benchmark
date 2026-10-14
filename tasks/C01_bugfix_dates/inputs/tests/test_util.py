import unittest
from datetime import date

from eventcal import util


class TestParse(unittest.TestCase):
    def test_naive_is_taipei(self):
        self.assertEqual(util.parse_ts("2026-05-01T10:00:00").utcoffset().total_seconds(), 8 * 3600)

    def test_z_suffix(self):
        self.assertEqual(util.parse_ts("2026-05-01T02:00:00Z").hour, 2)

    def test_to_taipei_from_utc(self):
        self.assertEqual(util.to_taipei("2026-05-01T02:00:00Z").hour, 10)

    def test_event_date_tw_taipei_input(self):
        self.assertEqual(util.event_date_tw("2026-05-01T14:30:00+08:00"), date(2026, 5, 1))


class TestQuarter(unittest.TestCase):
    def test_quarter_of(self):
        cases = {date(2026, 1, 1): (2026, 1), date(2026, 3, 31): (2026, 1), date(2026, 4, 1): (2026, 2),
                 date(2026, 9, 30): (2026, 3), date(2026, 12, 31): (2026, 4)}
        for d, exp in cases.items():
            self.assertEqual(util.quarter_of(d), exp, d)

    def test_prev_next_wrap(self):
        self.assertEqual(util.prev_quarter(2026, 1), (2025, 4))
        self.assertEqual(util.next_quarter(2026, 4), (2027, 1))
        self.assertEqual(util.prev_quarter(2026, 3), (2026, 2))

    def test_quarter_end(self):
        self.assertEqual(util.quarter_end(2026, 1), date(2026, 3, 31))
        self.assertEqual(util.quarter_end(2026, 2), date(2026, 6, 30))
        self.assertEqual(util.quarter_end(2026, 4), date(2026, 12, 31))

    def test_label(self):
        self.assertEqual(util.quarter_label(2026, 3), "2026Q3")


class TestFiscal(unittest.TestCase):
    def test_calendar_fiscal_year(self):
        self.assertEqual(util.fiscal_label(date(2026, 1, 15)), "FY2026Q1")
        self.assertEqual(util.fiscal_label(date(2026, 8, 15)), "FY2026Q3")
        self.assertEqual(util.fiscal_label(date(2026, 12, 31), 1), "FY2026Q4")

    def test_invalid_start_month(self):
        with self.assertRaises(ValueError):
            util.fiscal_period(date(2026, 1, 1), 13)


class TestBusinessDays(unittest.TestCase):
    def test_skip_weekend(self):
        self.assertEqual(util.add_business_days(date(2026, 10, 9), 1), date(2026, 10, 12))  # 週五 → 週一

    def test_negative(self):
        self.assertEqual(util.add_business_days(date(2026, 10, 12), -1), date(2026, 10, 9))

    def test_zero(self):
        self.assertEqual(util.add_business_days(date(2026, 10, 10), 0), date(2026, 10, 10))

    def test_days_between(self):
        self.assertEqual(util.days_between(date(2026, 1, 1), date(2026, 3, 1)), 59)


if __name__ == "__main__":
    unittest.main()
