from pathlib import Path
import io
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch
import yaml

from agal.config import LOCAL_STATE_FILE
from agal.presets import install_preset, uninstall_preset
from agal.skills import install_skill, load_local_state
from agal.subagents import (
    ADAPTER_PATHS,
    install_subagent,
    list_subagents,
    load_subagent,
    materialize_adapters,
    remove_subagent,
    render_adapters,
    save_subagent_template,
    unmaterialize_adapters,
    unprepare_all_subagents,
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


MCP_FIXTURE = {"m1": {"config": {"command": "echo"}, "source": "test"}}


def _files(root):
    return sorted(str(p.relative_to(root)) for p in root.rglob("*") if p.is_file() or p.is_symlink())


class TestLifecycle(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        root = Path(self.td.name)
        self.target = root / "project"
        self.target.mkdir()
        skills_dir, sub_dir, presets_dir = root / "skills", root / "subagents", root / "presets"
        for s in ["s1", "s2"]:
            (skills_dir / s).mkdir(parents=True)
            (skills_dir / s / "SKILL.md").write_text(
                f"---\nname: {s}\ndescription: Use when {s}.\n---\nBody\n", encoding="utf-8")
        defs = {
            "alpha": "skills: [s1, s2]\nmcp: [m1]\n",
            "beta": "skills: [s2]\n",
            "ghost": "skills: [missing-skill]\nmcp: [missing-mcp]\n",
            "solo": "",
        }
        for n, extra in defs.items():
            (sub_dir / n).mkdir(parents=True)
            (sub_dir / n / "AGENT.md").write_text(
                f"---\nname: {n}\ndescription: Use when {n}.\n{extra}---\nBody\n", encoding="utf-8")
        presets_dir.mkdir()
        (presets_dir / "p.yaml").write_text("name: p\nskills: [s1]\n", encoding="utf-8")
        self.cfg = {
            "skills_dir": str(skills_dir), "subagents_dir": str(sub_dir),
            "presets_dir": str(presets_dir), "sources_dir": str(root / "sources"),
            "context_file": str(root / "no-context.md"), "core_preset": None,
        }
        self._patches = [
            patch.dict(os.environ, {"AGAL_HOME": str(root / "home")}),
            patch("agal.mcp.get_all_mcp_servers", return_value=MCP_FIXTURE),
            patch("sys.stdout", new_callable=io.StringIO),
        ]
        for p in self._patches:
            p.start()

    def tearDown(self):
        for p in reversed(self._patches):
            p.stop()
        self.td.cleanup()

    def _install(self, n):
        return install_subagent(n, target_dir=self.target, cfg=self.cfg)

    def _remove(self, n):
        return remove_subagent(n, target_dir=self.target, cfg=self.cfg)

    def _has_skill(self, s):
        return (self.target / ".claude" / "skills" / s).exists()

    def test_install_records_state_and_deps(self):
        res = self._install("alpha")
        self.assertEqual(res["missing"], [])
        state = load_local_state(self.target)
        self.assertEqual(state["subagents"]["alpha"]["skills"], ["s1", "s2"])
        self.assertEqual(state["subagents"]["alpha"]["mcp"], ["m1"])
        self.assertEqual(len(state["subagents"]["alpha"]["files"]), 4)
        self.assertEqual(sorted(state["subagent_owned"]["skills"]), ["s1", "s2"])
        self.assertTrue(self._has_skill("s1"))
        self.assertIn("m1", json.loads((self.target / ".mcp.json").read_text())["mcpServers"])

    def test_reinstall_idempotent(self):
        self._install("alpha")
        self._install("alpha")
        self.assertEqual(len(load_local_state(self.target)["subagents"]["alpha"]["files"]), 4)

    def test_subagent_without_deps_persists_state(self):
        self._install("solo")
        self.assertIn("solo", load_local_state(self.target)["subagents"])

    def test_remove_last_ref_leaves_nothing(self):
        self._install("alpha")
        self._remove("alpha")
        self.assertEqual(_files(self.target), [])

    def test_shared_dep_kept_for_other_subagent(self):  # Review Focus 2
        self._install("alpha")
        self._install("beta")
        self._remove("alpha")
        self.assertFalse(self._has_skill("s1"))
        self.assertTrue(self._has_skill("s2"))
        self._remove("beta")
        self.assertEqual(_files(self.target), [])

    def test_dep_kept_for_active_preset_installed_after(self):  # Review Focus 2
        self._install("alpha")
        install_preset("p", target_dir=self.target, cfg=self.cfg)
        self._remove("alpha")
        self.assertTrue(self._has_skill("s1"))
        self.assertFalse(self._has_skill("s2"))

    def test_dep_kept_for_active_preset_installed_before(self):  # Review Focus 2
        install_preset("p", target_dir=self.target, cfg=self.cfg)
        self._install("alpha")
        self._remove("alpha")
        self.assertTrue(self._has_skill("s1"))

    def test_preexisting_manual_skill_not_removed(self):  # Review Focus 2
        install_skill("s1", target_dir=self.target, cfg=self.cfg)
        self._install("alpha")
        self._remove("alpha")
        self.assertTrue(self._has_skill("s1"))

    def test_missing_deps_warn_and_continue(self):  # Review Focus 3
        res = self._install("ghost")
        self.assertEqual(sorted(res["missing"]), ["missing-mcp", "missing-skill"])
        out = sys.stdout.getvalue()
        self.assertIn("missing-skill", out)
        self.assertIn("missing-mcp", out)
        self.assertTrue((self.target / ".claude" / "agents" / "ghost.md").is_file())

    def test_remove_not_installed(self):  # Review Focus 4
        self.assertEqual(self._remove("alpha"), {"removed": False, "skills": [], "mcp": []})
        self.assertFalse((self.target / LOCAL_STATE_FILE).exists())
        self._install("beta")
        before = load_local_state(self.target)
        self._remove("alpha")
        self.assertEqual(load_local_state(self.target), before)

    def test_unprepare_only_subagents_leaves_nothing(self):  # Review Focus 5
        self._install("alpha")
        self._install("beta")
        self.assertEqual(sorted(unprepare_all_subagents(target_dir=self.target, cfg=self.cfg)), ["alpha", "beta"])
        uninstall_preset(target_dir=self.target, cfg=self.cfg)
        self.assertEqual(_files(self.target), [])



