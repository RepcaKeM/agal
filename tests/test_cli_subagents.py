from pathlib import Path
import io
import json
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

    def test_bare_subagent_prints_help_when_not_a_tty(self):
        with patch("sys.stdin.isatty", return_value=False):
            self.assertIn("add", self._run(["subagent"]))

    def test_bare_subagent_wizard_sets_runtime_then_installs(self):
        with (
            patch("sys.stdin.isatty", return_value=True),
            patch("agal.cli._select_items_cli", side_effect=[["cursor"], ["beta"]]),
        ):
            out = self._run(["subagent"])
        self.assertIn("cursor", out)
        self.assertIn("beta", out)
        self.assertTrue((self.proj_dir / ".cursor" / "agents" / "beta.md").is_file())
        self.assertFalse((self.proj_dir / ".claude").exists())
        self.assertTrue((self.proj_dir / ".agents" / "skills" / "s2").is_dir())

    def test_bare_subagent_wizard_can_skip_runtime(self):
        with (
            patch("sys.stdin.isatty", return_value=True),
            patch("agal.cli._select_items_cli", side_effect=[[], ["solo"]]),
        ):
            out = self._run(["subagent"])
        self.assertIn("Installed subagent 'solo'", out)
        self.assertTrue((self.proj_dir / ".claude" / "agents" / "solo.md").is_file())
        self.assertTrue((self.proj_dir / ".cursor" / "agents" / "solo.md").is_file())

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

    def test_runtime_set_rebuilds_project_files(self):
        self._run(["subagent", "add", "alpha"])
        out = self._run(["runtime", "set", "cursor"])
        self.assertIn("cursor", out)
        self.assertTrue((self.proj_dir / ".cursor" / "agents" / "alpha.md").is_file())
        self.assertFalse((self.proj_dir / ".claude").exists())
        self.assertFalse((self.proj_dir / ".opencode").exists())
        self.assertFalse((self.proj_dir / ".mcp.json").exists())
        mcp = json.loads((self.proj_dir / ".cursor" / "mcp.json").read_text(encoding="utf-8"))
        self.assertIn("m1", mcp["mcpServers"])
        skill = self.proj_dir / ".agents" / "skills" / "s1"
        self.assertTrue(skill.is_dir())
        self.assertFalse(skill.is_symlink())

    def test_runtime_reset_and_alias(self):
        self._run(["ide", "set", "cursor"])
        self._run(["subagent", "add", "solo"])
        self.assertFalse((self.proj_dir / ".claude" / "agents" / "solo.md").exists())
        self._run(["target", "reset"])
        self.assertTrue((self.proj_dir / ".claude" / "agents" / "solo.md").is_file())
        self.assertTrue((self.proj_dir / ".opencode" / "agents" / "solo.md").is_file())
        self.assertTrue((self.proj_dir / ".agents" / "agents" / "solo" / "agent.md").is_file())
        unknown = self._run(["runtime", "set", "nope"])
        self.assertIn("Unknown runtime", unknown)

    def test_prepare_respects_runtime_and_copies_guidelines(self):
        cfg = yaml.safe_load((self.home_dir / "config.yaml").read_text(encoding="utf-8"))
        Path(cfg["context_file"]).write_text("# guidelines\n", encoding="utf-8")
        self._run(["runtime", "set", "agy"])
        self._run(["prepare", "p"])
        self.assertTrue((self.proj_dir / "AGENTS.md").is_file())
        self.assertFalse((self.proj_dir / "AGENTS.md").is_symlink())
        self.assertTrue((self.proj_dir / "GEMINI.md").is_file())
        self.assertFalse((self.proj_dir / "CLAUDE.md").exists())
        self.assertFalse((self.proj_dir / "KIMI.md").exists())
        self.assertTrue((self.proj_dir / ".agents" / "skills" / "s1").is_dir())
        self.assertFalse((self.proj_dir / ".claude").exists())

    def test_subagent_info_status_and_invalid_name(self):
        info = self._run(["subagent", "info", "alpha"])
        self.assertIn("s1", info)
        self.assertIn("m1", info)
        created = self._run(["subagent", "create", "../evil"])
        self.assertIn("❌", created)
        self.assertFalse(any(path.name.startswith("..") for path in self.sub_dir.iterdir()))
        self._run(["runtime", "set", "claude"])
        self._run(["subagent", "add", "solo"])
        status = self._run(["status"])
        self.assertIn("solo", status)
        self.assertIn("claude", status)
        checked = self._run(["check"])
        self.assertIn("alpha", checked)
        self.assertIn("solo", checked)

    def test_subagent_wizard_replaces_previous_subagents_and_keeps_preset(self):
        self._run(["prepare", "p"])
        self._run(["subagent", "add", "alpha"])
        self.assertTrue((self.proj_dir / ".claude" / "agents" / "alpha.md").is_file())
        self.assertTrue((self.proj_dir / ".claude" / "skills" / "s2").is_dir())

        with (
            patch("sys.stdin.isatty", return_value=True),
            patch("agal.cli._select_items_cli", side_effect=[[], ["solo"]]),
            patch("builtins.input", return_value="y"),
        ):
            out = self._run(["subagent"])

        self.assertIn("alpha", out.split("Removed subagent")[0])
        self.assertIn("Removed subagent 'alpha'", out)
        self.assertIn("Installed subagent 'solo'", out)
        self.assertFalse((self.proj_dir / ".claude" / "agents" / "alpha.md").exists())
        self.assertTrue((self.proj_dir / ".claude" / "agents" / "solo.md").is_file())
        self.assertFalse((self.proj_dir / ".claude" / "skills" / "s2").exists())
        self.assertFalse((self.proj_dir / ".mcp.json").exists())
        self.assertTrue((self.proj_dir / ".claude" / "skills" / "s1").is_dir())
        state = json.loads((self.proj_dir / ".agal_state.json").read_text(encoding="utf-8"))
        self.assertEqual(state.get("preset"), "p")
        self.assertEqual(list(state.get("subagents", {}).keys()), ["solo"])

    def test_subagent_wizard_declined_removal_keeps_previous_subagents(self):
        self._run(["subagent", "add", "alpha"])
        with (
            patch("sys.stdin.isatty", return_value=True),
            patch("agal.cli._select_items_cli", side_effect=[[], ["solo"]]),
            patch("builtins.input", return_value=""),
        ):
            out = self._run(["subagent"])
        self.assertNotIn("Removed subagent", out)
        state = json.loads((self.proj_dir / ".agal_state.json").read_text(encoding="utf-8"))
        self.assertEqual(sorted(state.get("subagents", {})), ["alpha", "solo"])

    def test_subagent_wizard_empty_selection_keeps_installed_subagents(self):
        self._run(["subagent", "add", "alpha"])
        with (
            patch("sys.stdin.isatty", return_value=True),
            patch("agal.cli._select_items_cli", side_effect=[["cursor"], []]),
        ):
            self._run(["subagent"])

        state = json.loads((self.proj_dir / ".agal_state.json").read_text(encoding="utf-8"))
        self.assertEqual(state.get("runtimes"), ["cursor"])
        self.assertIn("alpha", state.get("subagents", {}))
        self.assertTrue((self.proj_dir / ".cursor" / "agents" / "alpha.md").is_file())
