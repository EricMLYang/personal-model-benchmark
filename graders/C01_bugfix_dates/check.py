# BENCH-GRADER-CANARY-7f3a9c1e
from __future__ import annotations

import re
import shutil
from pathlib import Path

from _lib import (PY, copy_tree, fixed_fraction, item, read_text, run, temp_dir,
                  unittest_counts, unittest_results)

ORIGINAL_TESTS = ["test_util", "test_extract", "test_scheduler", "test_store"]
HIDDEN = "test_hidden_c01"


def _hidden(src: Path, task_dir: Path, grader_dir: Path, tmp: Path, name: str) -> dict[str, bool]:
    sandbox = tmp / name
    copy_tree(src, sandbox)
    for n in ORIGINAL_TESTS:  # 用原始版本的既有測試，避免作答改測試讓它通過
        shutil.copy2(task_dir / "inputs" / "tests" / f"{n}.py", sandbox / "tests" / f"{n}.py")
    shutil.copy2(grader_dir / "hidden_tests" / f"{HIDDEN}.py", sandbox / "tests" / f"{HIDDEN}.py")
    out = run([PY, "-m", "unittest", "-v", f"tests.{HIDDEN}"], sandbox, timeout=120)
    return unittest_results(out.stdout + out.stderr)


def grade(work: Path, task_dir: Path, grader_dir: Path) -> list[dict]:
    with temp_dir() as tmp:
        tmp = Path(tmp)
        base = _hidden(task_dir / "inputs", task_dir, grader_dir, tmp, "base")
        after = _hidden(work, task_dir, grader_dir, tmp, "after")
        hidden, fixed, target, broken = fixed_fraction(base, after)

        sandbox = tmp / "after"
        out = run([PY, "-m", "unittest", *[f"tests.{n}" for n in ORIGINAL_TESTS]], sandbox, timeout=120)
        e_total, e_bad = unittest_counts(out.stdout + out.stderr)
        existing = (e_total - e_bad) / e_total if e_total else 0.0

        original = {p.name for p in (task_dir / "inputs" / "tests").glob("*.py")}
        new_tests = [p.name for p in (work / "tests").glob("test_*.py") if p.name not in original]
        own_ok = 0.0
        if new_tests:
            out = run([PY, "-m", "unittest", *[f"tests.{p[:-3]}" for p in new_tests]], sandbox, timeout=120)
            n_total, n_bad = unittest_counts(out.stdout + out.stderr)
            own_ok = 1.0 if n_total and not n_bad else 0.0

    summary = read_text(work / "FIX_SUMMARY.md") or ""
    s1 = bool(re.search(r"台灣時間|時區|to_taipei|astimezone|UTC\+8", summary))
    s2 = bool(re.search(r"財年|fiscal|結束年", summary, re.I))
    gate = fixed > 0
    return [
        item("隱藏測試：修好的比例", 70, hidden, f"修好 {fixed}/{target}，退步 {broken}"),
        item("既有測試不退步", 15, existing if gate else 0, f"{e_total - e_bad}/{e_total} 通過"),
        item("自寫測試存在且通過", 7, own_ok, f"新增：{new_tests or '無'}"),
        item("FIX_SUMMARY 說明兩個根因", 8, (s1 + s2) / 2, f"時區={s1} 財年={s2}"),
    ]
