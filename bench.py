#!/usr/bin/env python3
"""Personal Model Benchmark CLI.

  python bench.py doctor
  python bench.py list
  python bench.py new   --agent codex --model gpt-x --suite quick [--mode headless|interactive] [--tasks C01,X03]
  python bench.py run   <run_dir> [--tasks C01,X03]          # headless：逐題呼叫 agents.yaml 中的指令
  python bench.py grade <run_dir>
  python bench.py board
  python bench.py selftest [--tasks C01]                     # 驗證評分器：空作答 ≤ 5、參考解答 ≥ 95
  python bench.py lint-data                                  # 用 .private/denylist.txt 掃描誤入的真實資料

作答資料夾預設建在 repo 之外（~/bench-runs，可用環境變數 BENCH_RUNS_DIR 覆寫），
避免 agent 讀到本 repo 的 AGENTS.md / CLAUDE.md 或 graders/。
"""
from __future__ import annotations

import argparse
import datetime as dt
import fnmatch
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
TASKS_DIR = ROOT / "tasks"
GRADERS_DIR = ROOT / "graders"
TEMPLATES_DIR = ROOT / "templates"
RESULTS_DIR = ROOT / "results"
CATEGORY_WEIGHTS = {"R": 20, "W": 20, "D": 15, "P": 10, "X": 10, "C": 15, "J": 10}
CATEGORY_NAMES = {"R": "閱讀萃取", "W": "寫作改稿", "D": "PM文件", "P": "簡報",
                  "X": "Excel數據", "C": "程式", "J": "審查判斷"}
CANARY = "BENCH-GRADER-CANARY-7f3a9c1e"  # 只出現在 graders/；作答中出現即判定偷看
INTEGRITY_PENALTY = 0.5
JUDGE_MIN_OBJECTIVE = 40


# ---------------------------------------------------------------- helpers
def runs_root() -> Path:
    return Path(os.environ.get("BENCH_RUNS_DIR", Path.home() / "bench-runs"))


def load_tasks() -> dict[str, dict]:
    tasks = {}
    for d in sorted(TASKS_DIR.iterdir()):
        f = d / "task.yaml"
        if not f.exists():
            continue
        meta = yaml.safe_load(f.read_text(encoding="utf-8"))
        meta["dir"] = d
        meta["grader_dir"] = GRADERS_DIR / d.name
        tasks[meta["id"]] = meta
    return tasks


def select_tasks(tasks: dict, suite: str | None, only: str | None) -> list[dict]:
    if only:
        ids = [x.strip() for x in only.split(",") if x.strip()]
        missing = [i for i in ids if i not in tasks]
        if missing:
            sys.exit(f"未知任務：{missing}")
        return [tasks[i] for i in ids]
    if suite == "quick":
        return [t for t in tasks.values() if t.get("quick")]
    return list(tasks.values())


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def snapshot(d: Path) -> dict[str, str]:
    return {p.relative_to(d).as_posix(): sha256(p) for p in sorted(d.rglob("*")) if p.is_file()}


def slug(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", s).strip("-")


def task_dirname(t: dict) -> str:
    return t["dir"].name


def load_grader(t: dict):
    path = t["grader_dir"] / "check.py"
    spec = importlib.util.spec_from_file_location(f"grader_{t['id']}", path)
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(GRADERS_DIR))
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.path.pop(0)
    return mod


def render_template(name: str, **kw) -> str:
    text = (TEMPLATES_DIR / name).read_text(encoding="utf-8")
    for k, v in kw.items():
        text = text.replace("{{" + k + "}}", str(v))
    return text


# ---------------------------------------------------------------- doctor / list
def cmd_doctor(_args):
    print(f"Python  {sys.version.split()[0]}")
    for mod in ("yaml", "openpyxl", "pptx", "pandas", "pytest"):
        try:
            m = __import__(mod)
            print(f"  ✓ {mod} {getattr(m, '__version__', '')}")
        except ImportError:
            print(f"  ✗ {mod} 未安裝")
    for exe in ("node", "git", "claude", "codex", "gemini", "agy"):
        print(f"  {'✓' if shutil.which(exe) else '✗'} {exe}")
    print(f"作答資料夾根目錄：{runs_root()}")
    judge = yaml.safe_load((GRADERS_DIR / "judge.yaml").read_text(encoding="utf-8")) or {}
    print(f"評審：{judge.get('command') or '未設定（只出客觀分）'}")


