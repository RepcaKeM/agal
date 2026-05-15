# agl — Agent Launch: project summary

## The problem

200+ `.md` skill files for AI agents. Three different CLIs: **Claude Code**,
**Gemini CLI**, **Kimi CLI**. Every launch required manually disabling unneeded
skills — in Claude via `/plugins`, in Gemini via the agent. Wrong direction:
starting with everything and subtracting.

Extra context: **emdash** (ADE — Agentic Development Environment, YC W26) is used
to run agents in parallel inside isolated git worktrees. Emdash solves the
many-terminals/many-branches problem, but not the per-session skill set problem.

---

## Solution evolution

### v1 — inject into the context file (rejected)

First approach: `agl --prepare backend` concatenated the selected skills into one
big `CLAUDE.md` / `GEMINI.md` / `KIMI.md` and injected it into the project.

**Problem:** burns tokens. Every skill enters context on every message, even when
irrelevant.

### v2 — symlinks into `.agents/skills/` (current)

The right approach, found after researching all three CLIs' docs: each supports
on-demand skill loading — only **names and descriptions** at start, full content
only when the agent decides a task matches.

---

## How skills work in each CLI

All three follow the same scheme:

1. **Discovery** — scan skill directories at session start
2. **Injection** — only each skill's `name` + `description` enters the system prompt
3. **Activation** — full `SKILL.md` read from disk when a task matches

| CLI | Project dir | Global dir |
|---|---|---|
| **Claude Code** | `.claude/skills/` | `~/.claude/skills/` |
| **Gemini CLI** | `.gemini/skills/` or `.agents/skills/` | `~/.gemini/skills/` |
| **Kimi CLI** | `.kimi/skills/`, `.claude/skills/`, `.agents/skills/` | `~/.kimi/skills/` |

**Common path:** `.agents/skills/` — the open Agent Skills standard, read natively
by Gemini and Kimi.

> **Kimi CLI**, thanks to `--skills-dir`, can skip global discovery entirely and
> use a given directory.

### Required SKILL.md format (Gemini enforces, others read)

```markdown
---
name: skill-name
description: When and what to use it for. The more precise, the better — the agent decides from this.
---

# Skill body
...
```

Gemini **silently ignores** files without `name:` and `description:` frontmatter.
Check yours: `agl --check`.

---

## Architecture

Each skill = a subdir with `SKILL.md` (Anthropic Agent Skills standard). Lets you
ship scripts/references/examples without restructuring.

```
~/my-skills/                   ← skill library (untouched)
  typescript/
    SKILL.md
  systematic-debugging/
    SKILL.md
    find-polluter.sh           ← extras travel with the skill
    references/
  ...

~/.agl/
  config.yaml                  ← skills_dir, core_preset, context_file, CLI paths
  presets/                     ← dir-symlink → repo/presets/
    backend-dev.yaml
    dev-workflow-core.yaml     ← meta-preset auto-merged into every preset

project/                       ← created by agl --prepare
  AGENTS.md  →  repo/AGENTS.md           ← coding guidelines (symlink or copy)
  CLAUDE.md  →  repo/AGENTS.md
  GEMINI.md  →  repo/AGENTS.md
  KIMI.md    →  repo/AGENTS.md
  .agents/skills/              ← Gemini + Kimi
    typescript           →  ~/my-skills/typescript          (dir symlink)
  .claude/skills/              ← Claude Code + Kimi
    typescript           →  ~/my-skills/typescript
```

Dir-level symlinks — whole skill packages with extras. Edit a skill in the
library, change is visible in every project immediately.

### Context files (coding guidelines)

`config.yaml: context_file: /path/to/AGENTS.md` makes `--prepare` place
`AGENTS.md` plus per-CLI `CLAUDE.md` / `GEMINI.md` / `KIMI.md` in the project
root (symlink, or copy under `--remote`). The set of created files is tracked in
`.agl_context`; `--unprepare` removes only those. An existing file you wrote
yourself (not created by agl) is never overwritten — it's skipped with a notice.

Set `context_file: null` to disable.

### Core preset (auto-merge)

`config.yaml: core_preset: dev-workflow-core` — a meta-preset merged into every
preset. Core skills load BEFORE preset skills, deduplicated.

