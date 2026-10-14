import unittest
from datetime import date

from eventcal import util


class TestIssue42(unittest.TestCase):
    def test_us_evening_is_next_day_tw(self):
        self.assertEqual(util.event_date_tw("2026-03-31T19:00:00-04:00"), date(2026, 4, 1))

    def test_fiscal_april(self):
        self.assertEqual(util.fiscal_label(date(2026, 5, 1), 4), "FY2027Q1")
        self.assertEqual(util.fiscal_label(date(2026, 3, 31), 4), "FY2026Q4")


if __name__ == "__main__":
    unittest.main()
