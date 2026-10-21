# Agal Subagents Architecture Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend `agal` with a subagent configuration engine that provisions specialized subagents and their dependencies locally for Claude Code, Antigravity (Agy), Cursor, and OpenCode, with full reference-counted teardown.

**Architecture:** A new module `agal/subagents.py` discovers and parses subagent definitions, writes one native agent file per runtime, and manages lifecycle. Dependencies (skills/MCP) are reference-counted in `.agal_state.json`. CLI exposes `agal subagent {add,remove,list,create}` and hooks subagent teardown into `agal --unprepare` / `agal unprepare` / `agal remove preset`.

**Tech Stack:** Python 3.10+, `argparse` CLI (existing `agal/cli.py`), `pyyaml` (only runtime dependency), `agal/ui.py` for output, `unittest` tests run under `pytest`. **No Click, no Rich.**

**Spec:** [docs/superpowers/specs/2026-10-21-subagents-design.md](../specs/2026-10-21-subagents-design.md)

## Global Constraints

- **Strict Local Isolation:** All configurations, symlinks, and adapter files must reside strictly within the target project root.
- **No Global Modifications:** No changes to global user configs (`~/.claude.json`, global cursor settings, user profile files). Never write through a symlink into a file outside the project.
- **No Clobbering:** An adapter path that already exists and is not tracked by agal is left untouched (warning printed, path not recorded).
- **Deterministic Teardown:** Every generated file is tracked in `.agal_state.json` and removed by `agal subagent remove` and `agal --unprepare`; adapter directories left empty by removal are pruned.
- **Python Architecture:** Follow existing patterns in `agal/presets.py`, `agal/skills.py`, `agal/cli.py`. Tests follow `tests/test_presets.py` / `tests/test_cli.py` style (`unittest.TestCase`, `tempfile`, explicit `cfg` dicts, `patch.dict("os.environ", {"AGAL_HOME": ...})`). Tests never touch the real `~/.agal` or depend on skills registered on the developer's machine.

## Runtime Formats (verified 2026-10-21 via Context7)

Every target runtime has **native** subagent files, so no routing block is injected into `AGENTS.md` / `GEMINI.md`.

| Runtime | Path | Frontmatter written by agal | Source |
|---|---|---|---|
| Claude Code | `.claude/agents/<name>.md` | `name`, `description`, `model` (`inherit\|sonnet\|opus\|haiku`), `skills` (names), `mcpServers` (names from `.mcp.json`), `disallowedTools` | Claude Code `AgentSpec` type |
| Cursor | `.cursor/agents/<name>.md` | `name`, `description`, `model: inherit`, `readonly` | cursor.com/docs/subagents |
| OpenCode | `.opencode/agents/<name>.md` (filename = agent name) | `description`, `mode: subagent`, `permission: {edit, bash}` (`tools` is deprecated) | opencode.ai/docs/agents |
| Antigravity | `.agents/agents/<name>/agent.md` | `name`, `description`, `subagent: true`, `mainAgent: false`, `model: inherit`, `skills` (`skills/<name>`), `tools` (only when a permission is false) | antigravity.google/docs/cli/subagents |

Notes:
- Cursor also reads `.claude/agents/`, but `.cursor/agents/` takes precedence on name clash; agal writes the Cursor file so `readonly` is honoured.
- Skills are already discovered by every runtime from the dirs `install_skill` writes (`.claude/skills/`, `.agents/skills/`; OpenCode reads both).
- MCP: agal writes project `.mcp.json` (Claude Code only), as presets already do. Cursor/OpenCode/Agy MCP config is out of scope; README states this.
- Model: only Claude accepts `sonnet|opus|haiku`; every other runtime always gets `inherit` (Agy tiers are `flash|pro`, OpenCode needs `provider/model`).

### Permission mapping

`permissions: {edit_files: bool, run_commands: bool}` (both default `true`):

| | `edit_files: false` | `run_commands: false` |
|---|---|---|
| Claude | `disallowedTools` += `Edit`, `Write`, `NotebookEdit` | `disallowedTools` += `Bash` |
| Cursor | `readonly: true` | `readonly: true` |
| OpenCode | `permission.edit: deny` | `permission.bash: deny` |
| Agy | `tools` whitelist without edit tools | `tools` whitelist without `run_command` |

