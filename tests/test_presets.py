from pathlib import Path
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
