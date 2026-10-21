# Design: Agal Subagents Architecture & Multi-Agent Preparation

**Date:** 2026-10-21  
**Status:** In Review / Ready for Approval  
**Revised:** 2026-10-21 — aligned with runtime formats verified via Context7 (see §4.2) and with the implementation plan `docs/superpowers/plans/2026-10-21-subagents.md`.

---

## 1. Intent and the Why

`agal` currently excels at curating skills and MCP servers via presets to reduce context bloat. However, modern agentic workflows are shifting from monolithic prompts with large tool piles to specialized **subagents**—narrowly focused assistants dedicated to specific domains (e.g., research, code audit, UI/styling, testing).

The intent of this feature is to extend `agal` so that it can configure specialized subagents for a project. Just as `agal` configures skills and MCP servers across different agent runtimes, it will now also configure subagents for **Claude Code**, **OpenCode**, **Agy (Antigravity)**, and **Cursor**.

Existing presets remain fully functional; subagents are an additive, first-class capability of `agal`.

---

## 2. Goals, Non-Goals, Anti-Goals

### Goals
- **Subagent Definitions:** Provide a standard format (Markdown + YAML frontmatter) defining a subagent's specialization (role, system prompt, delegation description, optional model) and toolset (base permissions, assigned skills, assigned MCP servers).
- **Subagents Library Location:** Bundled subagents live in the repo root under `Subagents/<name>/AGENT.md` (following the convention of `Skills/`). agal reads them from `subagents_dir` (default `~/.agal/subagents`), which `install.sh` symlinks to the repo's `Subagents/`, exactly as it does for `presets/`.
- **Bundled Starter Subagents:** Ship curated starter subagents in `Subagents/` (`researcher`, `auditor`, `ui-specialist`).
- **CLI Commands:**
  - `agal subagent add [NAMES...]`: Prepares the specified subagents in the local project (opens an interactive picker if no names are given).
  - `agal subagent list`: Lists all available subagents.
  - `agal subagent create <name>`: Scaffolds a new subagent template in `<subagents_dir>/<name>/AGENT.md`.
  - `agal subagent remove <names...>`: Removes subagents, their runtime files, and dependencies no longer referenced.
  - `agal --unprepare` / `agal unprepare` / `agal remove preset`: Remove all configured subagents together with skills, MCPs, hooks, and context files.
- **Multi-Runtime Adapters:** Every supported runtime has native project-level subagent files; agal writes one per runtime (details in §4.2):
  - **Claude Code:** `.claude/agents/<name>.md`
  - **Cursor:** `.cursor/agents/<name>.md`
  - **OpenCode:** `.opencode/agents/<name>.md`
  - **Antigravity (Agy):** `.agents/agents/<name>/agent.md`
- **Automatic Dependency Provisioning & Reference Counting:** When a subagent requires skills or MCP servers:
  - Required skills and MCP servers are linked/installed locally via the existing `install_skill` / `install_mcp`.
  - `.agal_state.json` records which dependencies were added by subagents, so that removing one subagent does not delete skills/MCPs still needed by another subagent, by the active preset, or installed independently by the user.
- **Strict Local Isolation:** Everything modified or generated resides strictly within the target project directory.

### Non-Goals
- Removing or deprecating presets. Presets continue to exist and can coexist with subagents.
- Running subagent execution loops within `agal` itself. `agal` configures the project environment; the actual agent CLIs/IDEs execute the subagents.
- Configuring MCP servers for Cursor, OpenCode, or Agy. agal writes project `.mcp.json`, which only Claude Code reads. This limitation applies equally to presets and is documented in the README.
- Interactive creation wizard. `create` only scaffolds a template to edit by hand.

### Anti-Goals
- **No Global Modifications:** No changes to global user configs (e.g. `~/.claude.json`, global cursor settings, user profile files). Nothing is written through a symlink to a file outside the project.
- **No Orphaned Files:** Every created file is tracked and removed upon teardown or removal; adapter directories left empty are pruned.
- **No Clobbering:** An adapter path that already exists and is not tracked by agal is left untouched (warning printed).
- **No Context-File Injection:** agal does not add subagent blocks to `AGENTS.md`, `GEMINI.md`, `CLAUDE.md`, or `KIMI.md`. Those files remain owned by the preset/context mechanism.

---

## 3. Constraints

- **Strict Local Isolation:** All configurations, symlinks, and adapter files must reside within the target project root.
- **Deterministic Teardown:** State is recorded in `.agal_state.json` to allow deterministic uninstallation via `agal subagent remove` and `agal --unprepare`.
- **Python Architecture:** Must adhere to existing `agal` codebase patterns (Python 3.10+, modular structure under `agal/`, `argparse` CLI in `agal/cli.py`, `pyyaml` as the only runtime dependency, `unittest`-style tests).

---

## 4. How It Works (Decisions Made)

### 4.1 Storage & Definition Format
Subagents are located in `Subagents/` (matching `Skills/`), one directory per subagent:
```text
Subagents/
  researcher/
    AGENT.md
  auditor/
    AGENT.md
  ui-specialist/
    AGENT.md
```

