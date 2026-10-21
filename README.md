# agal — Agent Agnostic Launch

Per-project & user-level **skill & MCP presets** and **subagents** for **Claude Code**, **Cursor**, **OpenCode**, and **Antigravity (Agy)**.

By default every agent CLI discovers *all* available skills — context noise, weaker
activation, wasted tokens. `agal` inverts this: you define a **preset** (e.g.
`backend-dev`, `wireframing`), and `agal` copies only those skills into the project.
The agent sees a small, relevant set instead of the global pile.

In addition to presets, `agal` configures specialized **subagents** with scoped
permissions, dedicated tools, and native agent definitions across all major agent runtimes.

Skills follow the **[Anthropic Agent Skills standard](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview)** —
each is a subdirectory with `SKILL.md` plus optional `scripts/`, `references/`, `examples/`.

---

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/RepcaKeM/agal/main/install.sh | bash
```

The bootstrap installs the `agal` CLI (via `pipx` / `uv` / managed venv — no system
Python pollution), links `~/.agal/presets` and `~/.agal/subagents` to the bundled libraries,
and writes a starter `~/.agal/config.yaml`.

> [!NOTE]
> **Existing installations:** Re-run `install.sh` (or run `ln -sfn "$PWD/Subagents" ~/.agal/subagents`) to link the bundled subagents library into `~/.agal/subagents`.

Or install the CLI directly:

```bash
pipx install git+https://github.com/RepcaKeM/agal.git
# or:  uv tool install git+https://github.com/RepcaKeM/agal.git
```

Optional but recommended: `fzf` (interactive preset/skill/subagent picker).

---

## Skills & subagents are bundled (Batteries Included)

This repo ships with curated, high-quality libraries ready out of the box:
- **Agent skills** under the `Skills/` directory (sourced from projects like `superpowers`, `agency-agents` and `caveman` under MIT license).
- **Starter subagents** under the `Subagents/` directory (`researcher`, `auditor`, `ui-specialist`).

By default, the installer automatically configures `agal` to use these bundled libraries. You don't need to download or configure any external library.

If you want to view or customize the configuration:

```bash
agal --config        # view or set custom skills_dir / subagents_dir
agal --check         # verify every SKILL.md has name + description frontmatter
agal subagent list   # view available subagents
```

The `AGENTS.md` coding guidelines are original prose written for this project.
The underlying ideas (reason before coding, minimal solutions, surgical edits,
verifiable outcomes) are widely held; the wording is our own and MIT-licensed
with the rest of this repo.

---

## Quick start

```bash
cd ~/projects/my-project

agal --prepare fullstack       # link skills + guidelines into the project
agal subagent add researcher   # add a dedicated research subagent
agal --status                  # show active preset and project status
# ... run claude / cursor / opencode / agy ...
agal --unprepare               # remove everything agal created (preset + subagents)

# Interactive: pick preset → pick CLI → launch
agal
```

`--prepare` creates, in the project root:

- `.claude/skills/` and `.agents/skills/` — copies of the preset's skills
- `AGENTS.md` + `CLAUDE.md` / `GEMINI.md` / `KIMI.md` — copies of the coding guidelines
  (skipped if you already have your own file by that name)

`agal runtime set <claude|cursor|opencode|agy>` limits those files to one IDE/CLI.
With no selection, every supported environment is prepared.

Everything is tracked by markers; `--unprepare` removes only what `agal` made and
never touches your own files.

---

## How skill loading works

1. **Discovery** — the CLI scans `.claude/skills/` (Claude, Kimi) or
   `.agents/skills/` (Gemini, Kimi) at session start
2. **Injection** — only each skill's `name` + `description` enters the system prompt
3. **Activation** — the full `SKILL.md` is read from disk only when a task matches

Only the preset's set is visible — not a global 200+.

---

## Presets

AGAL does not lock you into fixed, bloated bundles. Instead, it provides the tooling to easily compose, manage, and share your own presets combining **Skills** and **MCP servers** from any connected Git sources:

```bash
# Create a preset interactively (fzf / CLI multi-picker)
agal preset create my-preset

# List, inspect, and edit presets
agal preset list
agal preset info my-preset
agal preset edit my-preset    # opens in $EDITOR
agal preset delete my-preset
```

A preset YAML file (`~/.agal/presets/<name>.yaml`) looks like this:

```yaml
name: fullstack-dev
description: Fullstack web development workflow
skills:
  - systematic-debugging
  - test-driven-development
  - writing-plans
mcp:
  - postgresql
