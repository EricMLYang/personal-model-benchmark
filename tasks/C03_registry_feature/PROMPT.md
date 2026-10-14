# 任務：render_registry 新增 `--check` 模式與休眠警示，並補測試

本資料夾的 `render_registry.py` 會把 `registry.yaml` 與各 repo 的 git 現況渲染成 `_index.md`（規則見 `README.md`）。請完成下列兩個功能與測試。

## 功能 1：dormant 超過 90 天警示

- `dormant` 且沉寂天數 **大於 90 天**（剛好 90 天不算）的 repo，在「🔎 tier 稽核」段落加一行：
  ``- ⚠️ `<repo>`：dormant 已 <N> 天，請決定復工或改 archived``
  （`<N>` 為沉寂天數；全形冒號「：」與反引號格式要完全一致。）
- 警示不是違規：`tier_override` 的 repo 與未 clone 的 repo 不產生警示。
- 段落內順序：先列全部 ❌（依 registry 順序），再列全部 ⚠️（依 registry 順序）。
- 「✅ 所有 repo 的 tier 與 git 現況一致…」那一行，**只在沒有任何 ❌ 也沒有任何 ⚠️ 時**才輸出。

## 功能 2：`--check` 模式

- 加上 `--check` 參數時：**不寫入** `--out` 檔案（檔案不存在也不建立），改為把「🔎 tier 稽核」與「⚠️ 漂移偵測」兩段的內容行（就是會寫進 `_index.md` 的那些 `- ` 開頭的行）印到標準輸出。
- 結束碼：有任何 ❌ 稽核問題**或**任何漂移時回傳 `1`；否則回傳 `0`。**⚠️ 警示不影響結束碼。**
- 沒加 `--check` 時行為不變（寫檔、結束碼 0）。

## 測試

- 新增 `tests/test_render_registry.py`（pytest），覆蓋上述兩個功能的重點與邊界情況（例如剛好 90 天、91 天、只有警示時的結束碼、`--check` 不寫檔）。
- 測試需能在本資料夾以 `python -m pytest tests -q` 執行並全部通過；測試請自行在暫存資料夾建立假的 git repo（可用 `GIT_AUTHOR_DATE` / `GIT_COMMITTER_DATE` 控制 commit 日期），不要依賴本機其他 repo。

## 其他

- 不要改變既有輸出格式（表格、標題、既有稽核訊息）。
- 只能使用 Python 標準函式庫、PyYAML、pytest。
- 完成後簡短更新 `README.md` 說明新參數與警示規則。
