import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from agal.hooks import install_hook, uninstall_hook
from agal.skills import load_local_state, load_global_state


class TestHooks(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.target_dir = Path(self.td.name) / "project"
        self.target_dir.mkdir()
        self.home_dir = Path(self.td.name) / "home"
        self.home_dir.mkdir()

        self.hook_src = Path(self.td.name) / "pre-tool.sh"
        self.hook_src.write_text("#!/bin/bash\necho hook\n", encoding="utf-8")
        self.hook_src.chmod(0o755)

        self.mock_hooks = {
            "pre-tool.sh": {
                "name": "pre-tool.sh",
                "path": str(self.hook_src),
                "source": "my-source",
                "executable": True,
            }
        }

    def tearDown(self):
        self.td.cleanup()

    @patch("agal.hooks.get_all_hooks")
    def test_install_and_uninstall_hook_local(self, mock_get_hooks):
        mock_get_hooks.return_value = self.mock_hooks

        # 1. Install hook locally
        res = install_hook("pre-tool.sh", target_dir=self.target_dir, scope="local")
        self.assertEqual(res["hook"], "pre-tool.sh")

        dest = self.target_dir / ".claude" / "hooks" / "pre-tool.sh"
        self.assertTrue(dest.is_file())
        self.assertTrue(os.access(dest, os.X_OK))

        state = load_local_state(self.target_dir)
        self.assertIn("pre-tool.sh", state.get("hooks", {}))

        # 2. Uninstall hook locally (returns True)
        self.assertTrue(uninstall_hook("pre-tool.sh", target_dir=self.target_dir, scope="local"))
        self.assertFalse(dest.exists())

        state_after = load_local_state(self.target_dir)
        self.assertNotIn("pre-tool.sh", state_after.get("hooks", {}))

        # 3. Uninstall again when already gone (returns False)
        self.assertFalse(uninstall_hook("pre-tool.sh", target_dir=self.target_dir, scope="local"))

    def test_uninstall_hook_file_exists_without_state(self):
        # File exists in .claude/hooks but is not in state
        hooks_dir = self.target_dir / ".claude" / "hooks"
        hooks_dir.mkdir(parents=True)
        dest = hooks_dir / "untracked-hook.sh"
        dest.write_text("#!/bin/bash\nexit 0\n")

        self.assertTrue(uninstall_hook("untracked-hook.sh", target_dir=self.target_dir, scope="local"))
        self.assertFalse(dest.exists())

    @patch("agal.hooks.get_all_hooks")
    def test_install_and_uninstall_hook_global(self, mock_get_hooks):
        mock_get_hooks.return_value = self.mock_hooks

        with patch("pathlib.Path.home", return_value=self.home_dir), \
             patch("agal.skills.get_installed_file", return_value=self.home_dir / "installed.yaml"):
            res = install_hook("pre-tool.sh", scope="global")
            self.assertEqual(res["scope"], "global")

            dest = self.home_dir / ".claude" / "hooks" / "pre-tool.sh"
            self.assertTrue(dest.is_file())

            self.assertTrue(uninstall_hook("pre-tool.sh", scope="global"))
            self.assertFalse(dest.exists())
            self.assertFalse(uninstall_hook("pre-tool.sh", scope="global"))


if __name__ == "__main__":
    unittest.main()
