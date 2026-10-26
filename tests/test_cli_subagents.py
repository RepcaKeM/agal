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

    def test_start_picks_runtime_preset_subagents_then_extra_skills(self):
        (self.skills_dir / "s3").mkdir()
        (self.skills_dir / "s3" / "SKILL.md").write_text(
            "---\nname: s3\ndescription: Use when s3.\n---\nBody\n", encoding="utf-8"
        )
        answers = [["claude"], ["p"], ["beta"], ["s3"]]
        offered = []

        def pick(items, *args, **kwargs):
            offered.append(list(items))
            return answers.pop(0)

        with (
            patch("sys.stdin.isatty", return_value=True),
            patch("agal.cli._select_items_cli", side_effect=pick),
            patch("builtins.input", return_value=""),
        ):
            out = self._run(["start"])
        self.assertIn("Step 6 of 6", out)
        self.assertEqual(offered[3], ["s3"])
        state = json.loads((self.proj_dir / ".agal_state.json").read_text(encoding="utf-8"))
        self.assertEqual(state.get("runtimes"), ["claude"])
        self.assertEqual(state.get("preset"), "p")
        self.assertEqual(list(state.get("subagents", {})), ["beta"])
        self.assertEqual(sorted(state.get("skills", {})), ["s1", "s2", "s3"])
        self.assertNotIn("s3", state.get("preset_owned", {}).get("skills", []))
        self.assertTrue((self.proj_dir / ".claude" / "skills" / "s3").is_dir())

    def test_start_installs_selected_hook(self):
        hook_src = Path(self.td.name) / "sources" / "hooky"
        plugin_dir = hook_src / ".claude-plugin"
        plugin_dir.mkdir(parents=True)
        (plugin_dir / "marketplace.json").write_text(
            json.dumps({
                "name": "hm",
                "plugins": [{"name": "hp", "source": "./"}],
            }),
            encoding="utf-8",
        )
        (hook_src / "hooks").mkdir()
        (self.home_dir / "sources.yaml").write_text(
            yaml.safe_dump({"sources": {"hooky": {"path": str(hook_src)}}}),
            encoding="utf-8",
        )

        answers = [["claude"], ["p"], ["beta"], ["hooky"]]
        with (
            patch("sys.stdin.isatty", return_value=True),
            patch("agal.cli._select_items_cli", side_effect=lambda *a, **k: answers.pop(0)),
            patch("builtins.input", return_value=""),
        ):
            out = self._run(["start"])

        self.assertIn("Step 4 of 6", out)
        settings = json.loads(
            (self.proj_dir / ".claude" / "settings.local.json").read_text(encoding="utf-8")
        )
        self.assertEqual(settings["enabledPlugins"], {"hp@hm": True})
        state = json.loads((self.proj_dir / ".agal_state.json").read_text(encoding="utf-8"))
        self.assertEqual(
            state["hooks"]["hooky"]["adapters"]["claude"],
            {"marketplace": "hm", "plugin": "hp"},
        )

    def test_start_reconciles_agal_items_and_keeps_manual_ones(self):
        for name in ("s3", "s4"):
            (self.skills_dir / name).mkdir()
            (self.skills_dir / name / "SKILL.md").write_text(
                f"---\nname: {name}\ndescription: Use when {name}.\n---\nBody\n",
                encoding="utf-8",
            )
        self._run(["add", "skill", "s3"])
        self._run(["add", "mcp", "m1"])

        manual_skill = self.proj_dir / ".agents" / "skills" / "manual"
        manual_skill.mkdir(parents=True)
        (manual_skill / "SKILL.md").write_text("---\nname: manual\n---\n", encoding="utf-8")
        mcp_path = self.proj_dir / ".mcp.json"
        mcp_data = json.loads(mcp_path.read_text(encoding="utf-8"))
        mcp_data["mcpServers"]["manual-mcp"] = {"command": "echo"}
        mcp_path.write_text(json.dumps(mcp_data), encoding="utf-8")

        servers = {
            "m1": MCP_FIXTURE["m1"],
            "m2": {"config": {"command": "echo"}, "source": "test"},
        }
        answers = [["claude"], ["p"], ["beta"], ["m2"], ["s4"]]
        with (
            patch("sys.stdin.isatty", return_value=True),
            patch("agal.cli.get_all_mcp_servers", return_value=servers),
            patch("agal.cli._select_items_cli", side_effect=lambda *a, **k: answers.pop(0)),
            patch("builtins.input", side_effect=["y", "y"]),
        ):
            self._run(["start"])

        state = json.loads((self.proj_dir / ".agal_state.json").read_text(encoding="utf-8"))
        self.assertNotIn("s3", state["skills"])
        self.assertIn("s4", state["skills"])
        self.assertNotIn("m1", state["mcp"])
        self.assertIn("m2", state["mcp"])
        self.assertNotIn("manual", state["skills"])
        self.assertTrue((manual_skill / "SKILL.md").is_file())
        mcp_data = json.loads(mcp_path.read_text(encoding="utf-8"))
        self.assertNotIn("m1", mcp_data["mcpServers"])
        self.assertIn("m2", mcp_data["mcpServers"])
        self.assertIn("manual-mcp", mcp_data["mcpServers"])

    def test_start_removes_unselected_subagent_and_its_unused_deps(self):
        self._run(["subagent", "add", "alpha"])
        self.assertTrue((self.proj_dir / ".claude" / "agents" / "alpha.md").is_file())

        answers = [["claude"], ["p"], ["beta"]]
        with (
            patch("sys.stdin.isatty", return_value=True),
            patch("agal.cli._select_items_cli", side_effect=lambda *a, **k: answers.pop(0)),
            patch("builtins.input", return_value="y"),
        ):
            self._run(["start"])

        state = json.loads((self.proj_dir / ".agal_state.json").read_text(encoding="utf-8"))
        self.assertEqual(list(state.get("subagents", {})), ["beta"])
        self.assertFalse((self.proj_dir / ".claude" / "agents" / "alpha.md").exists())
        self.assertTrue((self.proj_dir / ".claude" / "agents" / "beta.md").is_file())
        self.assertNotIn("m1", state.get("mcp", {}))

    def test_start_skips_every_step_on_empty_selection(self):
        with (
            patch("sys.stdin.isatty", return_value=True),
            patch("agal.cli._select_items_cli", return_value=[]),
            patch("builtins.input", return_value=""),
        ):
            self._run(["start"])
        self.assertEqual(_files(self.proj_dir), [])

    def test_skill_picker_filters_by_name_and_description(self):
        offered = []

        def pick(items, *args, **kwargs):
            offered.append(list(items))
            return []

        with (
            patch("sys.stdin.isatty", return_value=True),
            patch("builtins.input", side_effect=["nothing-matches", "WHEN s2"]),
            patch("agal.cli._select_items_cli", side_effect=pick),
        ):
            out = self._run(["add", "skill"])
        self.assertIn("No skills match 'nothing-matches'", out)
        self.assertEqual(offered, [["s2"]])

    def test_start_prints_help_when_not_a_tty(self):
        with patch("sys.stdin.isatty", return_value=False):
            self.assertIn("usage", self._run(["start"]))

    def test_launcher_option_one_runs_start(self):
        with (
            patch("sys.stdin.isatty", return_value=True),
            patch("builtins.input", return_value="1"),
            patch("agal.cli._start_wizard") as wizard,
        ):
            self._run([])
        wizard.assert_called_once()

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
        self.assertFalse((self.proj_dir / "GEMINI.md").exists())
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

    def test_prepare_adds_adhd_rules_only_when_configured(self):
        cfg_path = self.home_dir / "config.yaml"
        cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
        Path(cfg["context_file"]).write_text("# guidelines\n", encoding="utf-8")
        self._run(["prepare", "p"])
        self.assertNotIn("Reader has ADHD.", (self.proj_dir / "AGENTS.md").read_text(encoding="utf-8"))
        cfg["adhd_rules"] = True
        cfg_path.write_text(yaml.safe_dump(cfg), encoding="utf-8")
        self._run(["prepare", "p"])
        agents = (self.proj_dir / "AGENTS.md").read_text(encoding="utf-8")
        self.assertEqual(agents.count("Reader has ADHD."), 1)

    def test_refresh_recopies_installed_skills_from_source(self):
        self._run(["prepare", "p"])
        self._run(["subagent", "add", "beta"])
        for s in ["s1", "s2"]:
            (self.skills_dir / s / "SKILL.md").write_text(
                f"---\nname: {s}\ndescription: Use when {s}.\n---\nUpdated\n", encoding="utf-8"
            )
        out = self._run(["refresh"])
        self.assertIn("Refreshed", out)
        for s in ["s1", "s2"]:
            copied = (self.proj_dir / ".claude" / "skills" / s / "SKILL.md").read_text(encoding="utf-8")
            self.assertIn("Updated", copied)
        state = json.loads((self.proj_dir / ".agal_state.json").read_text(encoding="utf-8"))
        self.assertEqual(state.get("preset"), "p")
        self.assertIn("beta", state.get("subagents", {}))

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
