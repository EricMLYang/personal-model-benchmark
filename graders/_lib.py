"""評分器共用工具。所有 check.py 皆回傳 items：[{name, weight, score(0~1), detail}]。

BENCH-GRADER-CANARY-7f3a9c1e
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml


def item(name: str, weight: float, score: float, detail: str = "") -> dict:
    return {"name": name, "weight": weight, "score": max(0.0, min(1.0, float(score))), "detail": detail}


def read_text(p: Path) -> str | None:
    try:
        return p.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def read_json(p: Path):
    t = read_text(p)
    if t is None:
        return None
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        return None


def read_yaml(p: Path):
    t = read_text(p)
    if t is None:
        return None
    try:
        return yaml.safe_load(t)
    except yaml.YAMLError:
        return None


def f1(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    f = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    return prec, rec, f


def run(cmd: list[str], cwd: Path, timeout: int = 300, env: dict | None = None) -> subprocess.CompletedProcess:
    e = os.environ.copy()
    e.update({"PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1"})
    if env:
        e.update(env)
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=timeout, env=e)


def unittest_counts(output: str) -> tuple[int, int]:
    """解析 unittest 輸出，回傳 (總數, 失敗+錯誤數)。"""
    m = re.search(r"Ran (\d+) tests?", output)
    total = int(m.group(1)) if m else 0
    bad = 0
    m = re.search(r"FAILED \(([^)]*)\)", output)
    if m:
        for k, v in re.findall(r"(failures|errors)=(\d+)", m.group(1)):
            bad += int(v)
    return total, bad


def unittest_results(output: str) -> dict[str, bool]:
    """解析 `unittest -v` 輸出，回傳 {測試名稱: 是否通過}。"""
    res = {}
    for m in re.finditer(r"^(test\w+) \(([\w.]+)\)[^\n]*?\.\.\. (ok|FAIL|ERROR|skipped.*)$", output, re.M):
        res[f"{m.group(2)}.{m.group(1)}"] = m.group(3) == "ok"
    return res


def fixed_fraction(baseline: dict[str, bool], after: dict[str, bool]) -> tuple[float, int, int, int]:
    """隱藏測試計分：原本失敗、現在通過的比例；原本通過、現在失敗的視為退步。
    回傳 (分數, 修好數, 應修數, 退步數)。"""
    target = [k for k, ok in baseline.items() if not ok]
    guards = [k for k, ok in baseline.items() if ok]
    fixed = sum(1 for k in target if after.get(k))
    broken = sum(1 for k in guards if not after.get(k))
    score = fixed / len(target) if target else 0.0
    if guards:
        score *= 1 - broken / len(guards)
    return score, fixed, len(target), broken


def pytest_counts(output: str) -> tuple[int, int]:
    passed = sum(int(x) for x in re.findall(r"(\d+) passed", output))
    failed = sum(int(x) for x in re.findall(r"(\d+) (?:failed|error|errors)", output))
    return passed + failed, failed


def copy_tree(src: Path, dst: Path) -> None:
    shutil.copytree(src, dst, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", "*.pyc"))


def temp_dir() -> tempfile.TemporaryDirectory:
    return tempfile.TemporaryDirectory(prefix="bench_grade_")


PY = sys.executable
