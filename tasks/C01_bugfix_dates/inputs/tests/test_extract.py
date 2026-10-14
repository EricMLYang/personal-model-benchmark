import unittest

from eventcal.extract import extract_event, is_earnings_event
from eventcal.models import Announcement


class TestIsEarnings(unittest.TestCase):
    def test_positive(self):
        for t in ["本公司受邀參加法人說明會", "2026 第三季法說會", "Q3 2026 Earnings Call",
                  "Results presentation for FY2026", "2026年度第2四半期 決算説明会", "3분기 실적 발표"]:
            self.assertTrue(is_earnings_event(t), t)

    def test_negative(self):
        for t in ["法說會取消", "法說會延期公告", "更正：法人說明會時間", "Q3 earnings call transcript",
                  "earnings call replay available", "股東會議事錄", "董事會決議配息", ""]:
            self.assertFalse(is_earnings_event(t), t)


class TestExtractEvent(unittest.TestCase):
    def test_time_in_title_wins(self):
        a = Announcement("2330X", "法說會 2026-10-16T14:00+08:00 舉行", "2026-10-01T18:00:00+08:00")
        self.assertEqual(extract_event(a).ts, "2026-10-16T14:00+08:00")

    def test_fallback_published(self):
        a = Announcement("NVCX", "Q3 Earnings Call", "2026-10-20T21:00:00-04:00")
        self.assertEqual(extract_event(a).ts, "2026-10-20T21:00:00-04:00")

    def test_not_event(self):
        self.assertIsNone(extract_event(Announcement("X", "董事會決議", "2026-10-01T00:00:00+08:00")))


if __name__ == "__main__":
    unittest.main()
