# render_registry

`registry.yaml` 是各 repo 的手填清冊；`render_registry.py` 讀清冊與各 repo 的 git 現況，產生 `projects/_index.md`。

## 執行

```bash
python render_registry.py --registry registry.yaml --projects projects --out projects/_index.md --today 2026-10-14
```

- `--projects`：放各 repo 的資料夾，每個子資料夾含 `.git` 才算 clone 在本機。
- `--today`：固定「今天」，測試用；省略時用系統日期。
- 沉寂天數 = 今天 − 最後一次 commit 的日期（`git log -1 --format=%cs`）。

## tier 規則

| tier | 圖示 | 規則 |
|------|------|------|
| active | 🟢 | 30 天內要有 commit（> 30 天即違規） |
| paused | 🟡 | 必填 `resume_when` |
| dormant | ⚪ | 30 天內不應有 commit（≤ 30 天即違規） |
| archived | 🗄️ | 必填 `ended` 與 `reason` |

- 有 `tier_override` 的 repo 不檢查天數規則（必填欄位仍檢查）。
- 沒 clone 在本機的 repo 不檢查天數規則。

## 輸出：🔎 tier 稽核

- 每個違規一行：``- ❌ `<repo>`：<說明>``，依 registry 順序。
- 沒有任何違規時只輸出一行 `- ✅ 所有 repo 的 tier 與 git 現況一致，必填欄位齊備`。

## 輸出：⚠️ 漂移偵測

- **在本機但未列管**：`--projects` 下有 `.git` 但不在 registry 的資料夾（依名稱排序）。
- **列管但本機沒有**：registry 有、本機沒有的 repo；`archived` 不算（封存的 repo 本來就不需要留在本機）。
- 都沒有時輸出 `- ✅ 無漂移`。

## `--check` 與休眠警示

- `dormant` 沉寂超過 90 天：稽核段加 ``- ⚠️ `<repo>`：dormant 已 N 天，請決定復工或改 archived``（不算違規）。
- `--check`：不寫檔，只印稽核與漂移兩段；有 ❌ 或漂移時結束碼 1，⚠️ 不影響。
