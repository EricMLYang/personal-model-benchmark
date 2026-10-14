# Personal Model Benchmark

用「我自己的工作型態」測新模型。新模型出來時，選好 agent 與模型，三行指令就能拿到可跨模型比較的成績單。

## 新模型出來時怎麼跑

```powershell
$env:PYTHONUTF8=1
python bench.py new --agent codex --model <新模型名稱>     # 建立作答資料夾（預設 ~/bench-runs/）
python bench.py run <上一步印出的資料夾>                   # 無頭模式：逐題呼叫 agent，自動計時
python bench.py grade <資料夾>                             # 評分 → 成績單 + results/leaderboard.md
```

- `--agent`：`claude-code`、`codex`、`gemini`（指令範本在 `agents.yaml`，可自行新增）。
- `--suite quick`（預設，★ 題）或 `full`；`--tasks C01,X03` 只跑指定題。
- **互動模式**（例如 agy 或想看長 session 表現）：`new` 加 `--mode interactive`，在作答資料夾開 agent、選模型，輸入「依 TASKS.md 全部做完」，完成後一樣 `grade`。

## 目前題目

```powershell
python bench.py list
```

| 題號 | 類別 | 測什麼 | 評分 |
|------|------|--------|------|
| ★R06 | 閱讀萃取 | 會議逐字稿 → 決策／行動項／待決（含改口、改派、被推翻的決定） | 埋點比對＋評審 |
| ★X01 | Excel | 凌亂 workbook → 區塊、標題、圖表與資料範圍的對應 | 精確比對 |
| ★X03 | Excel | 4 個 CSV 依規則計算 10 題＋客戶短報告 | 數值比對、報告數字追溯＋評審 |
| ★C01 | 程式 | 依 issue 修時區／財年 bug | 隱藏測試、不退步 |
| ★C03 | 程式 | 新增 `--check` 與休眠警示、自寫測試 | 隱藏測試、golden、變異測試 |
| ★J01 | 審查 | 依規範審查 notebook（10 個違規＋陷阱） | precision／recall＋評審 |

完整規劃（7 類 40 題＋串接題）見 `docs/DESIGN.md`；目前完成第一批 6 題。

## 評分

1. **客觀**（`graders/<題>/check.py`）：埋點、精確比對、隱藏測試、受保護檔案是否被改、是否偷看評分器。
2. **評審**（`judge: true` 的題目）：評審模型尚未決定（`graders/judge.yaml`），目前報表標 `pending`、以客觀分計。
3. **人工**：`report.md` 每題留「我會不會直接用（1–5）」欄。

## 維護

規則見 `AGENTS.md`。所有輸入都是合成資料，人物與公司來自 `world/world.yaml`；新增內容後跑 `python bench.py lint-data` 與 `python bench.py selftest`。
