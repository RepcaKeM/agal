from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from agal.skills import (
    install_skill,
    uninstall_skill,
    list_installed_skills,
    load_local_state,
)


class TestSkills(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.target_dir = Path(self.td.name) / "project"
        self.target_dir.mkdir()

        self.skill_source_dir = Path(self.td.name) / "source" / "skills" / "my-skill"
        self.skill_source_dir.mkdir(parents=True)
        (self.skill_source_dir / "SKILL.md").write_text(
            "---\nname: my-skill\ndescription: Test skill.\n---\n# Body",
            encoding="utf-8",
        )
        (self.skill_source_dir / "script.sh").write_text("#!/bin/bash\necho 42", encoding="utf-8")
        ref_dir = self.skill_source_dir / "references"
        ref_dir.mkdir()
        (ref_dir / "config.yaml").write_text("key: val", encoding="utf-8")

        self.mock_skills = {
            "my-skill": {
                "name": "my-skill",
                "path": str(self.skill_source_dir.resolve()),
                "source": "test-source",
                "description": "Test skill.",
            }
        }

    def tearDown(self):
        self.td.cleanup()

    @patch("agal.skills.get_all_skills")
    def test_install_skill_local_symlink(self, mock_get_skills):
        mock_get_skills.return_value = self.mock_skills

        res = install_skill("my-skill", target_dir=self.target_dir, scope="local", copy=False)
        self.assertEqual(res["skill"], "my-skill")

        agents_skill = self.target_dir / ".agents" / "skills" / "my-skill"
        claude_skill = self.target_dir / ".claude" / "skills" / "my-skill"

        self.assertTrue(agents_skill.is_symlink())
        self.assertTrue(claude_skill.is_symlink())

        # Check auxiliary files preserved
        self.assertTrue((agents_skill / "script.sh").is_file())
        self.assertTrue((agents_skill / "references" / "config.yaml").is_file())

        # Check state tracking
        state = load_local_state(self.target_dir)
        self.assertIn("my-skill", state["skills"])

    @patch("agal.skills.get_all_skills")
    def test_install_skill_local_copy(self, mock_get_skills):
        mock_get_skills.return_value = self.mock_skills

        res = install_skill("my-skill", target_dir=self.target_dir, scope="local", copy=True)
        self.assertEqual(res["mode"], "copy")

        agents_skill = self.target_dir / ".agents" / "skills" / "my-skill"
        self.assertTrue(agents_skill.is_dir())
        self.assertFalse(agents_skill.is_symlink())
        self.assertTrue((agents_skill / "script.sh").is_file())

    @patch("agal.skills.get_all_skills")
    def test_uninstall_skill_local(self, mock_get_skills):
        mock_get_skills.return_value = self.mock_skills

        install_skill("my-skill", target_dir=self.target_dir, scope="local")
        self.assertTrue((self.target_dir / ".agents" / "skills" / "my-skill").exists())

        uninstall_skill("my-skill", target_dir=self.target_dir, scope="local")
        self.assertFalse((self.target_dir / ".agents" / "skills" / "my-skill").exists())
        self.assertFalse((self.target_dir / ".claude" / "skills" / "my-skill").exists())

        installed = list_installed_skills(self.target_dir, scope="local")
        self.assertNotIn("my-skill", installed)


if __name__ == "__main__":
    unittest.main()
