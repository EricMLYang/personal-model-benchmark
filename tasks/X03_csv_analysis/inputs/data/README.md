# 資料字典（2026-09-01 ~ 2026-09-14，連鎖門市數位看板試播）

| 檔案 | 欄位 |
|------|------|
| `stores.csv` | `store_id`、`store_type`（住宅型／辦公型／交通型／學區型）、`region`（北區／中區／南區）、`status`（open／closed）、`opened` |
| `plays.csv` | `date`、`store_id`、`slot`（早餐／午餐／下午／晚餐／宵夜）、`pack`（受眾包代號）、`impressions`（曝光人次） |
| `sales.csv` | `date`、`store_id`、`slot`、`category`（品類）、`revenue`（營收，新台幣元）、`transactions`（交易筆數） |
| `packs.csv` | `pack`、`name`、`target_category`（受眾包要帶動的品類）、`target_slots`（設計投放時段，`|` 分隔） |

## 計算規則（所有題目一律適用，除非題目另有說明）

1. **已關店門市**（`status = closed`）不納入任何計算。
2. `plays.csv` 有重複上傳的列：**所有欄位完全相同的列只算一次**。
3. `sales.csv` 中 `revenue` 空白代表 POS 回傳失敗：**該列不納入任何營收、交易筆數計算**。
4. **時段對齊率**＝某受眾包在其 `target_slots` 內的曝光數 ÷ 該受眾包總曝光數 × 100。
5. **每千次曝光目標品類營收**＝該受眾包有播放的所有（日期, 門市, 時段）組合中，該包 `target_category` 的營收合計 ÷ 該包總曝光數 × 1000。
6. **客單價**＝營收合計 ÷ 交易筆數合計。
7. 週別：第一週＝09-01～09-07，第二週＝09-08～09-14。
