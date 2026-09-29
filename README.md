# agal — Agent Agnostic Launch

Per-project & user-level **skill & MCP presets** for **Claude Code** and **Gemini CLI**.

By default every agent CLI discovers *all* available skills — context noise, weaker
activation, wasted tokens. `agal` inverts this: you define a **preset** (e.g.
`backend-dev`, `wireframing`), and `agal` links only those skills into the project.
The agent sees a small, relevant set instead of the global pile.

Skills follow the **[Anthropic Agent Skills standard](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview)** —
each is a subdirectory with `SKILL.md` plus optional `scripts/`, `references/`, `examples/`.

---

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/RepcaKeM/agal/main/install.sh | bash
```

The bootstrap installs the `agal` CLI (via `pipx` / `uv` / managed venv — no system
Python pollution), links `~/.agal/presets` to the bundled presets, and writes a
starter `~/.agal/config.yaml`.

Or install the CLI directly:

```bash
pipx install git+https://github.com/RepcaKeM/agal.git
# or:  uv tool install git+https://github.com/RepcaKeM/agal.git
```

Optional but recommended: `fzf` (interactive preset/skill picker).

---

## Skills are bundled (Batteries Included)

This repo ships with a curated library of **modified, high-quality agent skills** under the `Skills/` directory (sourced from projects like `superpowers`, `agency-agents` and `caveman` under MIT license).

By default, the installer automatically configures `agal` to use these bundled skills. You don't need to download or configure any external skill library.

If you want to view or customize the configuration:

```bash
agal --config        # view or set custom skills_dir
agal --check         # verify every SKILL.md has name + description frontmatter
```

The `AGENTS.md` coding guidelines are original prose written for this project.
The underlying ideas (reason before coding, minimal solutions, surgical edits,
verifiable outcomes) are widely held; the wording is our own and MIT-licensed
with the rest of this repo.

---

## Quick start

```bash
cd ~/projects/my-project

agal --prepare backend-dev   # link skills + guidelines into the project
agal --status                # show active preset
# ... run claude / gemini / kimi ...
agal --unprepare             # remove everything agal created

# Interactive: pick preset → pick CLI → launch
agal
```

`--prepare` creates, in the project root:

- `.claude/skills/` and `.agents/skills/` — only the preset's skills
- `AGENTS.md` + `CLAUDE.md` / `GEMINI.md` / `KIMI.md` — the coding guidelines
  (skipped if you already have your own file by that name)

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

## Remote / portable mode (`--remote`)

Symlinks don't survive cloud agents (Claude Code Web, Cursor cloud) or a fresh
`git clone` on another machine. For portable setups, copy content instead:

```bash
agal --prepare backend-dev --remote   # copies skill + guideline content
git add .agents .claude AGENTS.md CLAUDE.md GEMINI.md KIMI.md   # commit with the project
```

Trade-off: edits in your library no longer propagate — re-run `--prepare`.

---

## Per-project config (`AGAL_CONFIG`)

Skip the global `~/.agal/config.yaml` for a monorepo with its own setup:

```bash
mkdir -p .agal
cat > .agal/config.yaml <<EOF
skills_dir:   /opt/skills
presets_dir:  /opt/agal/presets
core_preset:  null           # optional meta-preset to auto-merge
context_file: /opt/agal/AGENTS.md
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
