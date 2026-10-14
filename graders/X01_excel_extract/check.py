# BENCH-GRADER-CANARY-7f3a9c1e
from __future__ import annotations

import re
from pathlib import Path

from _lib import f1, item, read_yaml


def norm_range(r) -> str | None:
    if r is None:
        return None
    return str(r).replace("$", "").replace("'", "").replace('"', "").strip().upper() or None


def norm_ref(ref, sheet: str) -> str | None:
    if not ref:
        return None
    s = str(ref).replace("$", "").replace("'", "").replace('"', "").strip()
    if "!" in s:
        sh, rng = s.rsplit("!", 1)
    else:
        sh, rng = sheet, s
    return f"{sh.strip()}!{rng.strip().upper()}"


def norm_text(t) -> str | None:
    if t is None:
        return None
    t = re.sub(r"\s+", "", str(t))
    return t.replace("(", "（").replace(")", "）") or None


def grade(work: Path, task_dir: Path, grader_dir: Path) -> list[dict]:
    exp = read_yaml(grader_dir / "reference" / "workbook_summary.yaml")
    got = read_yaml(work / "workbook_summary.yaml")
    if not isinstance(got, dict) or not isinstance(got.get("sheets"), list):
        return [item("workbook_summary.yaml 存在且可解析", 100, 0, "缺檔或格式錯誤")]

    exp_sheets = {s["name"]: s for s in exp["sheets"]}
    got_sheets = {str(s.get("name")): s for s in got["sheets"] if isinstance(s, dict)}
    order_ok = [s.get("name") for s in got["sheets"] if isinstance(s, dict)] == [s["name"] for s in exp["sheets"]]

    # ---- blocks
    def blocks(sheets):
        out = {}
        for name, s in sheets.items():
            for b in s.get("blocks") or []:
                if isinstance(b, dict):
                    out[(name, norm_range(b.get("range")))] = b
        return out

    eb, gb = blocks(exp_sheets), blocks(got_sheets)
    tp = len(set(eb) & set(gb))
    _, _, bf1 = f1(tp, len(set(gb) - set(eb)), len(set(eb) - set(gb)))
    matched = [k for k in eb if k in gb]
    n = len(eb)

    def frac(pred):
        return sum(1 for k in matched if pred(eb[k], gb[k])) / n

    title = frac(lambda e, g: norm_text(e["title"]) == norm_text(g.get("title")))
    header = frac(lambda e, g: [norm_text(x) for x in e["header"]] == [norm_text(x) for x in (g.get("header") or [])])
    kind = frac(lambda e, g: e["kind"] == g.get("kind") and e["table_name"] == g.get("table_name"))
    formulas = frac(lambda e, g: e["has_formulas"] == g.get("has_formulas"))
    notes = frac(lambda e, g: [norm_text(x) for x in e["notes"]] == [norm_text(x) for x in (g.get("notes") or [])])

    # ---- charts
    def charts(sheets):
        out = {}
        for name, s in sheets.items():
            for c in s.get("charts") or []:
                if isinstance(c, dict):
                    out[(name, norm_text(c.get("title")))] = c
        return out

    ec, gc = charts(exp_sheets), charts(got_sheets)
    ctp = len(set(ec) & set(gc))
    _, _, cf1 = f1(ctp, len(set(gc) - set(ec)), len(set(ec) - set(gc)))
    cm = [k for k in ec if k in gc]
    m = len(ec)

    def series_set(c, sheet, field):
        return {norm_ref(s.get(field), sheet) for s in (c.get("series") or []) if isinstance(s, dict)}

    ctype = sum(1 for k in cm if ec[k]["type"] == gc[k].get("type")) / m
    values = sum(1 for k in cm if series_set(ec[k], k[0], "values_ref") == series_set(gc[k], k[0], "values_ref")) / m
    others = sum(1 for k in cm
                 if series_set(ec[k], k[0], "name_ref") == series_set(gc[k], k[0], "name_ref")
                 and series_set(ec[k], k[0], "categories_ref") == series_set(gc[k], k[0], "categories_ref")) / m
    link = sum(1 for k in cm if norm_range(ec[k]["linked_block"]) == norm_range(gc[k].get("linked_block"))
               and ec[k]["confidence"] == gc[k].get("confidence")) / m
    trap = ("產能概況", norm_text("A廠產能與稼動率"))
    trap_ok = trap in gc and gc[trap].get("linked_block") is None and gc[trap].get("confidence") == "low"

    return [
        item("sheet 清單與順序", 4, 1.0 if order_ok else 0.0),
        item("區塊範圍（F1）", 22, bf1, f"命中 {tp}/{n}，多報 {len(set(gb) - set(eb))}"),
        item("區塊標題", 10, title),
        item("表頭", 5, header),
        item("kind / table_name", 7, kind),
        item("has_formulas", 5, formulas),
        item("註記", 4, notes),
        item("圖表辨識（F1）", 10, cf1, f"命中 {ctp}/{m}"),
        item("圖表類型", 5, ctype),
        item("系列 values 範圍", 12, values),
        item("系列名稱與類別範圍", 5, others),
        item("圖表 → 區塊對應與信心度", 8, link),
        item("跨區塊圖表標 null / low（不硬猜）", 3, 1.0 if trap_ok else 0.0),
    ]