Example: `agl --prepare ai-ml` → ai-ml skills + dev-workflow-core skills
(brainstorming, planning, TDD, git-worktrees, etc. always available).

Disable: `core_preset: null`.

---

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/baszczkacper/agl/main/install.sh | bash
```

Installs the CLI via `pipx` / `uv` / a managed venv (no system-Python pollution),
links `~/.agl/presets` to the repo presets, and writes a starter config. Direct
alternative: `pipx install git+https://github.com/baszczkacper/agl.git`.

Then `agl --config` to set `skills_dir`. `fzf` recommended for interactive pickers.

The skill library is **not bundled** — see README → "Skills are NOT bundled" for
MIT-licensed source collections.

---

## Commands

```bash
# Presets
agl --new backend          # new preset — fzf multi-select from the library
agl --list                 # presets with skill counts
agl --info backend          # which skills are in a preset
agl --edit backend          # edit preset in $EDITOR

# Project mode (e.g. emdash / worktree workflow)
agl --prepare backend       # links skills + guidelines into cwd
agl --status                # active preset, mode, guidelines
agl --prepare automation    # swap preset (old links removed)
agl --unprepare             # remove everything agl created

# Pure CLI mode
agl                         # interactive: pick preset → pick CLI
agl backend                 # pick CLI only
agl backend claude          # run directly (links auto-removed on exit)

# Diagnostics
agl --check                 # which skills lack frontmatter
agl --validate backend-dev  # is the preset (after core merge) complete
agl --config                # open config.yaml

# Remote (cloud agents, CI, devcontainers, portable projects)
agl --prepare backend-dev --remote   # copy content instead of symlinking
```

### `AGL_CONFIG` env var (per-project config)

When you don't want the global `~/.agl/config.yaml` (e.g. a monorepo with its own
setup), point `AGL_CONFIG` at a project-local `config.yaml`.

---

## emdash workflow

```bash
cd ~/projects/my-project
agl --prepare backend      # creates .agents/skills/ + .claude/skills/ + guidelines

# Open emdash → "Add Task" → pick CLI
# emdash creates a worktree (project copy) → .agents/skills/ goes with it
# Claude reads .claude/skills/, Gemini reads .agents/skills/, Kimi reads both
# Each agent sees only the preset's skills, not the global 200+
# Full skill content loaded only when it matches the task
```

---

## Preset format

```yaml
# ~/.agl/presets/backend.yaml
name: backend
description: Node.js + PostgreSQL backend development
notes: |
  Production code focus. Ask before adding dependencies.
skills:
  - typescript          # name of the SKILL.md subdir (no .md, no /)
  - postgresql
  - nodejs-patterns
  - error-handling
  - docker-compose
```

Skills from `core_preset` (default `dev-workflow-core`) are appended
automatically — don't repeat them in the preset.

---

## Remote mode — when to use

| Scenario | Mode |
|---|---|
| Local dev on your own machine | symlink (default) |
| Devcontainer / Codespaces / SSH with the library on the remote | symlink |
| Cloud agent (Claude Code Web, Cursor cloud, Devin) | `--remote` |
| CI/CD pipeline (ephemeral runner, no skills_dir) | `--remote` |
| Monorepo shipped with skills baked in | `--remote` + git commit |
| Project cloned by devs without an agl setup | `--remote` |

`--remote` trade-off:
- ➕ Portable — works anywhere after clone, no `agl install`
- ➕ Self-contained — exactly the skills as of `--prepare` time
- ➖ No central updates — library edits don't propagate (re-run `--prepare`)
- ➖ Larger project — content copied instead of 60-byte symlinks

---

## Known limitations

- **Parallel presets in emdash:** all tasks in a project share one preset
  (`.agents/skills/` is single per project). Task A with `backend` and task B
  with `automation` simultaneously won't work — emdash has no per-task skill
  selection yet.
- **Frontmatter:** Gemini requires `name:` and `description:` in every SKILL.md.
  `agl --check` flags files to fix.
- **Kimi `--skills-dir`:** the flag can skip global discovery, but must be passed
  manually at launch — `agl` doesn't inject it automatically (yet).