def cmd_list(_args):
    for t in load_tasks().values():
        star = "★" if t.get("quick") else " "
        judge = "＋評審" if t.get("judge") else ""
        print(f"{star} {t['id']:4} [{CATEGORY_NAMES[t['category']]}] {t['title']} {judge}")


# ---------------------------------------------------------------- new
def cmd_new(args):
    tasks = select_tasks(load_tasks(), args.suite, args.tasks)
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M")
    run_id = f"{stamp}_{slug(args.agent)}_{slug(args.model)}"
    run_dir = runs_root() / run_id
    if run_dir.exists():
        sys.exit(f"已存在：{run_dir}")
    run_dir.mkdir(parents=True)
    rules = render_template("run_AGENTS.md")
    (run_dir / "AGENTS.md").write_text(rules, encoding="utf-8")
    (run_dir / "CLAUDE.md").write_text("@AGENTS.md\n", encoding="utf-8")
    (run_dir / "GEMINI.md").write_text("請先閱讀並遵守 AGENTS.md。\n", encoding="utf-8")
    lines = ["# 任務清單", "", "依序完成下列任務。每題的說明在該資料夾的 `PROMPT.md`。", ""]
    manifest = {}
    for t in tasks:
        dst = run_dir / task_dirname(t)
        shutil.copytree(t["dir"] / "inputs", dst) if (t["dir"] / "inputs").exists() else dst.mkdir()
        shutil.copy2(t["dir"] / "PROMPT.md", dst / "PROMPT.md")
        manifest[t["id"]] = snapshot(dst)
        lines.append(f"- [ ] `{task_dirname(t)}/` — {t['title']}")
    (run_dir / "TASKS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    meta = {"run_id": run_id, "agent": args.agent, "model": args.model, "suite": args.suite,
            "mode": args.mode, "created": dt.datetime.now().isoformat(timespec="seconds"),
            "tasks": [t["id"] for t in tasks], "timings": {}, "usage": {}}
    (run_dir / ".bench").mkdir()
    (run_dir / ".bench" / "run.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    (run_dir / ".bench" / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"建立作答資料夾：{run_dir}")
    if args.mode == "headless":
        print(f"下一步：python bench.py run \"{run_dir}\"")
    else:
        print(f"下一步：在該資料夾開啟 coding agent，選模型 {args.model}，輸入「依 TASKS.md 全部做完」，")
        print(f"        完成後執行 python bench.py grade \"{run_dir}\"")


# ---------------------------------------------------------------- run (headless)
def cmd_run(args):
    run_dir = Path(args.run_dir).resolve()
    meta_path = run_dir / ".bench" / "run.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    agents = yaml.safe_load((ROOT / "agents.yaml").read_text(encoding="utf-8"))
    if meta["agent"] not in agents:
        sys.exit(f"agents.yaml 沒有 {meta['agent']} 的設定")
    conf = agents[meta["agent"]]
    tasks = load_tasks()
    ids = args.tasks.split(",") if args.tasks else meta["tasks"]
    rules = (run_dir / "AGENTS.md").read_text(encoding="utf-8")
    for tid in ids:
        t = tasks[tid]
        work = run_dir / task_dirname(t)
        prompt = (f"{rules}\n\n---\n\n你現在的工作目錄就是本題資料夾。"
                  f"請閱讀 PROMPT.md 並完成任務，所有產出寫在本資料夾內。\n\n"
                  + (work / "PROMPT.md").read_text(encoding="utf-8"))
        cmd = [c.replace("{model}", meta["model"]) for c in conf["command"]]
        log_dir = run_dir / ".bench" / "logs"
        log_dir.mkdir(exist_ok=True)
        print(f"▶ {tid} {t['title']} …", flush=True)
        t0 = time.time()
        timeout = int(t.get("timeout_min", 30)) * 60
        stdin_prompt = conf.get("prompt_via", "stdin") == "stdin"
        if not stdin_prompt:
            cmd = cmd + [prompt]
        try:
            p = subprocess.run(cmd, cwd=work, input=prompt if stdin_prompt else None,
                               capture_output=True, text=True, encoding="utf-8",
                               errors="replace", timeout=timeout, shell=(os.name == "nt"))
            out, err, rc = p.stdout, p.stderr, p.returncode
        except subprocess.TimeoutExpired as e:
            out, err, rc = (e.stdout or ""), f"TIMEOUT after {timeout}s", -1
            if isinstance(out, bytes):
                out = out.decode("utf-8", "replace")
        elapsed = round(time.time() - t0, 1)
        (log_dir / f"{tid}.stdout.txt").write_text(out or "", encoding="utf-8")
        (log_dir / f"{tid}.stderr.txt").write_text(err or "", encoding="utf-8")
        meta["timings"][tid] = elapsed
        meta["usage"][tid] = extract_usage(out or "")
        meta.setdefault("exit_codes", {})[tid] = rc
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  完成：{elapsed}s，exit {rc}")
    print(f"全部完成。下一步：python bench.py grade \"{run_dir}\"")


def extract_usage(stdout: str) -> dict:
    """盡力從各 CLI 的 JSON 輸出抓 token / 費用；抓不到就回空 dict。"""
    usage = {}
    for line in stdout.splitlines()[::-1]:
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if "total_cost_usd" in obj:
            usage["cost_usd"] = obj["total_cost_usd"]
        u = obj.get("usage") or obj.get("stats") or {}
        if isinstance(u, dict):
            for k in ("input_tokens", "output_tokens", "cached_input_tokens"):
                if k in u:
                    usage[k] = u[k]
        if usage:
            break
    return usage


# ---------------------------------------------------------------- grade
def integrity_check(t: dict, work: Path, original: dict[str, str]) -> list[str]:
    violations = []
    for pattern in t.get("protected", []):
        for rel, h in original.items():
            if fnmatch.fnmatch(rel, pattern):
                p = work / rel
                if not p.exists():
                    violations.append(f"刪除了受保護檔案 {rel}")
                elif sha256(p) != h:
                    violations.append(f"修改了受保護檔案 {rel}")
    return violations


def canary_hit(work: Path) -> bool:
    for p in work.rglob("*"):
        if p.is_file() and p.stat().st_size < 5_000_000:
            try:
                if CANARY in p.read_text(encoding="utf-8", errors="ignore"):
                    return True
            except OSError:
                pass
    return False


def grade_task(t: dict, work: Path, original: dict[str, str] | None) -> dict:
    mod = load_grader(t)
    try:
        items = mod.grade(work, t["dir"], t["grader_dir"])
    except Exception as e:  # 評分器例外不應讓整個 run 失敗
        items = [{"name": "grader_error", "weight": 1, "score": 0, "detail": repr(e)}]
    total_w = sum(i["weight"] for i in items) or 1
    objective = round(100 * sum(i["weight"] * i["score"] for i in items) / total_w, 1)
    flags = []
    if original is not None:
        flags += integrity_check(t, work, original)
    if canary_hit(work):
        flags.append("作答中出現評分器 canary（疑似讀取 graders/）")
        objective = 0.0
    if flags and objective:
        objective = round(objective * INTEGRITY_PENALTY, 1)
    return {"id": t["id"], "title": t["title"], "category": t["category"], "objective": objective,
            "judge": "pending" if t.get("judge") else None, "flags": flags, "items": items}


def final_score(r: dict) -> float:
    if isinstance(r.get("judge"), (int, float)):
        return round(0.7 * r["objective"] + 0.3 * r["judge"], 1)
    return r["objective"]


def summarize(results: list[dict]) -> dict:
    by_cat: dict[str, list[float]] = {}
    for r in results:
        by_cat.setdefault(r["category"], []).append(final_score(r))
    cats = {c: round(sum(v) / len(v), 1) for c, v in by_cat.items()}
    w = sum(CATEGORY_WEIGHTS[c] for c in cats) or 1
    total = round(sum(CATEGORY_WEIGHTS[c] * s for c, s in cats.items()) / w, 1)
    return {"total": total, "categories": cats}


def cmd_grade(args):
    run_dir = Path(args.run_dir).resolve()
    meta = json.loads((run_dir / ".bench" / "run.json").read_text(encoding="utf-8"))
    manifest = json.loads((run_dir / ".bench" / "manifest.json").read_text(encoding="utf-8"))
    tasks = load_tasks()
    results = []
    for tid in meta["tasks"]:
        t = tasks[tid]
        print(f"評分 {tid} …", flush=True)
        results.append(grade_task(t, run_dir / task_dirname(t), manifest.get(tid)))
    summary = summarize(results)
    scores = {"run": {k: meta[k] for k in ("run_id", "agent", "model", "suite", "mode", "created")},
              "graded": dt.datetime.now().isoformat(timespec="seconds"),
              "timings": meta.get("timings", {}), "usage": meta.get("usage", {}),
              "summary": summary, "results": results}
    (run_dir / "scores.json").write_text(json.dumps(scores, ensure_ascii=False, indent=2), encoding="utf-8")
    report = render_report(scores)
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (RESULTS_DIR / "runs").mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / "runs" / f"{meta['run_id']}.json").write_text(
        json.dumps(scores, ensure_ascii=False, indent=2), encoding="utf-8")
    print(report)
    cmd_board(None)


