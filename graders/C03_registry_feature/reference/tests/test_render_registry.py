import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

SCRIPT = Path(__file__).resolve().parent.parent / "render_registry.py"
OK = "- ✅ 所有 repo 的 tier 與 git 現況一致，必填欄位齊備"


def _repo(projects, name, date):
    p = projects / name
    p.mkdir()
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@x", "GIT_COMMITTER_NAME": "t",
           "GIT_COMMITTER_EMAIL": "t@x", "GIT_AUTHOR_DATE": f"{date}T12:00:00+08:00",
           "GIT_COMMITTER_DATE": f"{date}T12:00:00+08:00"}
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=p, check=True, env=env)
    (p / "f").write_text("x")
    subprocess.run(["git", "add", "."], cwd=p, check=True, env=env)
    subprocess.run(["git", "commit", "-q", "-m", "c"], cwd=p, check=True, env=env)


@pytest.fixture
def make(tmp_path):
    def _make(repos, dates, extra=()):
        projects = tmp_path / "projects"
        projects.mkdir()
        for n, d in dates.items():
            _repo(projects, n, d)
        for n in extra:
            _repo(projects, n, "2026-10-01")
        for r in repos:
            r.setdefault("line", "a")
            r.setdefault("type", "code")
        reg = tmp_path / "registry.yaml"
        reg.write_text(yaml.safe_dump({"lines": [{"id": "a", "name": "A"}], "repos": repos}, allow_unicode=True),
                       encoding="utf-8")
        out = tmp_path / "_index.md"

        def run(*extra_args):
            env = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}
            return subprocess.run([sys.executable, str(SCRIPT), "--registry", str(reg), "--projects", str(projects),
                                   "--out", str(out), "--today", "2026-10-14", *extra_args],
                                  capture_output=True, text=True, encoding="utf-8", env=env)
        return run, out
    return _make


def test_warn_91(make):
    run, out = make([{"name": "d", "tier": "dormant"}], {"d": "2026-07-15"})
    run()
    assert "- ⚠️ `d`：dormant 已 91 天，請決定復工或改 archived" in out.read_text(encoding="utf-8")


def test_no_warn_90(make):
    run, out = make([{"name": "d", "tier": "dormant"}], {"d": "2026-07-16"})
    run()
    text = out.read_text(encoding="utf-8")
    assert "⚠️ `d`" not in text and OK in text


def test_override_no_warn(make):
    run, out = make([{"name": "d", "tier": "dormant", "tier_override": "x"}], {"d": "2026-01-01"})
    run()
    assert "⚠️ `d`" not in out.read_text(encoding="utf-8")


def test_only_warning_hides_ok(make):
    run, out = make([{"name": "d", "tier": "dormant"}], {"d": "2026-05-01"})
    run()
    assert OK not in out.read_text(encoding="utf-8")


def test_check_clean(make):
    run, out = make([{"name": "a", "tier": "active"}], {"a": "2026-10-10"})
    assert run("--check").returncode == 0
    assert not out.exists()


def test_check_error(make):
    run, out = make([{"name": "a", "tier": "active"}], {"a": "2026-08-01"})
    r = run("--check")
    assert r.returncode == 1 and "❌ `a`" in r.stdout and not out.exists()


def test_check_drift(make):
    run, _ = make([{"name": "a", "tier": "active"}], {"a": "2026-10-10"}, extra=["stray"])
    assert run("--check").returncode == 1


def test_check_warning_only_exit0(make):
    run, _ = make([{"name": "d", "tier": "dormant"}], {"d": "2026-05-01"})
    r = run("--check")
    assert r.returncode == 0 and "⚠️ `d`" in r.stdout
