from pathlib import Path
import io
import tempfile
import unittest
from unittest.mock import patch
import yaml

from agal.subagents import (
    ADAPTER_PATHS,
    list_subagents,
    load_subagent,
    materialize_adapters,
    render_adapters,
    save_subagent_template,
    unmaterialize_adapters,
)

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


AGENT = {
    "name": "rev", "description": "Use when reviewing.", "model": "inherit",
    "permissions": {"edit_files": False, "run_commands": True},
    "skills": ["s1"], "mcp": ["m1"], "system_prompt": "You review.",
}


def _split(text):
    _, fm, body = text.split("---", 2)
    return yaml.safe_load(fm), body.strip()


class TestAdapters(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.target = Path(self.td.name)
        self.rendered = render_adapters(AGENT)

    def tearDown(self):
        self.td.cleanup()

    def test_paths(self):
        self.assertEqual(sorted(self.rendered), sorted([
            ".claude/agents/rev.md", ".cursor/agents/rev.md",
            ".opencode/agents/rev.md", ".agents/agents/rev/agent.md",
        ]))
        self.assertEqual(sorted(ADAPTER_PATHS("rev")), sorted(self.rendered))

    def test_claude(self):
        fm, body = _split(self.rendered[".claude/agents/rev.md"])
        self.assertEqual(fm["name"], "rev")
        self.assertEqual(fm["model"], "inherit")
        self.assertEqual(fm["skills"], ["s1"])
        self.assertEqual(fm["mcpServers"], ["m1"])
        self.assertEqual(fm["disallowedTools"], ["Edit", "Write", "NotebookEdit"])
        self.assertNotIn("tools", fm)
        self.assertEqual(body, "You review.")

    def test_claude_model_passthrough_others_inherit(self):
        r = render_adapters({**AGENT, "model": "sonnet"})
        self.assertEqual(_split(r[".claude/agents/rev.md"])[0]["model"], "sonnet")
        self.assertEqual(_split(r[".cursor/agents/rev.md"])[0]["model"], "inherit")
        self.assertEqual(_split(r[".agents/agents/rev/agent.md"])[0]["model"], "inherit")
        self.assertNotIn("model", _split(r[".opencode/agents/rev.md"])[0])

    def test_cursor(self):
        fm, _ = _split(self.rendered[".cursor/agents/rev.md"])
        self.assertTrue(fm["readonly"])
        full = render_adapters({**AGENT, "permissions": {"edit_files": True, "run_commands": True}})
        self.assertNotIn("readonly", _split(full[".cursor/agents/rev.md"])[0])

    def test_opencode(self):
        fm, _ = _split(self.rendered[".opencode/agents/rev.md"])
        self.assertEqual(fm["mode"], "subagent")
        self.assertEqual(fm["permission"], {"edit": "deny", "bash": "allow"})
        self.assertNotIn("name", fm)

    def test_antigravity(self):
        fm, _ = _split(self.rendered[".agents/agents/rev/agent.md"])
        self.assertIs(fm["subagent"], True)
        self.assertIs(fm["mainAgent"], False)
        self.assertEqual(fm["skills"], ["skills/s1"])
        self.assertIn("run_command", fm["tools"])
        self.assertNotIn("replace_file_content", fm["tools"])

    def test_materialize_then_unmaterialize_leaves_nothing(self):
        files = materialize_adapters(AGENT, self.target)
        self.assertEqual(sorted(files), sorted(self.rendered))
        unmaterialize_adapters(files, self.target)
        self.assertEqual(list(self.target.iterdir()), [])

    def test_existing_user_file_not_clobbered(self):
        user = self.target / ".claude" / "agents" / "rev.md"
        user.parent.mkdir(parents=True)
        user.write_text("mine", encoding="utf-8")
        with patch("sys.stdout", io.StringIO()):
            files = materialize_adapters(AGENT, self.target)
        self.assertEqual(user.read_text(encoding="utf-8"), "mine")
        self.assertNotIn(".claude/agents/rev.md", files)

    def test_unmaterialize_keeps_non_empty_dirs(self):
        files = materialize_adapters(AGENT, self.target)
        other = self.target / ".claude" / "agents" / "other.md"
        other.write_text("x", encoding="utf-8")
        unmaterialize_adapters(files, self.target)
        self.assertTrue(other.is_file())
        self.assertFalse((self.target / ".cursor").exists())


