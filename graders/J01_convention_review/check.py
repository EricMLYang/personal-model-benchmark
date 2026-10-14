# BENCH-GRADER-CANARY-7f3a9c1e
from __future__ import annotations

import re
from pathlib import Path

from _lib import f1, item, read_json, read_text, read_yaml


def cell_tags(nb: str) -> dict[str, int]:
    cells = nb.split("# COMMAND ----------")
    tags = {}
    for i, c in enumerate(cells, 1):
        lines = [x for x in c.strip().splitlines() if x.strip() and not x.startswith("# Databricks")]
        m = re.match(r"# \[(c\d+[a-z]?)\]", lines[0]) if lines else None
        if m:
            tags[m.group(1)] = i
    return tags


def grade(work: Path, task_dir: Path, grader_dir: Path) -> list[dict]:
    key = read_yaml(grader_dir / "answer_key.yaml")
    truth = {(c, r) for c, r in key["violations"]}
    decoys = {(c, r) for c, r in key["decoys"]}
    nb = (task_dir / "inputs" / "jobs" / "daily_sales" / "notebook.py").read_text(encoding="utf-8")
    tags = cell_tags(nb)

    data = read_json(work / "findings.json")
    if not isinstance(data, list):
        return [item("findings.json 存在且為陣列", 100, 0, "缺檔或格式錯誤")]

    reported, fixes = set(), {}
    for f in data:
        if not isinstance(f, dict):
            continue
        rule = str(f.get("rule", "")).strip().upper()
        cell = f.get("cell")
        if not isinstance(cell, int) and f.get("tag") in tags:
            cell = tags[f["tag"]]
        if isinstance(cell, int) and re.fullmatch(r"R\d+", rule):
            reported.add((cell, rule))
            fixes[(cell, rule)] = str(f.get("fix") or "").strip()

    tp = len(reported & truth)
    fp = len(reported - truth)
    fn = len(truth - reported)
    prec, rec, score = f1(tp, fp, fn)
    decoy_hits = reported & decoys
    fix_ok = sum(1 for k in reported & truth if len(fixes.get(k, "")) >= 6) / len(truth)

    review = read_text(work / "review.md") or ""
    review_lines = [x for x in review.splitlines() if x.strip()]
    return [
        item("違規找出 F1", 75, score, f"TP {tp}、FP {fp}、FN {fn}（precision {prec:.2f}、recall {rec:.2f}）；"
                                      f"漏報 {sorted(truth - reported)}"),
        item("陷阱未誤報", 10, (1 - len(decoy_hits) / len(decoys)) if reported else 0.0,
             f"誤報陷阱：{sorted(decoy_hits) or '無'}"),
        item("每筆命中附具體修正建議", 10, fix_ok),
        item("review.md 存在（5–10 行）", 5, 1.0 if 5 <= len(review_lines) <= 12 else (0.5 if review_lines else 0.0),
             f"{len(review_lines)} 行"),
    ]
