# 任務：把凌亂的 Excel 抽成語意摘要

`產能月報.xlsx` 是業務單位每月回報的檔案，版面不規則：一張 sheet 裡有好幾個表、標題用合併儲存格、有公式、有正式的 Excel 表格物件、有圖表。下游的 agent 需要一份**語意摘要**，才知道「哪張圖畫的是哪個表」。

請產出 `workbook_summary.yaml`，格式如下（欄位名稱必須完全一致）：

```yaml
workbook: 產能月報.xlsx
sheets:
  - name: <sheet 名稱>                 # 依 workbook 中的 sheet 順序，全部 sheet 都要列
    blocks:                            # 沒有區塊就寫 []
      - range: B4:H8                   # 區塊範圍，不含 $，大寫
        title: <標題文字或 null>
        kind: formal_table | inferred
        table_name: <正式表格名稱或 null>
        header: [<表頭列各欄文字>]
        has_formulas: true | false
        notes: [<註記文字>]             # 沒有就寫 []
    charts:                            # 沒有圖表就寫 []
      - title: <圖表標題>
        type: bar | line | pie | scatter | area | other
        series:
          - name_ref: 產能概況!B5       # 「sheet!儲存格」，不含 $ 與引號
            values_ref: 產能概況!C5:H5
            categories_ref: 產能概況!C4:H4
        linked_block: <該圖資料所在區塊的 range，或 null>
        confidence: high | low
```

## 定義

- **區塊（block）**：至少 2 列 × 2 欄、由表頭列開始的連續矩形資料範圍；範圍包含表頭列與合計列。只有一欄的文字行（例如說明文字、單獨的大標題）不是區塊。
- **kind**：Excel 正式表格物件（Insert → Table）為 `formal_table`，並填 `table_name`；其他為 `inferred`，`table_name: null`。
- **title**：區塊正上方 1–2 列內、緊鄰區塊左上角的文字（可能是合併儲存格）；沒有就 `null`。Sheet 最上方的大標題不算任何區塊的標題，除非它就緊鄰在區塊正上方。
- **has_formulas**：區塊範圍內是否有任何公式儲存格。
- **notes**：區塊正下方 1–2 列內、以「註」開頭的文字。
- **linked_block**：圖表所有系列的 values 都落在同一個區塊內時，填該區塊 range，`confidence: high`；系列跨到不同區塊或無法判斷時，填 `null`，`confidence: low`。**不要硬猜。**

## 要求

- 原始 Excel 檔不得修改（只讀）。
- 可以寫程式解析（openpyxl、zipfile 讀圖表 XML 等），程式放在本資料夾即可；評分只看 `workbook_summary.yaml`。
