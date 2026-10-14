#!/usr/bin/env python3
"""把 registry.yaml（手填的 repo 清冊）＋各 repo 的 git 現況，渲染成 projects/_index.md。

用法：
  python render_registry.py --registry registry.yaml --projects projects --out projects/_index.md [--today 2026-10-14]

規則見 README.md。
"""
from __future__ import annotations

import argparse
import datetime as dt
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

TIER_ICON = {"active": "🟢 active", "paused": "🟡 paused", "dormant": "⚪ dormant", "archived": "🗄️ archived"}
ACTIVE_DAYS = 30


@dataclass
class GitState:
    cloned: bool
    branch: str = "—"
    last_commit: dt.date | None = None
    dirty: int = 0


def git(path: Path, *args: str) -> str:
    out = subprocess.run(["git", *args], cwd=path, capture_output=True, text=True, encoding="utf-8")
    return out.stdout.strip() if out.returncode == 0 else ""


def git_state(path: Path) -> GitState:
    if not (path / ".git").exists():
        return GitState(cloned=False)
    last = git(path, "log", "-1", "--format=%cs")
    status = git(path, "status", "--porcelain")
    return GitState(
        cloned=True,
        branch=git(path, "rev-parse", "--abbrev-ref", "HEAD") or "—",
        last_commit=dt.date.fromisoformat(last) if last else None,
        dirty=len([x for x in status.splitlines() if x.strip()]),
    )


def days_since(state: GitState, today: dt.date) -> int | None:
    if not state.cloned or state.last_commit is None:
        return None
    return (today - state.last_commit).days


def audit(repos: list[dict], states: dict[str, GitState], today: dt.date) -> list[str]:
    """回傳 ❌ 稽核問題（依 registry 順序）。"""
    issues = []
    for r in repos:
        name, tier = r["name"], r["tier"]
        d = days_since(states[name], today)
        override = bool(r.get("tier_override"))
        if tier == "paused" and not r.get("resume_when"):
            issues.append(f"- ❌ `{name}`：標 paused 但缺 resume_when")
        if tier == "archived" and not (r.get("ended") and r.get("reason")):
            issues.append(f"- ❌ `{name}`：標 archived 但缺 ended／reason")
        if d is None or override:
            continue
        if tier == "active" and d > ACTIVE_DAYS:
            issues.append(f"- ❌ `{name}`：標 active 但已 {d} 天沒有 commit")
        if tier == "dormant" and d <= ACTIVE_DAYS:
            issues.append(f"- ❌ `{name}`：標 dormant 但 {d} 天內有 commit")
    return issues


def drift(repos: list[dict], projects: Path) -> list[str]:
    listed = {r["name"] for r in repos}
    on_disk = sorted(p.name for p in projects.iterdir() if (p / ".git").exists()) if projects.exists() else []
    unlisted = [n for n in on_disk if n not in listed]
    missing = [r["name"] for r in repos if r["tier"] != "archived" and r["name"] not in on_disk]
    lines = []
    if unlisted:
        lines.append("- **在本機但未列管**：" + ", ".join(f"`{n}`" for n in unlisted))
    if missing:
        lines.append("- **列管但本機沒有**：" + ", ".join(f"`{n}`" for n in missing))
    return lines


def row(r: dict, s: GitState, today: dt.date) -> str:
    tier = TIER_ICON[r["tier"]]
    note = r.get("note", "")
    if not s.cloned:
        return f"| `{r['name']}` | {r['type']} | {tier} | `—` | （未 clone） | — | 0 | ⚠️ 未 clone — {note} |"
    last = s.last_commit.isoformat() if s.last_commit else "—"
    d = days_since(s, today)
    quiet = f"{d}d" if d is not None else "—"
    return f"| `{r['name']}` | {r['type']} | {tier} | `{s.branch}` | {last} | {quiet} | {s.dirty} | {note} |"


def render(reg: dict, states: dict[str, GitState], projects: Path, today: dt.date) -> str:
    repos = reg["repos"]
    out = ["# Projects Index", "",
           f"> 自動產生，請勿手改。來源：registry.yaml（updated: {reg.get('updated', '—')}）＋各 repo git 現況｜產生日：{today.isoformat()}",
           ""]
    for line in reg["lines"]:
        members = [r for r in repos if r["line"] == line["id"]]
        if not members:
            continue
        out += [f"## {line['name']}", "",
                "| repo | type | tier | 分支 | last commit | 沉寂 | dirty | 說明 |",
                "|------|------|------|------|-------------|:---:|:-----:|------|"]
        out += [row(r, states[r["name"]], today) for r in members]
        out.append("")
    out += ["## 🔎 tier 稽核", ""]
    issues = audit(repos, states, today)
    out += issues or ["- ✅ 所有 repo 的 tier 與 git 現況一致，必填欄位齊備"]
    out += ["", "## ⚠️ 漂移偵測", ""]
    out += drift(repos, projects) or ["- ✅ 無漂移"]
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--registry", default="registry.yaml")
    ap.add_argument("--projects", default="projects")
    ap.add_argument("--out", default="projects/_index.md")
    ap.add_argument("--today", help="固定今天日期（YYYY-MM-DD），測試用")
    args = ap.parse_args(argv)
    today = dt.date.fromisoformat(args.today) if args.today else dt.date.today()
    reg = yaml.safe_load(Path(args.registry).read_text(encoding="utf-8"))
    projects = Path(args.projects)
    states = {r["name"]: git_state(projects / r["name"]) for r in reg["repos"]}
    Path(args.out).write_text(render(reg, states, projects, today), encoding="utf-8")
    print(f"已寫入 {args.out}")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
