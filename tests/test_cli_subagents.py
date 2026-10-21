from pathlib import Path
import io
import os
import sys
import tempfile
import unittest
from unittest.mock import patch
import yaml

from agal.cli import main

MCP_FIXTURE = {"m1": {"config": {"command": "echo"}, "source": "test"}}


def _files(root):
    return sorted(str(p.relative_to(root)) for p in root.rglob("*") if p.is_file() or p.is_symlink())


class TestCLISubagents(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        root = Path(self.td.name)
        self.home_dir = root / "home"
        self.home_dir.mkdir()
        self.proj_dir = root / "project"
        self.proj_dir.mkdir()
        self.skills_dir = root / "skills"
        self.sub_dir = root / "subagents"
        self.presets_dir = root / "presets"

        for s in ["s1", "s2"]:
            (self.skills_dir / s).mkdir(parents=True)
            (self.skills_dir / s / "SKILL.md").write_text(
                f"---\nname: {s}\ndescription: Use when {s}.\n---\nBody\n", encoding="utf-8"
            )

        defs = {
            "alpha": "skills: [s1, s2]\nmcp: [m1]\n",
            "beta": "skills: [s2]\n",
            "ghost": "skills: [missing-skill]\nmcp: [missing-mcp]\n",
            "solo": "",
        }
        for n, extra in defs.items():
            (self.sub_dir / n).mkdir(parents=True)
            (self.sub_dir / n / "AGENT.md").write_text(
                f"---\nname: {n}\ndescription: Use when {n}.\n{extra}---\nBody\n", encoding="utf-8"
            )

        self.presets_dir.mkdir()
        (self.presets_dir / "p.yaml").write_text("name: p\nskills: [s1]\n", encoding="utf-8")

        cfg_content = {
            "skills_dir": str(self.skills_dir),
            "subagents_dir": str(self.sub_dir),
            "presets_dir": str(self.presets_dir),
            "sources_dir": str(root / "sources"),
            "context_file": str(root / "no-context.md"),
            "core_preset": None,
        }
        (self.home_dir / "config.yaml").write_text(
            yaml.safe_dump(cfg_content), encoding="utf-8"
        )

        self._patches = [
            patch.dict(os.environ, {"AGAL_HOME": str(self.home_dir), "HOME": str(self.home_dir)}),
            patch("agal.mcp.get_all_mcp_servers", return_value=MCP_FIXTURE),
            patch("pathlib.Path.cwd", return_value=self.proj_dir),
        ]
        for p in self._patches:
            p.start()

    def tearDown(self):
        for p in reversed(self._patches):
            p.stop()
        self.td.cleanup()

    def _run(self, argv):
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            main(argv)
        return buf.getvalue()

    def test_list(self):
        out = self._run(["subagent", "list"])
        self.assertIn("alpha", out)
        self.assertIn("beta", out)

    def test_add_and_remove(self):
        out = self._run(["subagent", "add", "alpha"])
        self.assertIn("alpha", out)
        self.assertTrue((self.proj_dir / ".claude" / "agents" / "alpha.md").is_file())
        self._run(["subagent", "remove", "alpha"])
        self.assertEqual(_files(self.proj_dir), [])

    def test_add_picker_when_no_names(self):
        with patch("agal.cli._select_items_cli", return_value=["beta"]):
            self._run(["subagent", "add"])
        self.assertTrue((self.proj_dir / ".claude" / "agents" / "beta.md").is_file())

    def test_cli_add_unknown_subagent(self):  # Review Focus 3 (CLI)
        out = self._run(["subagent", "add", "nope", "beta"])
        self.assertIn("❌", out)
        self.assertTrue((self.proj_dir / ".claude" / "agents" / "beta.md").is_file())

    def test_remove_not_installed_message(self):
        self.assertIn("not installed", self._run(["subagent", "remove", "alpha"]))

    def test_create(self):
        self._run(["subagent", "create", "fresh"])
        self.assertTrue((self.sub_dir / "fresh" / "AGENT.md").is_file())
        self.assertIn("❌", self._run(["subagent", "create", "fresh"]))

    def test_bare_subagent_prints_help(self):
        self.assertIn("add", self._run(["subagent"]))

    def test_preset_named_subagent_does_not_shadow_command(self):
        (self.presets_dir / "subagent.yaml").write_text("name: subagent\nskills: []\n", encoding="utf-8")
        self.assertIn("alpha", self._run(["subagent", "list"]))

    def test_cli_unprepare_only_subagents(self):  # Review Focus 5
        for argv in (["--unprepare"], ["unprepare"]):
            with self.subTest(argv=argv):
                self._run(["subagent", "add", "alpha", "beta"])
                self._run(argv)
                self.assertEqual(_files(self.proj_dir), [])

    def test_remove_preset_also_removes_subagents(self):
        self._run(["subagent", "add", "alpha"])
        self._run(["remove", "preset", "p"])
        self.assertEqual(_files(self.proj_dir), [])
