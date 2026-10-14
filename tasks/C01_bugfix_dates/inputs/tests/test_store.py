import unittest

from eventcal.models import Company, Event
from eventcal.store import StateStore


class TestStore(unittest.TestCase):
    def setUp(self):
        self.s = StateStore()
        self.s.add_company(Company("2330X", "台岳半導體", "TW"))

    def test_dedupe_same_day(self):
        self.assertTrue(self.s.add_event(Event("2330X", "2026-07-16T14:00:00+08:00", "法說會")))
        self.assertFalse(self.s.add_event(Event("2330X", "2026-07-16T16:00:00+08:00", "法說會（英文場）")))
        self.assertEqual(len(self.s.events("2330X")), 1)

    def test_different_day_kept(self):
        self.s.add_event(Event("2330X", "2026-07-16T14:00:00+08:00", "法說會"))
        self.s.add_event(Event("2330X", "2026-10-15T14:00:00+08:00", "法說會"))
        self.assertEqual(len(self.s.events("2330X")), 2)

    def test_last_event_none(self):
        self.assertIsNone(self.s.last_event("2330X"))

    def test_unknown_company_events_empty(self):
        self.assertEqual(self.s.events("NOPE"), [])


if __name__ == "__main__":
    unittest.main()
