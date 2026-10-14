# BENCH-GRADER-CANARY-7f3a9c1e
from __future__ import annotations

import shutil
from pathlib import Path

from _lib import (PY, copy_tree, fixed_fraction, item, pytest_counts, read_text, run, temp_dir,
                  unittest_results)

HIDDEN = "test_hidden_c03"

# 由參考解答產生的變異體：好的測試應該讓每一個變異體失敗
MUTANTS = {
    "90 天邊界改成 >=": ("d > DORMANT_WARN_DAYS", "d >= DORMANT_WARN_DAYS"),
    "--check 永遠回 0": ("return 1 if errors or drifts else 0", "return 0"),
    "--check 仍寫檔": ("        return 1 if errors or drifts else 0",
                     "        Path(args.out).write_text(render(reg, states, projects, today), encoding=\"utf-8\")\n"
                     "        return 1 if errors or drifts else 0"),
    "警示也讓結束碼為 1": ("return 1 if errors or drifts else 0", "return 1 if errors or drifts or warns else 0"),
    "只有警示時仍印 ✅": ("issues = audit(repos, states, today) + warnings(repos, states, today)\n    out += issues or [OK_AUDIT]",
                    "issues = audit(repos, states, today)\n    out += (issues or [OK_AUDIT]) + warnings(repos, states, today)"),
    "override 仍產生警示": ('and not r.get("tier_override") and d is not None', "and d is not None"),
}


def _hidden(src: Path, grader_dir: Path, sandbox: Path) -> dict[str, bool]:
    copy_tree(src, sandbox)
    (sandbox / "tests").mkdir(exist_ok=True)
    for f in (grader_dir / "hidden_tests").iterdir():
        if f.is_file():
            shutil.copy2(f, sandbox / "tests" / f.name)
    out = run([PY, "-m", "unittest", "-v", f"tests.{HIDDEN}"], sandbox, timeout=300)
    return unittest_results(out.stdout + out.stderr)


def _own_tests(sandbox: Path) -> tuple[int, int]:
    out = run([PY, "-m", "pytest", "tests/test_render_registry.py", "-q", "-p", "no:cacheprovider"],
              sandbox, timeout=300)
    return pytest_counts(out.stdout + out.stderr)


def grade(work: Path, task_dir: Path, grader_dir: Path) -> list[dict]:
    ref_src = (grader_dir / "reference" / "render_registry.py").read_text(encoding="utf-8")
    with temp_dir() as tmp:
        tmp = Path(tmp)
        base = _hidden(task_dir / "inputs", grader_dir, tmp / "base")
        after = _hidden(work, grader_dir, tmp / "after")
        hidden, fixed, target, broken = fixed_fraction(base, after)

        has_tests = (work / "tests" / "test_render_registry.py").exists()
        own_total = own_bad = 0
        killed, mut_detail = 0, "無測試檔"
        if has_tests:
            own = tmp / "own"
            copy_tree(work, own)
            own_total, own_bad = _own_tests(own)
            # 變異測試：先確認測試在參考解答上通過，再逐一換成變異體
            (own / "render_registry.py").write_text(ref_src, encoding="utf-8")
            r_total, r_bad = _own_tests(own)
            if r_total and not r_bad:
                survived = []
                for name, (old, new) in MUTANTS.items():
                    assert old in ref_src, name
                    (own / "render_registry.py").write_text(ref_src.replace(old, new, 1), encoding="utf-8")
                    m_total, m_bad = _own_tests(own)
                    if m_bad or not m_total:
                        killed += 1
                    else:
                        survived.append(name)
                mut_detail = f"殺死 {killed}/{len(MUTANTS)}；存活：{survived or '無'}"
            else:
                mut_detail = f"測試在參考解答上未全數通過（{r_total - r_bad}/{r_total}），不計變異分"

    readme = read_text(work / "README.md") or ""
    own_ok = 1.0 if own_total >= 5 and not own_bad else (0.5 if own_total and not own_bad else 0.0)
    return [
        item("隱藏測試：新功能與不退步", 62, hidden, f"新功能通過 {fixed}/{target}，退步 {broken}"),
        item("自寫測試通過（≥ 5 個）", 10, own_ok, f"{own_total - own_bad}/{own_total} 通過"),
        item("自寫測試的變異殺傷率", 25, killed / len(MUTANTS), mut_detail),
        item("README 說明 --check", 3, 1.0 if "--check" in readme else 0.0, ""),
    ]