Claude uses a deny-list, not a `tools:` whitelist, so Skill and MCP tools stay available without enumerating them.

## Spec Deltas (applied to the spec on 2026-10-21)

1. No `<!-- agal:subagents -->` block in `AGENTS.md`/`GEMINI.md`; Agy and Cursor get native agent files (`.agents/agents/`, `.cursor/agents/`) instead of the routing block / `.mdc` rule.
2. `trigger` field dropped: all four runtimes delegate on `description`, so it must contain the "Use when …" clause.
3. `model` restricted to `inherit|sonnet|opus|haiku` (spec listed `fast`, `high`, `claude-3-5-haiku`, which no runtime accepts portably).
4. Claude gets `disallowedTools`, not a `tools:` whitelist.
5. CLI is `agal subagent add [NAMES...]` (picker when empty) instead of `agal subagent [NAMES...]`: argparse cannot mix free positional names with subcommand names.
6. `create` scaffolds a template; no interactive wizard.
7. Only `Subagents/<name>/AGENT.md` is supported (not `Subagents/<name>.md`).
8. Reference counting uses `state["subagent_owned"]` instead of `installed_by` on each skill entry, so `install_skill`/`install_mcp` stay unchanged.
9. Subagents are read from `subagents_dir` (default `~/.agal/subagents`, symlinked by `install.sh` to repo `Subagents/`), mirroring presets.

## State Schema

```json
{
  "skills": {"...": "unchanged"},
  "mcp": {"...": "unchanged"},
  "hooks": {},
  "preset": null,
  "subagents": {
    "researcher": {
      "skills": ["context7-docs", "find-docs"],
      "mcp": ["context7"],
      "files": [".claude/agents/researcher.md", ".cursor/agents/researcher.md",
                ".opencode/agents/researcher.md", ".agents/agents/researcher/agent.md"]
    }
  },
  "subagent_owned": {"skills": ["find-docs"], "mcp": ["context7"]}
}
```

- `subagents[n].skills/mcp`: deps that are present for `n` (installed by it or already there). Missing deps are not listed.
- `subagent_owned`: deps that a subagent install **newly added**. Only owned deps are ever uninstalled by subagent removal, so skills added by hand (`agal add skill`) or by a preset installed earlier are never removed.
- Removal of owned dep `d` happens when no other subagent lists `d` and the active preset (`resolve_preset(state["preset"])`, including `core_preset`) does not list it. If `state["preset"]` is set but cannot be resolved, keep all deps (conservative).

## Review Focus → Tests

| # | Focus | Covered by |
|---|---|---|
| 1 | Malformed `AGENT.md` raises `ValueError` naming the file | `test_malformed_raises_value_error`, `test_list_skips_invalid` (Task 2) |
| 2 | Shared deps kept for another subagent / active preset / manual install | `test_shared_dep_kept_for_other_subagent`, `test_dep_kept_for_active_preset_*`, `test_preexisting_manual_skill_not_removed` (Task 4) |
| 3 | Missing deps warn and continue | `test_missing_deps_warn_and_continue` (Task 4), `test_cli_add_unknown_subagent` (Task 5) |
| 4 | Removing non-installed subagent is a clean no-op | `test_remove_not_installed` (Task 4) |
| 5 | `--unprepare` with only subagents leaves zero files | `test_unprepare_only_subagents_leaves_nothing` (Task 4), `test_cli_unprepare_only_subagents` (Task 5) |

---

### Task 1: Bundled Starter Subagents

**Files:**
- Create: `Subagents/researcher/AGENT.md`
- Create: `Subagents/auditor/AGENT.md`
- Create: `Subagents/ui-specialist/AGENT.md`
- Test: `tests/test_subagents.py`

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_subagents.py::TestStarterSubagents -v`
Expected: FAIL with `AssertionError: False is not true : Missing .../Subagents/researcher/AGENT.md`

- [ ] **Step 3: Create starter subagents**

| Name | `permissions` | `skills` | `mcp` | Body starts with |
|---|---|---|---|---|
| researcher | edit `false`, run `true` | `context7-docs`, `find-docs` | `context7` | `You are a dedicated research subagent.` |
| auditor | edit `false`, run `true` | `requesting-code-review`, `verification-before-completion` | — | `You are a dedicated code audit subagent.` |
| ui-specialist | edit `true`, run `true` | `a11y-debugging` | — | `You are a dedicated UI subagent.` |

All use `model: inherit`. Each `description` ends with a "Use when …" clause. `researcher` and `ui-specialist` depend on skills/MCP that are not bundled in `Skills/`; on machines without a source providing them, install warns per Review Focus 3. This is intended.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_subagents.py::TestStarterSubagents -v` → check: PASS

