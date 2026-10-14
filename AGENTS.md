# AGENTS.md — Personal Model Benchmark（維護用）

本檔是**維護這個 benchmark** 的規則，不是作答規則。作答規則在 `templates/run_AGENTS.md`，由 `bench.py new` 複製到作答資料夾。
設計全貌見 `docs/DESIGN.md`。

## 這個 repo 在做什麼

用「我的工作型態」測新模型：每題是一個能力原子（讀、寫、PM 文件、簡報、Excel、程式、審查），輸入全是合成資料，評分先客觀、後評審。

## 不能破的規則

1. **零真實資料。** 不得從任何工作 repo 複製內容、人名、客戶名、內部代號、數字進來。只抽工作型態，內容一律原創或由 `generators/` 產生。新增檔案後跑 `python bench.py lint-data`（禁用詞表在 `.private/denylist.txt`，不進 git）。
2. **人物、公司、客戶只用 `world/world.yaml`** 的虛構設定。
3. **評分器與參考答案只放 `graders/`**，絕不放進 `tasks/<ID>/inputs/` 或 `PROMPT.md`。
4. **`graders/` 內的評分專用檔要帶 canary**（`BENCH-GRADER-CANARY-7f3a9c1e`），**`graders/<ID>/reference/` 內的檔案不可帶**（參考解答會被複製進作答區做自我驗證）。
5. **每題都要通過 `python bench.py selftest`**：空作答 ≤ 5 分、參考解答 ≥ 95 分。改動任何題目或評分器後重跑。
6. 題目一旦有人跑過成績，就不要改它的輸入或評分邏輯；要改就開新題號（例如 `C01b`），舊成績才可比。

## 新增一題

```text
tasks/<ID>_<slug>/
  task.yaml      # id、title、category（R/W/D/P/X/C/J）、quick、judge、timeout_min、protected（不得修改的輸入檔 glob）
  PROMPT.md      # 給 agent 的題目說明（繁體中文，輸出檔名與格式寫死）
  inputs/        # 凍結輸入，會整包複製進作答區
graders/<ID>_<slug>/
  check.py       # def grade(work, task_dir, grader_dir) -> list[item]
  reference/     # 參考解答（疊加在 inputs 上即為滿分作答）
  hidden_tests/、answer_key.yaml、solution.py …（視需要）
```

- 客觀評分優先：埋點命中、精確比對、隱藏測試、schema。要防「空作答拿分」：退步類、紀律類分數要以「有實質作答」為前提。
- 程式題的隱藏測試用 `_lib.fixed_fraction`：只計「原本失敗、現在通過」的測試，原本通過的當退步守門。
- 需要 LLM 評審的題目在 `task.yaml` 設 `judge: true`，並在 `graders/<ID>/rubric.md` 寫 1／3／5 分錨點；評審模型在 `graders/judge.yaml`（目前未定）。

## 常用指令

```bash
python bench.py doctor | list | selftest | lint-data
python bench.py new --agent codex --model <m> [--suite quick|full] [--mode headless|interactive] [--tasks C01,X03]
python bench.py run <run_dir>      # 無頭模式
python bench.py grade <run_dir>    # 評分 → report.md、scores.json、results/
python bench.py board              # results/leaderboard.md
```

Windows 上執行前建議 `set PYTHONUTF8=1`（PowerShell：`$env:PYTHONUTF8=1`）。