```

Presets can optionally inherit a meta-preset (configured via `core_preset` in `config.yaml`). If configured, core skills and MCP servers are automatically prepended and deduplicated.

---

## Subagents

While presets configure project-wide skills and MCP tools, modern agent workflows often benefit from **specialized subagents** dedicated to specific domains (e.g. deep research, code auditing, UI styling).

`agal subagent` provisions native agent files for each supported runtime, installs required skills and MCP dependencies into the project, and manages lifecycles with automatic reference counting.

### Supported runtimes & generated files

When you add a subagent (`agal subagent add <name>`), `agal` writes native project-level definitions conforming to each runtime's official agent specification:

| Runtime | Generated Path | Subagent Format |
|---|---|---|
| **Claude Code** | `.claude/agents/<name>.md` | Native agent spec (`name`, `description`, `model`, `skills`, `mcpServers`, `disallowedTools`) |
| **Cursor** | `.cursor/agents/<name>.md` | Subagent definition (`name`, `description`, `model: inherit`, `readonly`) |
| **OpenCode** | `.opencode/agents/<name>.md` | Subagent definition (`description`, `mode: subagent`, `permission: {edit, bash}`) |
| **Antigravity (Agy)** | `.agents/agents/<name>/agent.md` | Native agent spec (`subagent: true`, `mainAgent: false`, `model: inherit`, `tools` whitelist) |

### Commands

```bash
# Two-step menu: pick IDE/CLI, then pick subagents to install
agal subagent

# List all available subagents in your subagents library
agal subagent list

# Add subagent(s) to the project (interactive picker if omitted)
agal subagent add researcher auditor

# Remove subagent(s) and clean up unreferenced dependencies
agal subagent remove researcher

# Scaffold a new subagent definition template in <subagents_dir>/<name>/AGENT.md
agal subagent create my-agent

# Show one subagent's permissions and whether its skills/MCP are available
agal subagent info researcher

# Prepare only the environments you use (stored in this project's .agal_state.json)
agal runtime set cursor
agal runtime list
agal runtime reset          # all of: claude, cursor, opencode, agy

# Clean up all subagents, skills, MCP servers, and presets from current project
agal unprepare
```

### Subagent definition format (`AGENT.md`)

Subagents are stored in `Subagents/<name>/AGENT.md` (or your configured `subagents_dir`). Each subagent is defined by YAML frontmatter and a Markdown system prompt:

```yaml
---
name: researcher            # required; must match the directory name
description: >-             # required; used by runtimes to decide when to delegate
  Deep codebase exploration, web research, and documentation queries.
  Use when the user asks for deep research, architecture analysis, or documentation search.
model: inherit              # optional: inherit | sonnet | opus | haiku (default: inherit)
permissions:                # optional tool restrictions (both default to true)
  edit_files: false
  run_commands: true
skills:                     # optional list of required skill names
  - context7-docs
  - find-docs
mcp:                        # optional list of required MCP server names
  - context7
---
You are a dedicated research subagent. Your role is strictly investigative: explore the codebase, query documentation, search the web, and synthesize findings. You do not modify code or configuration files.
```

#### Fields & defaults

- **`name`** (*string*, required): Unique name matching the directory name (`Subagents/<name>/`).
- **`description`** (*string*, required): Used by agent runtimes to determine when to delegate tasks. Should always include a `"Use when..."` clause.
- **`model`** (*string*, default: `inherit`): Model preference (`inherit`, `sonnet`, `opus`, `haiku`). Passed through to Claude Code; other runtimes inherit their session model.
- **`permissions`** (*mapping*, default: `{edit_files: true, run_commands: true}`):
  - `edit_files`: Set `false` to restrict file editing and creation.
  - `run_commands`: Set `false` to restrict shell execution.
- **`skills`** (*list of strings*, default: `[]`): Skills required by the subagent. Automatically installed into `.claude/skills/` and `.agents/skills/`.
- **`mcp`** (*list of strings*, default: `[]`): MCP servers required by the subagent. Automatically configured in `.mcp.json`.
- **Markdown Body**: The system prompt defining the subagent's role, instructions, and operating behavior.

#### Permission mapping

`agal` automatically translates abstract permissions into native enforcement for each runtime:

| Runtime | `edit_files: false` | `run_commands: false` |
|---|---|---|
| **Claude Code** | `disallowedTools: [Edit, Write, NotebookEdit]` | `disallowedTools: [Bash]` |
| **Cursor** | prompt restriction while commands stay available (`readonly: true` only when both are false) | prompt restriction while editing stays available (`readonly: true` only when both are false) |
| **OpenCode** | `permission.edit: deny` | `permission.bash: deny` |
| **Antigravity** | read tools (`view_file`, `grep_search`, `list_dir`, `find_by_name`) plus `run_command` | read tools plus `replace_file_content` and `write_to_file` |

### Dependency reference counting & cleanup

When installing a subagent:
- Any declared `skills` are linked project-locally.
- Any declared `mcp` servers are added to project `.mcp.json`.
- Newly installed dependencies are tracked in `.agal_state.json` under `subagent_owned`.

When removing a subagent (`agal subagent remove <name>`):
- Only dependencies not required by any other installed subagent or active preset are removed.
- Pre-existing dependencies (manually installed before the subagent or owned by a preset) are never deleted.
- Running `agal unprepare` or `agal --unprepare` cleanly tears down all subagents before unlinking preset resources.

> [!IMPORTANT]
> **MCP files:** Claude Code reads project `.mcp.json`. When this project's runtime selection includes Cursor, `agal` also writes `.cursor/mcp.json`. OpenCode and Antigravity do not read either file. A project that has not run `agal runtime set` keeps the previous behavior and writes only `.mcp.json`.

---

## Copies, not symlinks

Skills and guideline files are always copied into the project, so the result
survives cloud agents and a fresh clone. `--remote` / `--copy` are still accepted
and do the same thing. Re-run `agal prepare` after you edit a skill in the library.

```bash
agal --prepare backend-dev
git add .agents .claude AGENTS.md CLAUDE.md GEMINI.md KIMI.md
```

---

## Per-project config (`AGAL_CONFIG`)

Skip the global `~/.agal/config.yaml` for a monorepo with its own setup:

```bash
mkdir -p .agal
cat > .agal/config.yaml <<EOF
skills_dir:    /opt/skills
subagents_dir: /opt/agal/subagents
presets_dir:   /opt/agal/presets
core_preset:   null           # optional meta-preset to auto-merge
context_file:  /opt/agal/AGENTS.md
EOF

