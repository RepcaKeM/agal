from pathlib import Path
import json
import tempfile
import unittest
from unittest.mock import patch
import yaml

from agal.presets import (
    load_preset,
    save_preset,
    resolve_preset,
    list_presets,
    delete_preset,
    edit_preset,
    install_preset,
    uninstall_preset,
    _select_items_cli,
    create_preset_interactive,
)


class TestPresets(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.presets_dir = Path(self.td.name) / "presets"
        self.presets_dir.mkdir()
        self.target_dir = Path(self.td.name) / "project"
        self.target_dir.mkdir()

        self.cfg = {
            "presets_dir": str(self.presets_dir),
            "core_preset": "core",
            "sources_dir": str(Path(self.td.name) / "sources"),
        }

        # Create core preset
        core_file = self.presets_dir / "core.yaml"
        with open(core_file, "w", encoding="utf-8") as f:
            yaml.safe_dump({
                "name": "core",
                "description": "Core workflow",
                "skills": ["brainstorming", "planning"],
                "mcp": ["core-mcp"],
            }, f)

        # Create custom preset
        custom_file = self.presets_dir / "backend.yaml"
        with open(custom_file, "w", encoding="utf-8") as f:
            yaml.safe_dump({
                "name": "backend",
                "description": "Backend dev",
                "skills": ["database-optimizer", "planning"],  # planning duplicate
                "mcp": ["postgres"],
            }, f)

    def tearDown(self):
        self.td.cleanup()

    def test_load_preset(self):
        p = load_preset("backend", cfg=self.cfg)
        self.assertEqual(p["name"], "backend")
        self.assertIn("database-optimizer", p["skills"])

    def test_resolve_preset_with_core(self):
        resolved = resolve_preset("backend", cfg=self.cfg)
        self.assertEqual(resolved["name"], "backend")
        # Check core skills prepended and deduplicated
        self.assertEqual(resolved["skills"], ["brainstorming", "planning", "database-optimizer"])
        # Check core MCP prepended
        self.assertEqual(resolved["mcp"], ["core-mcp", "postgres"])

    def test_save_and_list_presets(self):
        save_preset("frontend", "Frontend dev", ["react"], ["figma"], cfg=self.cfg)
        presets = list_presets(cfg=self.cfg)
        names = [p["name"] for p in presets]
        self.assertIn("frontend", names)
        self.assertIn("backend", names)
        self.assertIn("core", names)

    @patch("agal.presets.get_all_skills")
    @patch("agal.presets.get_all_mcp_servers")
    @patch("agal.skills.get_all_skills")
    @patch("agal.mcp.get_all_mcp_servers")
    def test_install_and_uninstall_preset(self, mock_mcp_direct, mock_skills_direct, mock_mcp, mock_skills):
        skill_dir = Path(self.td.name) / "mock_skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("---\nname: brainstorming\n---\n", encoding="utf-8")

        mock_data_skills = {
            "brainstorming": {"name": "brainstorming", "path": str(skill_dir), "source": "src"},
            "planning": {"name": "planning", "path": str(skill_dir), "source": "src"},
            "database-optimizer": {"name": "database-optimizer", "path": str(skill_dir), "source": "src"},
        }
        mock_data_mcp = {
            "core-mcp": {"name": "core-mcp", "config": {"command": "echo"}},
            "postgres": {"name": "postgres", "config": {"command": "echo"}},
        }
        mock_skills.return_value = mock_data_skills
        mock_skills_direct.return_value = mock_data_skills
        mock_mcp.return_value = mock_data_mcp
        mock_mcp_direct.return_value = mock_data_mcp

        res = install_preset("backend", target_dir=self.target_dir, scope="local", cfg=self.cfg)
        self.assertEqual(res["preset"], "backend")
        self.assertTrue((self.target_dir / ".mcp.json").exists())
        self.assertTrue((self.target_dir / ".agents" / "skills" / "brainstorming").exists())

        un_res = uninstall_preset(target_dir=self.target_dir, scope="local", cfg=self.cfg)
        self.assertIn("brainstorming", un_res["removed_skills"])
        self.assertIn("postgres", un_res["removed_mcp"])
        self.assertFalse((self.target_dir / ".agents" / "skills" / "brainstorming").exists())

    @patch("agal.presets.get_all_skills")
    @patch("agal.presets.get_all_mcp_servers")
    @patch("agal.skills.get_all_skills")
    @patch("agal.mcp.get_all_mcp_servers")
    def test_install_preset_scans_skills_and_mcp_once(
        self, mock_mcp_direct, mock_skills_direct, mock_mcp, mock_skills
    ):
        skill_dir = Path(self.td.name) / "mock_skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("---\nname: brainstorming\n---\n", encoding="utf-8")

        mock_data_skills = {
            "brainstorming": {"name": "brainstorming", "path": str(skill_dir), "source": "src"},
            "planning": {"name": "planning", "path": str(skill_dir), "source": "src"},
            "database-optimizer": {"name": "database-optimizer", "path": str(skill_dir), "source": "src"},
        }
        mock_data_mcp = {
            "core-mcp": {"name": "core-mcp", "config": {"command": "echo"}},
            "postgres": {"name": "postgres", "config": {"command": "echo"}},
        }
        mock_skills.return_value = mock_data_skills
        mock_skills_direct.return_value = mock_data_skills
        mock_mcp.return_value = mock_data_mcp
        mock_mcp_direct.return_value = mock_data_mcp

        install_preset("backend", target_dir=self.target_dir, scope="local", cfg=self.cfg)

        self.assertEqual(mock_skills.call_count, 1)
        self.assertEqual(mock_skills_direct.call_count, 0)
        self.assertEqual(mock_mcp.call_count, 1)
        self.assertEqual(mock_mcp_direct.call_count, 0)

    @patch("agal.presets.get_all_skills")
    @patch("agal.presets.get_all_mcp_servers")
    @patch("agal.skills.get_all_skills")
    @patch("agal.mcp.get_all_mcp_servers")
    def test_prepare_replaces_previous_preset_and_keeps_manual_skill(
        self, mock_mcp_direct, mock_skills_direct, mock_mcp, mock_skills
    ):
        from agal.skills import install_skill, load_local_state

        skill_dir = Path(self.td.name) / "mock_skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("---\nname: s\ndescription: Use when s.\n---\n", encoding="utf-8")

        mock_data_skills = {
            name: {"name": name, "path": str(skill_dir), "source": "src"}
            for name in ("brainstorming", "planning", "database-optimizer", "react", "manual-one")
        }
        mock_data_mcp = {
            "core-mcp": {"name": "core-mcp", "config": {"command": "echo"}},
            "postgres": {"name": "postgres", "config": {"command": "echo"}},
            "figma": {"name": "figma", "config": {"command": "echo"}},
        }
        mock_skills.return_value = mock_data_skills
        mock_skills_direct.return_value = mock_data_skills
        mock_mcp.return_value = mock_data_mcp
        mock_mcp_direct.return_value = mock_data_mcp

        save_preset("frontend", "Frontend dev", ["react"], ["figma"], cfg=self.cfg)

        install_skill("manual-one", target_dir=self.target_dir, scope="local", cfg=self.cfg)
        install_preset("backend", target_dir=self.target_dir, scope="local", cfg=self.cfg)
        self.assertTrue((self.target_dir / ".agents" / "skills" / "database-optimizer").exists())

        install_preset("frontend", target_dir=self.target_dir, scope="local", cfg=self.cfg)

        state = load_local_state(self.target_dir)
        self.assertEqual(state["preset"], "frontend")
        self.assertNotIn("database-optimizer", state["skills"])
        self.assertFalse((self.target_dir / ".agents" / "skills" / "database-optimizer").exists())
        self.assertIn("react", state["skills"])
        self.assertIn("manual-one", state["skills"])
        self.assertTrue((self.target_dir / ".agents" / "skills" / "manual-one").exists())
        self.assertNotIn("postgres", state["mcp"])
        self.assertIn("figma", state["mcp"])

    @patch("agal.presets.get_all_skills")
    @patch("agal.presets.get_all_mcp_servers")
    @patch("agal.skills.get_all_skills")
    @patch("agal.mcp.get_all_mcp_servers")
    def test_prepare_preserves_subagents_and_shared_subagent_deps(
        self, mock_mcp_direct, mock_skills_direct, mock_mcp, mock_skills
    ):
        from agal.skills import load_local_state
        from agal.subagents import install_subagent, remove_subagent

        skill_dir = Path(self.td.name) / "mock_skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("---\nname: s\ndescription: Use when s.\n---\n", encoding="utf-8")

        sub_dir = Path(self.td.name) / "subagents"
        (sub_dir / "db-agent").mkdir(parents=True)
        (sub_dir / "db-agent" / "AGENT.md").write_text(
            "---\nname: db-agent\ndescription: Use when db.\nskills: [database-optimizer, sub-only]\nmcp: [postgres]\n---\nBody\n",
            encoding="utf-8",
        )
        cfg = {**self.cfg, "subagents_dir": str(sub_dir), "core_preset": None}
        save_preset("frontend", "Frontend dev", ["react"], ["figma"], cfg=cfg)

        mock_data_skills = {
            name: {"name": name, "path": str(skill_dir), "source": "src"}
            for name in ("database-optimizer", "planning", "react", "sub-only")
        }
        mock_data_mcp = {
            "postgres": {"name": "postgres", "config": {"command": "echo"}},
            "figma": {"name": "figma", "config": {"command": "echo"}},
        }
        mock_skills.return_value = mock_data_skills
        mock_skills_direct.return_value = mock_data_skills
        mock_mcp.return_value = mock_data_mcp
        mock_mcp_direct.return_value = mock_data_mcp

        install_preset("backend", target_dir=self.target_dir, scope="local", cfg=cfg)
        install_subagent("db-agent", target_dir=self.target_dir, cfg=cfg)
        install_preset("frontend", target_dir=self.target_dir, scope="local", cfg=cfg)

        state = load_local_state(self.target_dir)
        self.assertEqual(state["preset"], "frontend")
        self.assertIn("db-agent", state["subagents"])
        self.assertTrue((self.target_dir / ".claude" / "agents" / "db-agent.md").is_file())
        self.assertNotIn("planning", state["skills"])
        self.assertIn("database-optimizer", state["skills"])
        self.assertIn("sub-only", state["skills"])
        self.assertIn("react", state["skills"])
        self.assertIn("postgres", state["mcp"])
        self.assertIn("figma", state["mcp"])

        remove_subagent("db-agent", target_dir=self.target_dir, cfg=cfg)
        state_after = load_local_state(self.target_dir)
        self.assertNotIn("database-optimizer", state_after["skills"])
        self.assertNotIn("sub-only", state_after["skills"])
        self.assertIn("react", state_after["skills"])
        self.assertNotIn("postgres", state_after["mcp"])
        self.assertIn("figma", state_after["mcp"])

    @patch("agal.presets.get_all_skills")
    @patch("agal.presets.get_all_mcp_servers")
    @patch("agal.skills.get_all_skills")
    @patch("agal.mcp.get_all_mcp_servers")
    def test_prepare_same_preset_twice_and_failed_preset_preserves_state(
        self, mock_mcp_direct, mock_skills_direct, mock_mcp, mock_skills
    ):
        from agal.skills import load_local_state

        skill_dir = Path(self.td.name) / "mock_skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("---\nname: s\ndescription: Use when s.\n---\n", encoding="utf-8")

        mock_data_skills = {
            name: {"name": name, "path": str(skill_dir), "source": "src"}
            for name in ("brainstorming", "planning", "database-optimizer")
        }
        mock_data_mcp = {
            "core-mcp": {"name": "core-mcp", "config": {"command": "echo"}},
            "postgres": {"name": "postgres", "config": {"command": "echo"}},
        }
        mock_skills.return_value = mock_data_skills
        mock_skills_direct.return_value = mock_data_skills
        mock_mcp.return_value = mock_data_mcp
        mock_mcp_direct.return_value = mock_data_mcp

        install_preset("backend", target_dir=self.target_dir, scope="local", cfg=self.cfg)
        install_preset("backend", target_dir=self.target_dir, scope="local", cfg=self.cfg)

        state = load_local_state(self.target_dir)
        self.assertEqual(
            sorted(state["preset_owned"]["skills"]),
            ["brainstorming", "database-optimizer", "planning"],
        )
        self.assertEqual(sorted(state["preset_owned"]["mcp"]), ["core-mcp", "postgres"])

        with self.assertRaises(FileNotFoundError):
            install_preset("does-not-exist", target_dir=self.target_dir, scope="local", cfg=self.cfg)

        state_after = load_local_state(self.target_dir)
        self.assertEqual(state_after["preset"], "backend")
        self.assertTrue((self.target_dir / ".agents" / "skills" / "database-optimizer").exists())

    @patch("agal.presets.get_all_skills")
    @patch("agal.presets.get_all_mcp_servers")
    @patch("agal.skills.get_all_skills")
    @patch("agal.mcp.get_all_mcp_servers")
    def test_prepare_keeps_manual_items_when_previous_preset_is_gone(
        self, mock_mcp_direct, mock_skills_direct, mock_mcp, mock_skills
    ):
        from agal.mcp import install_mcp
        from agal.skills import install_skill, load_local_state, save_local_state

        skill_dir = Path(self.td.name) / "mock_skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("---\nname: s\ndescription: Use when s.\n---\n", encoding="utf-8")

        mock_data_skills = {
            name: {"name": name, "path": str(skill_dir), "source": "src"}
            for name in ("manual-one", "old-skill", "brainstorming")
        }
        mock_data_mcp = {
            name: {"name": name, "config": {"command": "echo"}}
            for name in ("manual-mcp", "old-mcp", "figma")
        }
        mock_skills.return_value = mock_data_skills
        mock_skills_direct.return_value = mock_data_skills
        mock_mcp.return_value = mock_data_mcp
        mock_mcp_direct.return_value = mock_data_mcp

        cfg = {**self.cfg, "core_preset": None}
        save_preset("fresh", "Fresh", ["brainstorming"], ["figma"], cfg=cfg)
        install_skill("manual-one", target_dir=self.target_dir, scope="local", cfg=cfg)
        install_skill("old-skill", target_dir=self.target_dir, scope="local", cfg=cfg)
        install_mcp("manual-mcp", target_dir=self.target_dir, scope="local", cfg=cfg)
        install_mcp("old-mcp", target_dir=self.target_dir, scope="local", cfg=cfg)
        state = load_local_state(self.target_dir)
        state["preset"] = "overallgood"
        state.pop("preset_owned", None)
        save_local_state(self.target_dir, state)

        install_preset("fresh", target_dir=self.target_dir, scope="local", cfg=cfg)

        state = load_local_state(self.target_dir)
        self.assertEqual(state["preset"], "fresh")
        for name in ("manual-one", "old-skill", "brainstorming"):
            self.assertIn(name, state["skills"])
            self.assertTrue((self.target_dir / ".agents" / "skills" / name).is_dir())
        for name in ("manual-mcp", "old-mcp", "figma"):
            self.assertIn(name, state["mcp"])
        self.assertEqual(state["preset_owned"]["skills"], ["brainstorming"])
        self.assertEqual(state["preset_owned"]["mcp"], ["figma"])
        self.assertNotIn("manual-one", state["preset_owned"]["skills"])
        self.assertNotIn("old-mcp", state["preset_owned"]["mcp"])

    def test_preset_hooks_install_and_uninstall_selected_adapters(self):
        from agal.skills import load_local_state, save_local_state

        src = Path(self.td.name) / "sources" / "fixture-src"
        src.mkdir(parents=True)
        plugin_dir = src / ".claude-plugin"
        plugin_dir.mkdir()
        (plugin_dir / "marketplace.json").write_text(
            json.dumps({
                "name": "fixture-market",
                "plugins": [{"name": "fixture-plugin", "source": "./"}],
            }),
            encoding="utf-8",
        )
        (src / "hooks").mkdir()
        entry = src / ".opencode" / "plugins" / "index.js"
        entry.parent.mkdir(parents=True)
        entry.write_text("export default {}\n", encoding="utf-8")
        bundle = {
            "name": "fixture-src",
            "path": str(src),
            "source": "fixture-src",
            "adapters": {
                "claude": {"marketplace": "fixture-market", "plugin": "fixture-plugin"},
                "opencode": str(entry.resolve()),
            },
        }

        cfg = {**self.cfg, "context_file": str(Path(self.td.name) / "none.md")}
        save_preset("hooky", "Hooks", [], [], hooks=["fixture-src"], cfg=cfg)
        save_local_state(self.target_dir, {"runtimes": ["claude", "opencode"]})
        with patch("agal.presets.get_all_skills", return_value={}), \
             patch("agal.presets.get_all_hooks", return_value={"fixture-src": bundle}):
            install_preset("hooky", target_dir=self.target_dir, scope="local", cfg=cfg)

        settings = json.loads(
            (self.target_dir / ".claude" / "settings.local.json").read_text(encoding="utf-8")
        )
        self.assertEqual(settings["enabledPlugins"], {"fixture-plugin@fixture-market": True})
        self.assertTrue(
            (self.target_dir / ".opencode" / "plugins" / "agal-fixture-src.js").is_file()
        )

        with patch("agal.presets.get_all_skills", return_value={}), \
             patch("agal.presets.get_all_hooks", return_value={"fixture-src": bundle}):
            uninstall_preset(target_dir=self.target_dir, scope="local", cfg=cfg)

        self.assertFalse((self.target_dir / ".claude" / "settings.local.json").exists())
        self.assertFalse(
            (self.target_dir / ".opencode" / "plugins" / "agal-fixture-src.js").exists()
        )
        self.assertEqual(load_local_state(self.target_dir).get("hooks", {}), {})

    @patch("sys.stdout")
    @patch("builtins.input", side_effect=["1, 3"])
    def test_select_items_cli_with_labels(self, mock_input, mock_stdout):
        items = ["skill-a", "skill-b", "skill-c"]
        labels = [
            "skill-a      [source1]  Desc A",
            "skill-b      [source2]  Desc B",
            "skill-c      [source1]  Desc C",
        ]
        selected = _select_items_cli(items, "Select items", display_labels=labels)
        self.assertEqual(selected, ["skill-a", "skill-c"])

    @patch("sys.stdout")
    @patch("agal.presets.get_all_skills")
    @patch("agal.presets.get_all_mcp_servers")
    @patch("builtins.input", side_effect=["Test description", "1", "1"])
    def test_create_preset_interactive(self, mock_input, mock_mcp, mock_skills, mock_stdout):
        mock_skills.return_value = {
            "my-skill": {"name": "my-skill", "source": "src1", "description": "Skill description"},
        }
        mock_mcp.return_value = {
            "my-mcp": {"name": "my-mcp", "source": "src2", "config": {"command": "cmd"}},
        }
        path = create_preset_interactive("interactive-test", cfg=self.cfg)
        self.assertTrue(path.exists())
        loaded = load_preset("interactive-test", cfg=self.cfg)
        self.assertEqual(loaded["description"], "Test description")
        self.assertEqual(loaded["skills"], ["my-skill"])
        self.assertEqual(loaded["mcp"], ["my-mcp"])

    def test_delete_preset(self):
        # Create a preset to delete
        save_preset("to-delete", "Will be deleted", ["skill"], cfg=self.cfg)
        self.assertTrue((self.presets_dir / "to-delete.yaml").exists())
        self.assertTrue(delete_preset("to-delete", cfg=self.cfg))
        self.assertFalse((self.presets_dir / "to-delete.yaml").exists())
        # Deleting non-existent preset returns False
        self.assertFalse(delete_preset("non-existent", cfg=self.cfg))

    @patch("subprocess.run")
    def test_edit_preset(self, mock_subproc):
        save_preset("to-edit", "Will be edited", ["skill1"], cfg=self.cfg)
        path = edit_preset("to-edit", cfg=self.cfg)
        self.assertEqual(path, self.presets_dir / "to-edit.yaml")
        mock_subproc.assert_called_once()

        with self.assertRaises(FileNotFoundError):
            edit_preset("non-existent", cfg=self.cfg)


if __name__ == "__main__":
    unittest.main()