- [ ] **Step 5: Commit**

```bash
git add Subagents/ tests/test_subagents.py
git commit -m "feat(subagents): add starter subagent definitions"
```

---

### Task 2: Parser, Discovery, Template

**Files:**
- Create: `agal/subagents.py`
- Modify: `agal/config.py` (add `get_subagents_dir`, `subagents_dir` default in `load_config`)
- Modify: `install.sh` (link `$AGAL_HOME/subagents → $SRC_DIR/Subagents`, add `subagents_dir` to starter config)
- Test: `tests/test_subagents.py`

**Interfaces:**
- `get_subagents_dir(cfg: dict | None = None) -> Path`: `cfg["subagents_dir"]` else `get_agal_home() / "subagents"` (mirrors `get_presets_dir`).
- `load_subagent(name: str, cfg: dict | None = None) -> dict`: keys `name`, `description`, `model`, `permissions`, `skills`, `mcp`, `system_prompt`, `path`.
  - Missing `<dir>/<name>/AGENT.md` → `FileNotFoundError`.
  - No frontmatter, invalid YAML, frontmatter not a mapping, missing/empty `description`, `name` ≠ directory name, `model` not in `inherit|sonnet|opus|haiku`, or `skills`/`mcp` not lists → `ValueError` whose message contains the `AGENT.md` path.
  - Defaults: `model: inherit`, both permissions `true`, `skills: []`, `mcp: []`.
- `list_subagents(cfg: dict | None = None) -> dict[str, dict]`: sorted by name; an invalid definition prints `⚠️  Skipping subagent '<name>': <error>` and is skipped; a missing directory gives `{}`.
- `save_subagent_template(name: str, cfg: dict | None = None) -> Path`: writes a valid template; `FileExistsError` if it exists.

- [ ] **Step 1: Write failing tests**

```python
import io
import tempfile
from unittest.mock import patch

from agal.subagents import list_subagents, load_subagent, save_subagent_template


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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_subagents.py::TestSubagentParsing -v`
Expected: collection ERROR with `ModuleNotFoundError: No module named 'agal.subagents'`

- [ ] **Step 3: Implement** `get_subagents_dir` + `subagents_dir` in `load_config` (no `mkdir`; a missing dir means no subagents), the three functions in `agal/subagents.py`, and the `install.sh` link (same as `presets`, lines 60–63; add `subagents_dir: $AGAL_HOME/subagents` to the starter config heredoc).

- [ ] **Step 4: Verify**

Run: `pytest tests/test_subagents.py -v` → check: all PASS
Run: `bash -n install.sh` → check: no syntax error

- [ ] **Step 5: Commit**

```bash
git add agal/subagents.py agal/config.py install.sh tests/test_subagents.py
git commit -m "feat(subagents): parser, discovery and template scaffold"
```

---

### Task 3: Native Runtime Adapters

**Files:**
- Modify: `agal/subagents.py`
- Test: `tests/test_subagents.py`

No changes to `agal/context.py`, `AGENTS.md`, or `GEMINI.md`.

**Interfaces:**
- `ADAPTER_PATHS(name) -> list[str]`: the four relative paths from the Runtime Formats table.
- `render_adapters(agent: dict) -> dict[str, str]`: pure; maps each relative path to file content (YAML frontmatter via `yaml.safe_dump(..., sort_keys=False)` + `system_prompt` body). Empty lists/keys are omitted.
- `materialize_adapters(agent: dict, target_dir: Path) -> list[str]`: writes the rendered files; a path that already exists (file or symlink) is skipped with `⚠️  <path> exists and is not managed by agal (skipped).` and left out of the result. Returns the relative paths it wrote.
- `unmaterialize_adapters(files: list[str], target_dir: Path) -> None`: deletes the listed files, then removes each parent directory that is now empty, walking up but never removing `target_dir` itself.