export AGAL_CONFIG=$(pwd)/.agal/config.yaml
agal prepare my-preset
```

---

## Command reference

```bash
# Git Sources (Skills & MCP Repositories)
agal source add <git-url> [--name <name>]   # attach git repo as source (auto-detects skills & MCP)
agal source list                            # list connected repositories
agal source update [name]                   # git pull updates from remote
agal source remove <name>                   # remove attached repository

# Unified Installation (Skills & MCP)
agal add skill <name> [--local|--global]    # install individual skill (full directory package)
agal add mcp <name> [--local|--global]      # configure MCP server (.mcp.json or user config)
agal add preset <name> [--local|--global]   # install entire preset
agal remove <skill|mcp|preset> <name>       # cleanly uninstall item/preset

# Presets (Unified Skills + MCP)
agal preset create <name>                   # interactive preset creator (fzf / CLI menu)
agal preset list                            # list all presets
agal preset info <name>                     # show skills and MCP in a preset
agal preset edit <name>                     # edit preset YAML in $EDITOR
agal preset delete <name> [--yes]           # delete a preset file definition

# Subagents (Multi-Runtime Specialized Agents)
agal subagent list                          # list available subagents
agal subagent add [name...]                 # install subagent(s) (fzf / picker if omitted)
agal subagent remove <name...>              # remove subagent(s) and unused dependencies
agal subagent create <name>                 # scaffold new subagent template in subagents_dir
agal subagent info <name>                   # permissions and dependency availability

# Project IDE/CLI (filters skills, MCP, guidelines, and subagent files)
agal runtime                                # show or pick IDE/CLI for this project
agal runtime set <claude|cursor|opencode|agy>...
agal runtime list
agal runtime reset                          # prepare every supported IDE/CLI
# aliases: agal target, agal ide

# Diagnostics & Updates
agal check                                  # validate metadata & check remote updates
agal update                                 # pull updates for all sources
agal status                                 # active local preset & global items

# Project Shortcuts (backward compatible)
agal prepare <name>                         # link skills + MCP into current project
agal prepare <name> -r                      # copy mode (portable / cloud agents)
agal unprepare                              # cleanly remove everything agal created
```

### Remote (HTTP) MCP servers

A source can define remote MCP servers next to stdio ones. Put an `agal-mcp.yaml`
(or `mcp.json` with `mcpServers`) in the source repo:

```yaml
itsaplan:
  type: http            # optional, defaults to http
  url: https://api.example.com/mcp
  headers:
    Authorization: "Bearer ${ITSAPLAN_TOKEN}"
```

Never commit secrets — use `${VAR}` placeholders; Claude Code expands them from
the environment when it reads `.mcp.json`.

---

## Docs

- `AGENTS.md` — coding guidelines (read by all CLIs as project context)
- `agal-summary.md` — full architecture, design evolution, known limits

## License

MIT — see [LICENSE](LICENSE). Covers this repo's own content (tool,
presets, guidelines). Bundled and third-party skills are governed
by their respective upstream MIT licenses.
