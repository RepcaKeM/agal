from pathlib import Path
import unittest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
STARTERS = ["researcher", "auditor", "ui-specialist"]


class TestStarterSubagents(unittest.TestCase):
    def test_starter_subagents_exist_and_valid(self):
        for name in STARTERS:
            with self.subTest(name=name):
                f = REPO_ROOT / "Subagents" / name / "AGENT.md"
                self.assertTrue(f.is_file(), f"Missing {f}")
                text = f.read_text(encoding="utf-8")
                self.assertTrue(text.startswith("---\n"))
                _, fm_text, body = text.split("---", 2)
                fm = yaml.safe_load(fm_text)
                self.assertEqual(fm["name"], name)
                self.assertIn("Use when", fm["description"])
                self.assertIn(fm.get("model", "inherit"), {"inherit", "sonnet", "opus", "haiku"})
                self.assertEqual(set(fm["permissions"]), {"edit_files", "run_commands"})
                self.assertIsInstance(fm["skills"], list)
                self.assertIsInstance(fm["mcp"], list)
                self.assertTrue(body.strip())
