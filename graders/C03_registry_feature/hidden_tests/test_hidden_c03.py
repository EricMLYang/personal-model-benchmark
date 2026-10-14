# BENCH-GRADER-CANARY-7f3a9c1e
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
SCRIPT = HERE.parent / "render_registry.py"
GOLDEN = HERE / "golden_s1.md"
TODAY = "2026-10-14"
OK_AUDIT = "- ✅ 所有 repo 的 tier 與 git 現況一致，必填欄位齊備"


def make_repo(projects: Path, name: str, date: str | None) -> None:
    p = projects / name
    p.mkdir(parents=True)
    env = os.environ.copy()
    env.update({"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com", "GIT_COMMITTER_NAME": "t",
                "GIT_COMMITTER_EMAIL": "t@example.com"})
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=p, check=True, env=env)
    if date:
        env["GIT_AUTHOR_DATE"] = env["GIT_COMMITTER_DATE"] = f"{date}T12:00:00+08:00"
        (p / "README.md").write_text(name, encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=p, check=True, env=env)
        subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=p, check=True, env=env)


class Scenario:
    def __init__(self, repos, on_disk, extra=()):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.projects = self.root / "projects"
        self.projects.mkdir()
        lines = [{"id": "a", "name": "A 線"}, {"id": "b", "name": "B 線"}]
        reg = {"updated": "2026-10-01", "lines": lines, "repos": repos}
        self.registry = self.root / "registry.yaml"
        self.registry.write_text(yaml.safe_dump(reg, allow_unicode=True, sort_keys=False), encoding="utf-8")
        for name, date in on_disk.items():
            make_repo(self.projects, name, date)
        for name in extra:
            make_repo(self.projects, name, "2026-10-01")
        self.out = self.root / "_index.md"

    def run(self, *extra):
        cmd = [sys.executable, str(SCRIPT), "--registry", str(self.registry), "--projects", str(self.projects),
               "--out", str(self.out), "--today", TODAY, *extra]
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"
        return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", env=env)

    def text(self):
        return self.out.read_text(encoding="utf-8")

    def close(self):
        self.tmp.cleanup()


def repo(name, tier, line="a", **kw):
    d = {"name": name, "line": line, "type": "code", "tier": tier, "note": f"{name} 說明"}
    d.update(kw)
    return d


def warn(name, days):
    return f"- ⚠️ `{name}`：dormant 已 {days} 天，請決定復工或改 archived"


class Base(unittest.TestCase):
    def scenario(self, repos, on_disk, extra=()):
        s = Scenario(repos, on_disk, extra)
        self.addCleanup(s.close)
        return s


class TestGolden(Base):
    def test_golden_full_render(self):
        repos = [
            repo("insight_pm", "active", type="pm"),
            repo("event_crawler", "active"),
            repo("quarterly_deck", "paused", resume_when="每季簡報"),
            repo("signage_pm", "active", line="b", type="pm"),
            repo("signage_datahub", "dormant", line="b"),
            repo("legacy_middleware", "archived", line="b", ended="2026-06", reason="Demo 交付完成"),
            repo("study_group", "active", line="b", tier_override="讀書會節奏較慢"),
        ]
        on_disk = {"insight_pm": "2026-10-10", "event_crawler": "2026-08-01", "signage_pm": "2026-10-13",
                   "signage_datahub": "2026-06-01", "study_group": "2026-07-01"}
        s = self.scenario(repos, on_disk, extra=["scratch_repo"])
        r = s.run()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(s.text().replace("\r\n", "\n"), GOLDEN.read_text(encoding="utf-8").replace("\r\n", "\n"))


class TestDormantWarning(Base):
    def test_warn_91_days(self):
        s = self.scenario([repo("old", "dormant")], {"old": "2026-07-15"})
        s.run()
        self.assertIn(warn("old", 91), s.text())

    def test_no_warn_90_days(self):
        s = self.scenario([repo("old", "dormant")], {"old": "2026-07-16"})
        s.run()
        self.assertNotIn("⚠️ `old`", s.text())
        self.assertIn(OK_AUDIT, s.text())

    def test_override_no_warn(self):
        s = self.scenario([repo("old", "dormant", tier_override="x")], {"old": "2026-01-01"})
        s.run()
        self.assertNotIn("⚠️ `old`", s.text())

    def test_uncloned_dormant_no_warn(self):
        s = self.scenario([repo("old", "dormant")], {})
        s.run()
        self.assertNotIn("⚠️ `old`", s.text())

    def test_ok_line_hidden_when_only_warning(self):
        s = self.scenario([repo("old", "dormant")], {"old": "2026-05-01"})
        s.run()
        self.assertIn(warn("old", 166), s.text())
        self.assertNotIn(OK_AUDIT, s.text())

    def test_errors_before_warnings(self):
        s = self.scenario([repo("old", "dormant"), repo("hot", "active")], {"old": "2026-05-01", "hot": "2026-08-01"})
        s.run()
        t = s.text()
        e = t.find("- ❌ `hot`")
        w = t.find(warn("old", 166))
        self.assertTrue(e >= 0 and w >= 0 and e < w, t)


class TestCheckMode(Base):
    def test_check_clean_exit0_no_file(self):
        s = self.scenario([repo("ok", "active")], {"ok": "2026-10-10"})
        r = s.run("--check")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertFalse(s.out.exists())

    def test_check_error_exit1(self):
        s = self.scenario([repo("hot", "active")], {"hot": "2026-08-01"})
        r = s.run("--check")
        self.assertEqual(r.returncode, 1)
        self.assertIn("- ❌ `hot`：標 active 但已 74 天沒有 commit", r.stdout)
        self.assertFalse(s.out.exists())

    def test_check_drift_exit1(self):
        s = self.scenario([repo("ok", "active")], {"ok": "2026-10-10"}, extra=["stray"])
        r = s.run("--check")
        self.assertEqual(r.returncode, 1)
        self.assertIn("`stray`", r.stdout)

    def test_check_missing_paused_is_drift(self):
        s = self.scenario([repo("ok", "active"), repo("p", "paused", resume_when="x")], {"ok": "2026-10-10"})
        self.assertEqual(s.run("--check").returncode, 1)

    def test_check_warning_only_exit0(self):
        s = self.scenario([repo("old", "dormant")], {"old": "2026-05-01"})
        r = s.run("--check")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn(warn("old", 166), r.stdout)

    def test_check_does_not_overwrite(self):
        s = self.scenario([repo("hot", "active")], {"hot": "2026-08-01"})
        s.out.write_text("舊內容", encoding="utf-8")
        s.run("--check")
        self.assertEqual(s.out.read_text(encoding="utf-8"), "舊內容")


class TestUnchanged(Base):
    def test_normal_mode_writes(self):
        s = self.scenario([repo("ok", "active")], {"ok": "2026-10-10"})
        r = s.run()
        self.assertEqual(r.returncode, 0)
        self.assertIn("| `ok` | code | 🟢 active | `main` | 2026-10-10 | 4d | 0 | ok 說明 |", s.text())

    def test_archived_missing_no_drift(self):
        s = self.scenario([repo("ok", "active"), repo("gone", "archived", ended="2026-01", reason="r")],
                          {"ok": "2026-10-10"})
        s.run()
        self.assertIn("- ✅ 無漂移", s.text())

    def test_dormant_recent_is_error(self):
        s = self.scenario([repo("d", "dormant")], {"d": "2026-10-01"})
        s.run()
        self.assertIn("- ❌ `d`：標 dormant 但 13 天內有 commit", s.text())


if __name__ == "__main__":
    unittest.main()
