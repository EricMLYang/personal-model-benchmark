# FIX_SUMMARY

## 根因 1：事件日期沒有轉成台灣時間
`util.event_date_tw()` 直接取原始時區的日期（`parse_ts(ts).date()`），美東 3/31 19:00 被記成 3/31。改為先 `to_taipei()` 再取日期；`store.add_event` 的同日去重與 `scheduler` 的季度判斷都依賴此函式，一併修正。

## 根因 2：財年以起始年份命名
`util.fiscal_period()` 回傳的是財年起始年份；README 規定以結束年份命名，財年非 1 月起時需 +1。

## 新增測試
`tests/test_issue42.py`：跨時區日期、跨年、去重、財年 4/7/10 月起的邊界、冷啟動與歷史窗口的 fiscal 標籤。