- [ ] **Step 0: Verify Agy details (manual, before writing code)**

In a scratch project, create `.agents/agents/probe/agent.md` with `subagent: true`, `mainAgent: false`, `skills: [skills/<an installed skill>]`, and no `tools`. Open the Agy CLI agents view.
→ check: (a) `probe` is listed; (b) the skill resolves (confirms that `skills/<name>` is relative to `.agents/`); (c) the tool list Agy shows for `probe`. Record the real read-only tool names. They replace the provisional `AGY_READ_TOOLS = ["view_file", "grep_search"]` below. If (a) or (b) fails, stop and update the Runtime Formats table before continuing.

Agy `tools` (only when a permission is false) = `AGY_READ_TOOLS` + `["replace_file_content"]` if `edit_files` + `["run_command"]` if `run_commands`. Edit-tool names also come from Step 0.

- [ ] **Step 1: Write failing tests**

```python
from agal.subagents import ADAPTER_PATHS, materialize_adapters, render_adapters, unmaterialize_adapters

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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_subagents.py::TestAdapters -v`
Expected: collection ERROR with `ImportError: cannot import name 'ADAPTER_PATHS'`

- [ ] **Step 3: Implement** the four functions per the Runtime Formats and Permission mapping tables.

- [ ] **Step 4: Verify**

Run: `pytest tests/test_subagents.py -v` → check: all PASS
Manual: in a scratch project, materialize `researcher`, then open Claude Code (`/agents`), Cursor, OpenCode (`@` agent list), and Agy. → check: each runtime lists `researcher`, and none reports a frontmatter error.

- [ ] **Step 5: Commit**

```bash
git add agal/subagents.py tests/test_subagents.py
git commit -m "feat(subagents): native agent files for Claude Code, Cursor, OpenCode, Antigravity"
```

---

### Task 4: Install, Reference Counting, Teardown

**Files:**
- Modify: `agal/subagents.py`
- Modify: `agal/skills.py` (`save_local_state`: keep the file while `state["subagents"]` is non-empty)
- Modify: `agal/mcp.py` (`uninstall_mcp`, local scope: delete `.mcp.json` when `mcpServers` is empty and it has no other top-level keys; today it is kept whenever any skill remains, which leaves an empty file behind)
- Test: `tests/test_subagents.py`

`agal/presets.py` is **not** modified. `subagents.py` imports `resolve_preset` from it, so presets importing subagents would be circular. Callers in `cli.py` sequence the teardown (Task 5).

**Interfaces:**
- `install_subagent(name, target_dir=None, cfg=None) -> dict`: returns `{"name", "files", "skills", "mcp", "missing"}`.
  1. `load_subagent` (errors propagate to the caller).
  2. Snapshot `before = set(state["skills"]), set(state["mcp"])`.
  3. For each skill, then each MCP: if already present, record it. Otherwise call `install_skill`/`install_mcp` inside `try/except (ValueError, FileNotFoundError)`. On success, record it and add it to owned. On failure, print `⚠️  Subagent '<n>': skill '<s>' not available (skipped).` and add it to `missing` (Review Focus 3).
  4. If already installed, call `unmaterialize_adapters(old files)` first (idempotent reinstall). Then `materialize_adapters`.
  5. Reload state (the `install_*` helpers persist state themselves), write `subagents[name]` and `subagent_owned`, then save.
- `remove_subagent(name, target_dir=None, cfg=None) -> dict`: returns `{"removed": bool, "skills": [...], "mcp": [...]}`.
  - Not installed → return `{"removed": False, "skills": [], "mcp": []}` without saving state (Review Focus 4).
  - Otherwise: pop the entry, save, then `unmaterialize_adapters(entry["files"])`. Compute `needed` = deps of the other subagents ∪ the active preset's resolved deps (an unresolvable preset means keep everything). Uninstall owned ∖ needed: **skills first, then MCP** (so `.mcp.json` cleanup sees the final state). Reload state, drop the removed deps from `subagent_owned`, save.