Each `AGENT.md` follows this specification:
```yaml
---
name: researcher            # required, must equal the directory name
description: >-             # required; used by every runtime to decide delegation
  Deep codebase exploration, web research, and documentation queries.
  Use when the user asks for deep research, architecture analysis, or documentation search.
model: inherit              # optional: inherit | sonnet | opus | haiku (default inherit)
permissions:                # optional; both default to true
  edit_files: false
  run_commands: true
skills:                     # optional list of skill names
  - context7-docs
  - find-docs
mcp:                        # optional list of MCP server names
  - context7
---
You are a dedicated research subagent. Your role is strictly investigative...
```

- There is no separate `trigger` field: all four runtimes pick a subagent based on `description`, so it must contain the "Use when …" clause.
- `model` is passed to Claude Code as is. Every other runtime gets `inherit` (Agy uses `flash|pro` tiers, OpenCode needs `provider/model` ids).
- A definition with missing frontmatter, invalid YAML, a missing `description`, a name/directory mismatch, an unsupported `model`, or non-list `skills`/`mcp` is rejected with a `ValueError` naming the file. `agal subagent list` skips such definitions with a warning.

### 4.2 Runtime Materialization
When `agal subagent add <name>` runs, agal writes one native file per runtime. Formats were verified on 2026-10-21 against the official docs (Claude Code `AgentSpec`, cursor.com/docs/subagents, opencode.ai/docs/agents, antigravity.google/docs/cli/subagents):

| Runtime | Path | Frontmatter written by agal |
|---|---|---|
| Claude Code | `.claude/agents/<name>.md` | `name`, `description`, `model`, `skills`, `mcpServers`, `disallowedTools` |
| Cursor | `.cursor/agents/<name>.md` | `name`, `description`, `model: inherit`, `readonly` |
| OpenCode | `.opencode/agents/<name>.md` | `description`, `mode: subagent`, `permission: {edit, bash}` |
| Antigravity | `.agents/agents/<name>/agent.md` | `name`, `description`, `subagent: true`, `mainAgent: false`, `model: inherit`, `skills` (`skills/<name>`), `tools` (only when a permission is false) |

The markdown body of `AGENT.md` becomes the body of each file.

Cursor also reads `.claude/agents/`, but `.cursor/agents/` takes precedence on a name clash; agal writes the Cursor file so that `readonly` applies.

**Permission mapping:**

| | `edit_files: false` | `run_commands: false` |
|---|---|---|
| Claude Code | `disallowedTools` += `Edit`, `Write`, `NotebookEdit` | `disallowedTools` += `Bash` |
| Cursor | `readonly: true` | `readonly: true` |
| OpenCode | `permission.edit: deny` | `permission.bash: deny` |
| Antigravity | `tools` whitelist without edit tools | `tools` whitelist without `run_command` |

Claude Code uses a deny-list rather than a `tools:` whitelist, so Skill and MCP tools remain available without enumerating them.

**Open verification (Antigravity):** the base `tools` whitelist names and whether `skills/<name>` resolves relative to `.agents/` must be confirmed in the Agy CLI before implementation (plan Task 3, Step 0).

**Dependencies:**
- Skills listed in `skills` are linked via `install_skill` into `.claude/skills/` and `.agents/skills/`, which all four runtimes discover (OpenCode reads both).
- MCP servers listed in `mcp` are configured via `install_mcp` into project `.mcp.json`.
- A skill or MCP server not found in any registered source is reported with a warning and skipped; the subagent is still installed.

### 4.3 State & Reference Counting
`.agal_state.json` gains two keys:

```json
{
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

- `subagents.<name>` lists the dependencies present for that subagent and the files written for it.
- `subagent_owned` lists dependencies that a subagent install newly added. Dependencies that already existed (added manually or by a preset) are never removed by subagent removal.
- On `agal subagent remove <name>`, an owned dependency is uninstalled only if no other installed subagent lists it and the active preset (resolved including `core_preset`) does not list it. If the active preset cannot be resolved, all dependencies are kept.
- Removing a subagent that is not installed is a no-op that leaves state untouched.
- `agal --unprepare` removes all subagents first, then the preset's items, and leaves no agal-generated files behind.

### 4.4 CLI Surface
- `agal subagent add [NAMES...]`: Prepares the specified subagents (interactive picker if none given).
- `agal subagent list`: Shows all available subagents.
- `agal subagent create <name>`: Generates a new subagent template in `<subagents_dir>/<name>/AGENT.md`; refuses to overwrite an existing one.
- `agal subagent remove <names...>`: Removes the subagents' runtime files and cleans up unreferenced skills/MCPs.
- `agal --unprepare` (also `agal unprepare`, `agal remove preset`): Cleans up all subagents and presets installed in the project.

The positional subagent names live under `add` because argparse cannot mix free positional names with subcommand names in one position (a subagent called `list` would be ambiguous).

---

## 5. Builder Calls Summary

1. **Native Adapters Everywhere:** Every runtime gets its own native subagent file; no routing blocks are injected into context files, so there is no interaction with `AGENTS.md`/`GEMINI.md` symlinks.
2. **Tool Scoping:** Claude Code uses `disallowedTools`, Cursor `readonly`, OpenCode `permission`, Agy a `tools` whitelist. Skills are installed project-locally. MCP servers are project-wide (`.mcp.json`), so Claude Code subagents reference them via `mcpServers`, but other agents in the project can also see them.
3. **Granular Removal:** Supports both `agal subagent remove <name>` and `agal --unprepare`, with reference counting via `subagent_owned` in `.agal_state.json`.
4. **Storage:** Subagents live in `Subagents/` in the repository, read through `subagents_dir` (symlinked by `install.sh`), mirroring presets.
