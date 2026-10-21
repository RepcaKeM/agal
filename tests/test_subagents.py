from pathlib import Path
import io
import tempfile
import unittest
from unittest.mock import patch
import yaml

from agal.subagents import list_subagents, load_subagent, save_subagent_template

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


class TestSubagentParsing(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.sub_dir = Path(self.td.name) / "subagents"
        self.cfg = {"subagents_dir": str(self.sub_dir)}

    def tearDown(self):
        self.td.cleanup()

    def _write(self, name, text):
        d = self.sub_dir / name
        d.mkdir(parents=True)
        (d / "AGENT.md").write_text(text, encoding="utf-8")

    def test_load_bundled_researcher(self):
        cfg = {"subagents_dir": str(REPO_ROOT / "Subagents")}
        self.assertTrue(set(STARTERS) <= set(list_subagents(cfg)))
        r = load_subagent("researcher", cfg)
        self.assertEqual(r["model"], "inherit")
        self.assertEqual(r["permissions"], {"edit_files": False, "run_commands": True})
        self.assertIn("context7-docs", r["skills"])
        self.assertTrue(r["system_prompt"].startswith("You are a dedicated research subagent."))

    def test_defaults_applied(self):
        self._write("mini", "---\nname: mini\ndescription: Use when testing.\n---\nBody\n")
        a = load_subagent("mini", self.cfg)
        self.assertEqual(a["model"], "inherit")
        self.assertEqual(a["permissions"], {"edit_files": True, "run_commands": True})
        self.assertEqual((a["skills"], a["mcp"]), ([], []))

    def test_missing_raises_file_not_found(self):
        with self.assertRaises(FileNotFoundError):
            load_subagent("nope", self.cfg)

    def test_malformed_raises_value_error(self):  # Review Focus 1
        cases = {
            "nofm": "Just body\n",
            "badyaml": "---\nname: [unclosed\n---\nBody\n",
            "notdict": "---\n- a\n- b\n---\nBody\n",
            "nodesc": "---\nname: nodesc\n---\nBody\n",
            "badmodel": "---\nname: badmodel\ndescription: x\nmodel: fast\n---\nBody\n",
            "mismatch": "---\nname: other\ndescription: x\n---\nBody\n",
            "badskills": "---\nname: badskills\ndescription: x\nskills: s1\n---\nBody\n",
        }
        for name, text in cases.items():
            self._write(name, text)
            with self.subTest(name=name):
                with self.assertRaises(ValueError) as cm:
                    load_subagent(name, self.cfg)
                self.assertIn("AGENT.md", str(cm.exception))

    def test_list_skips_invalid(self):  # Review Focus 1
        self._write("good", "---\nname: good\ndescription: Use when ok.\n---\nBody\n")
        self._write("bad", "no frontmatter\n")
        out = io.StringIO()
        with patch("sys.stdout", out):
            agents = list_subagents(self.cfg)
        self.assertEqual(list(agents), ["good"])
        self.assertIn("bad", out.getvalue())

    def test_save_template_roundtrip(self):
        save_subagent_template("newbie", self.cfg)
        self.assertEqual(load_subagent("newbie", self.cfg)["name"], "newbie")
        with self.assertRaises(FileExistsError):
            save_subagent_template("newbie", self.cfg)