- `unprepare_all_subagents(target_dir=None, cfg=None) -> list[str]`: `remove_subagent` for every installed subagent with the preset check disabled (the caller is tearing everything down). Returns the removed names.

- [ ] **Step 1: Write failing tests**

```python
import json
import os

from agal.config import LOCAL_STATE_FILE
from agal.presets import install_preset, uninstall_preset
from agal.skills import install_skill, load_local_state
from agal.subagents import install_subagent, remove_subagent, unprepare_all_subagents

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
```

Add `import sys` to the test module imports.

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_subagents.py::TestLifecycle -v`
Expected: collection ERROR with `ImportError: cannot import name 'install_subagent'`

- [ ] **Step 3: Implement** `save_local_state` fix, `uninstall_mcp` fix, and the three functions.

- [ ] **Step 4: Verify**

Run: `pytest tests/test_subagents.py -v` → check: all PASS
Run: `pytest tests/test_skills.py tests/test_mcp.py tests/test_presets.py -v` → check: all PASS (the `.mcp.json` cleanup change does not break existing expectations; if a test asserted the empty file is kept, update the assertion and note it in the commit body)

- [ ] **Step 5: Commit**

```bash
git add agal/subagents.py agal/skills.py agal/mcp.py tests/test_subagents.py
git commit -m "feat(subagents): install/remove with reference-counted dependencies"
```

---

### Task 5: CLI Surface (argparse)

**Files:**
- Modify: `agal/cli.py`
- Test: `tests/test_cli_subagents.py`

**Surface:**
- `agal subagent add [NAMES...]`: installs each name; with no names, shows a picker via `_select_items_cli` (labels `name  description`). An unknown or invalid name prints `❌ <error>` and continues with the rest.
- `agal subagent remove NAMES...`: prints `⚠️  Subagent '<n>' is not installed.` when `removed` is false.
- `agal subagent list`: name + description (same style as `cmd_list`).
- `agal subagent create NAME`: `save_subagent_template`; on `FileExistsError` prints `❌ …`; prints the created path.
- `agal subagent` with no action: prints the `subagent` subparser help.
- Add `"subagent"` to `known_commands` (`cli.py:695`).
- `cmd_unprepare_alias` and `cmd_remove` (`item_type == "preset"`, local scope) call `unprepare_all_subagents` **before** `uninstall_preset`.

- [ ] **Step 1: Write failing tests**

Setup mirrors `tests/test_cli.py`: temp `AGAL_HOME` with `config.yaml` setting `skills_dir`, `subagents_dir`, `presets_dir`, `context_file` (nonexistent) to temp fixtures (same subagents/skills as Task 4), `patch("pathlib.Path.cwd", return_value=self.proj_dir)`, stdout captured.

```python
class TestCLISubagents(unittest.TestCase):
    # setUp/tearDown/_run(argv) -> stdout str, as described above

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

    def test_bare_subagent_prints_help(self):
        self.assertIn("add", self._run(["subagent"]))

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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_cli_subagents.py -v`
Expected: FAIL with `SystemExit: 2` (argparse: `invalid choice: 'subagent'`)

- [ ] **Step 3: Implement** the `subagent` subparser with `add|remove|list|create`, `cmd_subagent`, the `known_commands` entry, and the teardown ordering in `cmd_unprepare_alias` / `cmd_remove`.

- [ ] **Step 4: Verify**

Run: `pytest tests/test_cli_subagents.py -v` → check: all PASS
Run: `pytest tests/test_cli.py -v` → check: all PASS

- [ ] **Step 5: Commit**

```bash
git add agal/cli.py tests/test_cli_subagents.py
git commit -m "feat(cli): add agal subagent add/remove/list/create"
```

---

### Task 6: Regression & Documentation

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Full suite** — Run: `pytest -v` → check: all PASS (70 existing + new)

- [ ] **Step 2: README.** Document `agal subagent add|remove|list|create`, the `AGENT.md` format (fields, defaults, permission mapping table), the generated files per runtime, `subagents_dir` + the re-run of `install.sh` that existing installs need, and the MCP limitation (only Claude Code reads `.mcp.json`).
→ check: every command in the README runs as written in a scratch project.

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: document subagents in README"
```
