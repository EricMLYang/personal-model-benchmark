# BENCH-GRADER-CANARY-7f3a9c1e
from __future__ import annotations

import importlib.util
import re
from pathlib import Path

from _lib import item, read_json, read_text

HEADINGS = ["重點發現", "受眾包表現", "資料品質提醒"]
NUM_RE = re.compile(r"(?<![\w.\-/:])(\d{1,3}(?:,\d{3})+|\d+)(\.\d+)?(?![\w\-/:]|\.\d)")


def _solution(grader_dir: Path):
    spec = importlib.util.spec_from_file_location("x03_solution", grader_dir / "solution.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _match(got, exp) -> bool:
    if isinstance(exp, str):
        return isinstance(got, str) and got.strip() == exp
    try:
        return abs(float(got) - float(exp)) <= 0.011
    except (TypeError, ValueError):
        return False


def extract_numbers(text: str) -> list[tuple[float, int, str]]:
    """回傳 (數值, 小數位數, 原字串)；略過日期、代號、小於 100 的整數。"""
    text = re.sub(r"\d{4}-\d{2}-\d{2}|\d{1,2}-\d{2}|\d{1,2}/\d{1,2}", " ", text)
    out = []
    for m in NUM_RE.finditer(text):
        start = m.start()
        if start and re.match(r"[A-Za-z]", text[start - 1]):  # P02、Q01 這類代號
            continue
        ip, dp = m.group(1), m.group(2) or ""
        v = float(ip.replace(",", "") + dp)
        decimals = len(dp) - 1 if dp else 0
        tail = text[m.end():m.end() + 2]
        if decimals == 0 and v < 100 and "%" not in tail:
            continue
        out.append((v, decimals, m.group(0)))
    return out


def traceable(v: float, decimals: int, allowed: list[float]) -> bool:
    tol = 0.5 * 10 ** -decimals + 1e-9
    return any(abs(round(a, decimals) - v) <= tol or abs(a - v) <= tol for a in allowed)


def grade(work: Path, task_dir: Path, grader_dir: Path) -> list[dict]:
    sol = _solution(grader_dir)
    data = task_dir / "inputs" / "data"
    exp = sol.answers(data)
    got = read_json(work / "answers.json")
    items = []
    got = got if isinstance(got, dict) else {}
    for q, e in exp.items():
        ok = _match(got.get(q), e)
        items.append(item(f"{q}", 6, 1.0 if ok else 0.0, f"作答 {got.get(q)!r}"))

    report = read_text(work / "report.md")
    if not report:
        items.append(item("報告存在", 40, 0.0, "缺 report.md"))
        return items

    positions = [report.find(f"## {h}") for h in HEADINGS]
    heads_ok = all(p >= 0 for p in positions) and positions == sorted(positions)
    body = re.sub(r"[#*|>\-\s`]", "", report)
    length_ok = len(body) <= 800

    dq = report[positions[2]:] if positions[2] >= 0 else ""
    dq_nums = {n[2].replace(",", "") for n in re.finditer(r"\d[\d,]*", dq) for n in [(None, None, n.group(0))]}
    dq_hits = sum(1 for x in ("37", "58", "3") if x in dq_nums)

    allowed = sorted(sol.allowed_numbers(data))
    nums = extract_numbers(report)
    bad = [n[2] for n in nums if not traceable(n[0], n[1], allowed)]
    ratio = (len(nums) - len(bad)) / len(nums) if nums else 0.0
    trace_score = max(0.0, min(1.0, (ratio - 0.5) / 0.4))  # ≥ 90% 滿分、≤ 50% 零分

    items += [
        item("報告三個小節依序存在", 8, 1.0 if heads_ok else 0.0),
        item("報告 800 字以內", 4, 1.0 if length_ok else 0.0, f"{len(body)} 字"),
        item("資料品質段寫出排除數量（3／37／58）", 8, dq_hits / 3, f"命中 {dq_hits}/3"),
        item("報告數字可追溯", 20, trace_score,
             f"{len(nums) - len(bad)}/{len(nums)} 可追溯；無法追溯：{bad[:8]}"),
    ]
    return items