def render_report(s: dict) -> str:
    r = s["run"]
    out = [f"# 成績單 {r['run_id']}", "",
           f"- agent：{r['agent']}｜model：{r['model']}｜suite：{r['suite']}｜mode：{r['mode']}",
           f"- 總分（加權）：**{s['summary']['total']}**", "",
           "| 類別 | 分數 |", "|---|---|"]
    for c, v in s["summary"]["categories"].items():
        out.append(f"| {CATEGORY_NAMES[c]} | {v} |")
    out += ["", "| 題目 | 客觀 | 評審 | 最終 | 耗時(s) | 旗標 |", "|---|---|---|---|---|---|"]
    for x in s["results"]:
        judge = x["judge"] if x["judge"] is not None else "—"
        out.append(f"| {x['id']} {x['title']} | {x['objective']} | {judge} | {final_score(x)} | "
                   f"{s['timings'].get(x['id'], '')} | {'；'.join(x['flags'])} |")
    out += ["", "## 細項", ""]
    for x in s["results"]:
        out.append(f"### {x['id']} {x['title']}")
        for i in x["items"]:
            out.append(f"- {i['name']}（權重 {i['weight']}）：{round(i['score'] * 100)}% — {i.get('detail', '')}")
        out.append("- 人工評分（我會不會直接用 1–5）：")
        out.append("")
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------- board
def cmd_board(_args):
    rows = []
    for f in sorted((RESULTS_DIR / "runs").glob("*.json")) if (RESULTS_DIR / "runs").exists() else []:
        s = json.loads(f.read_text(encoding="utf-8"))
        rows.append(s)
    head = "| run | agent | model | suite | mode | 總分 | " + " | ".join(CATEGORY_NAMES.values()) + " | 耗時(min) | 費用(USD) |"
    sep = "|" + "---|" * (8 + len(CATEGORY_NAMES))
    lines = ["# Leaderboard", "", "> 由 `python bench.py board` 產生；評審未跑的題目以客觀分計。", "", head, sep]
    for s in sorted(rows, key=lambda x: x["run"]["created"], reverse=True):
        r = s["run"]
        cats = [str(s["summary"]["categories"].get(c, "—")) for c in CATEGORY_NAMES]
        minutes = round(sum(s.get("timings", {}).values()) / 60, 1) if s.get("timings") else "—"
        cost = sum(u.get("cost_usd", 0) for u in s.get("usage", {}).values()) or "—"
        lines.append(f"| {r['run_id']} | {r['agent']} | {r['model']} | {r['suite']} | {r['mode']} | "
                     f"**{s['summary']['total']}** | " + " | ".join(cats) + f" | {minutes} | {cost} |")
    RESULTS_DIR.mkdir(exist_ok=True)
    (RESULTS_DIR / "leaderboard.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"已更新 {RESULTS_DIR / 'leaderboard.md'}")


# ---------------------------------------------------------------- selftest
def cmd_selftest(args):
    tasks = select_tasks(load_tasks(), None, args.tasks)
    ok = True
    for t in tasks:
        with tempfile.TemporaryDirectory() as tmp:
            blank = Path(tmp) / "blank"
            ref = Path(tmp) / "ref"
            for d in (blank, ref):
                if (t["dir"] / "inputs").exists():
                    shutil.copytree(t["dir"] / "inputs", d)
                else:
                    d.mkdir()
            original = snapshot(blank)
            refsrc = t["grader_dir"] / "reference"
            shutil.copytree(refsrc, ref, dirs_exist_ok=True)
            rb = grade_task(t, blank, original)
            rr = grade_task(t, ref, original)
        good = rb["objective"] <= 5 and rr["objective"] >= 95 and not rr["flags"]
        ok &= good
        print(f"{'✓' if good else '✗'} {t['id']}  空作答 {rb['objective']:5}  參考解答 {rr['objective']:5}")
        if not good:
            for i in rr["items"]:
                if i["score"] < 1:
                    print(f"     ref  {i['name']}: {i['score']:.2f} {i.get('detail', '')}")
            for i in rb["items"]:
                if i["score"] > 0:
                    print(f"     blank {i['name']}: {i['score']:.2f} {i.get('detail', '')}")
            print(f"     flags: {rr['flags']}")
    sys.exit(0 if ok else 1)


# ---------------------------------------------------------------- lint-data
def cmd_lint_data(_args):
    deny = ROOT / ".private" / "denylist.txt"
    if not deny.exists():
        sys.exit("找不到 .private/denylist.txt（每行一個禁用詞，此檔不進 git）")
    terms = [t.strip() for t in deny.read_text(encoding="utf-8").splitlines()
             if t.strip() and not t.startswith("#")]
    tracked = subprocess.run(["git", "ls-files", "-co", "--exclude-standard"], cwd=ROOT,
                             capture_output=True, text=True, encoding="utf-8").stdout.split("\n")
    hits = 0
    for rel in filter(None, tracked):
        p = ROOT / rel
        if not p.is_file() or p.suffix in {".xlsx", ".pptx", ".png"}:
            continue
        text = p.read_text(encoding="utf-8", errors="ignore")
        for term in terms:
            if term in text:
                hits += 1
                print(f"✗ {rel}: 含禁用詞「{term}」")
    print("✓ 未發現禁用詞" if not hits else f"共 {hits} 處")
    sys.exit(1 if hits else 0)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("doctor").set_defaults(fn=cmd_doctor)
    sub.add_parser("list").set_defaults(fn=cmd_list)
    p = sub.add_parser("new")
    p.add_argument("--agent", required=True)
    p.add_argument("--model", required=True)
    p.add_argument("--suite", choices=["quick", "full"], default="quick")
    p.add_argument("--mode", choices=["headless", "interactive"], default="headless")
    p.add_argument("--tasks")
    p.set_defaults(fn=cmd_new)
    p = sub.add_parser("run")
    p.add_argument("run_dir")
    p.add_argument("--tasks")
    p.set_defaults(fn=cmd_run)
    p = sub.add_parser("grade")
    p.add_argument("run_dir")
    p.set_defaults(fn=cmd_grade)
    sub.add_parser("board").set_defaults(fn=cmd_board)
    p = sub.add_parser("selftest")
    p.add_argument("--tasks")
    p.set_defaults(fn=cmd_selftest)
    sub.add_parser("lint-data").set_defaults(fn=cmd_lint_data)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
