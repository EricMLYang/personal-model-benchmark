# Notebook 開發規範（資料平台組）

適用於所有放在 `jobs/` 底下、跑在 Spark（ANSI mode 開啟）+ Unity Catalog 的 notebook。

| 編號 | 規則 |
|------|------|
| R1 | 每個 cell 的第一行必須是標籤 `# [cNN] 名稱`（NN 為兩位數，可加字母後綴如 `c05a`）。 |
| R2 | 禁止無上限的 `collect()`／`toPandas()`。必須先 `limit(n)`；若確定是已聚合的小表，需在同一行或上一行加註解 `# small: <理由>`。 |
| R3 | 不得使用 `hive_metastore.` 開頭的表名或 `dbfs:/` 路徑；一律使用 Unity Catalog 三段式名稱或 `/Volumes/` 路徑。 |
| R4 | catalog 與 schema 不得寫死，必須來自 `cfg = load_config()`，例如 `f"{cfg.catalog}.{cfg.schema}.s_sales"`。 |
| R5 | 不得在迴圈中反覆呼叫 `withColumn`；多個欄位請一次用 `select` 或 `withColumns`。 |
| R6 | 金鑰、token、密碼不得寫在程式碼中；一律 `dbutils.secrets.get(scope, key)`。 |
| R7 | 由原始字串欄位轉數值或日期時，必須用 `try_cast`（例如 `F.expr("try_cast(revenue AS DOUBLE)")`），不得用 `.cast(...)`，避免 ANSI mode 下整批失敗。 |
| R8 | `MERGE` 之前，來源資料必須依 merge key 去重（`dropDuplicates([...])` 或 window 取最新）。 |
| R9 | 寫入目標表名須符合層級前綴：bronze `b_`、silver `s_`、gold `g_`。本 notebook 的彙總報表屬 gold。 |
| R10 | 轉換邏輯必須是純函式 `def f(df: DataFrame) -> DataFrame`：函式內不得寫入表、不得呼叫 `display()`。 |
