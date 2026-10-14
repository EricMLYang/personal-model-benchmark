# 任務：依規範審查 notebook

請依 `CONVENTIONS.md` 的規則（R1–R10）審查 `jobs/daily_sales/notebook.py`，找出所有違規。

- **只審查、不修改**：不得修改 notebook 或規範檔。
- 只回報真正違反規範的地方；符合規範例外條款的寫法不算違規。
- 同一個 cell 違反多條規則時，每條規則各回報一筆。

## 產出：`findings.json`

```json
[
  {
    "cell": 2,
    "tag": "c02",
    "rule": "R6",
    "line": 15,
    "evidence": "違規的原始程式碼片段",
    "fix": "具體的修正方式（一句話或程式碼）"
  }
]
```

- `cell`：cell 在檔案中的順序（以 `# COMMAND ----------` 分隔，第一個 cell 為 1）。
- `tag`：該 cell 的標籤（如 `c02`）；沒有標籤填 `null`。
- `rule`：違反的規則編號（`R1`–`R10`）。
- `line`：違規所在的檔案行號（1 起算）。

另外寫一份 `review.md`，用 5–10 行向 notebook 作者說明最需要優先處理的三件事與理由。
