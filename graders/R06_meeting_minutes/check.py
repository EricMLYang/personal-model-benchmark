# BENCH-GRADER-CANARY-7f3a9c1e
from __future__ import annotations

from pathlib import Path

from _lib import f1, item, read_json, read_text, read_yaml


def _texts(lst, field="text") -> list[str]:
    out = []
    for x in lst or []:
        if isinstance(x, dict):
            out.append(str(x.get(field, "")))
        elif isinstance(x, str):
            out.append(x)
    return out


def _norm(s: str) -> str:
    return s.replace(" ", "").replace("／", "/")


def grade(work: Path, task_dir: Path, grader_dir: Path) -> list[dict]:
    key = read_yaml(grader_dir / "answer_key.yaml")
    m = read_json(work / "minutes.json")
    if not isinstance(m, dict):
        return [item("minutes.json 存在且可解析", 100, 0, "缺檔或格式錯誤")]

    # ---- 決策
    decisions = [_norm(t) for t in _texts(m.get("decisions"))]
    found = []
    for d in key["decisions"]:
        ok = any(all(_norm(k) in t for k in group) for t in decisions for group in d["any_of"])
        found.append(ok)
    ov = key["overturned"]
    overturned_listed = [t for t in decisions
                         if all(k in t for k in ov["must_have"]) and any(k in t for k in ov["any_marker"])
                         and not any(k in t for k in ov["unless_any"])]

    # ---- 行動項
    actions = [a for a in (m.get("actions") or []) if isinstance(a, dict)]
    used, matched, due_ok = set(), 0, 0
    for exp in key["actions"]:
        for i, a in enumerate(actions):
            if i in used:
                continue
            if str(a.get("owner", "")).strip() == exp["owner"] and any(k in str(a.get("task", "")) for k in exp["keywords"]):
                used.add(i)
                matched += 1
                due_ok += str(a.get("due", "")).strip() == exp["due"]
                break
    fp = len(actions) - len(used)
    _, _, act_f1 = f1(matched, fp, len(key["actions"]) - matched)
    owners = {str(a.get("owner", "")).strip() for a in actions}
    fabricated = sorted(o for o in owners if o not in key["attendees"])

    # ---- 待決事項
    oq_kw = key["open_question"]["keywords"]
    in_open = any(any(k in t for k in oq_kw) for t in _texts(m.get("open_questions")))
    in_actions = any(any(k in str(a.get("task", "")) for k in oq_kw) for a in actions)

    md = read_text(work / "minutes.md") or ""
    md_ok = ("|" in md) and sum(1 for a in key["actions"] if a["owner"] in md) >= 5

    has_decisions = bool(decisions)
    return [
        item("會議日期", 3, 1.0 if m.get("meeting_date") == key["meeting_date"] else 0.0),
        item("最終決策命中", 20, sum(found) / len(found), f"{dict(zip([d['id'] for d in key['decisions']], found))}"),
        item("被推翻的決定未列為決策", 10, (0.0 if overturned_listed else 1.0) if has_decisions else 0.0,
             f"誤列：{overturned_listed or '無'}"),
        item("行動項（負責人＋事項）F1", 30, act_f1, f"命中 {matched}/{len(key['actions'])}，多報 {fp}"),
        item("期限換算正確", 15, due_ok / len(key["actions"]), f"{due_ok}/{len(key['actions'])}"),
        item("無負責人的提議列為待決、未自行指派", 10, 1.0 if in_open and not in_actions else 0.0,
             f"open={in_open} action={in_actions}"),
        item("負責人皆為與會者（未編造）", 5, (0.0 if fabricated else 1.0) if actions else 0.0,
             f"非與會者：{fabricated or '無'}"),
        item("minutes.md 含行動項表", 7, 1.0 if md_ok else 0.0),
    ]
