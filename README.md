# agl — Agent Launch

Per-project **skill presets** for **Claude Code**, **Gemini CLI** and **Kimi CLI**.

By default every agent CLI discovers *all* available skills — context noise, weaker
activation, wasted tokens. `agl` inverts this: you define a **preset** (e.g.
`backend-dev`, `wireframing`), and `agl` links only those skills into the project.
The agent sees a small, relevant set instead of the global pile.

Skills follow the **[Anthropic Agent Skills standard](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview)** —
each is a subdirectory with `SKILL.md` plus optional `scripts/`, `references/`, `examples/`.

---

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/baszczkacper/agl/main/install.sh | bash
```

The bootstrap installs the `agl` CLI (via `pipx` / `uv` / managed venv — no system
Python pollution), links `~/.agl/presets` to the bundled presets, and writes a
starter `~/.agl/config.yaml`.

Or install the CLI directly:

```bash
pipx install git+https://github.com/baszczkacper/agl.git
# or:  uv tool install git+https://github.com/baszczkacper/agl.git
```

Optional but recommended: `fzf` (interactive preset/skill picker).

---

## Skills are NOT bundled

This repo ships the **tool, the presets, and the coding guidelines** — *not* the
skill library itself. You supply your own `skills_dir`. Presets reference skills
by directory name; point `skills_dir` at any Anthropic-standard skill collection.

The presets here were curated against skills sourced from these MIT-licensed
projects — clone any of them as a starting library:

| Source | Notes |
|---|---|
| [msitarzewski/agency-agents](https://github.com/msitarzewski/agency-agents) | MIT |
| [obra/superpowers](https://github.com/obra/superpowers) | MIT |
| [forrestchang/andrej-karpathy-skills](https://github.com/forrestchang/andrej-karpathy-skills) | MIT |
| [juliusbrussee/caveman](https://github.com/juliusbrussee/caveman) | MIT |

Set the path after install:

```bash
agl --config        # set skills_dir: /path/to/your/skills
agl --check         # verify every SKILL.md has name + description frontmatter
```

The `AGENTS.md` coding guidelines are derived from
[Andrej Karpathy's](https://github.com/forrestchang/andrej-karpathy-skills) public
guidance on working with coding agents.

---

## Quick start

```bash
cd ~/projects/my-project

agl --prepare backend-dev   # link skills + guidelines into the project
agl --status                # show active preset
# ... run claude / gemini / kimi ...
agl --unprepare             # remove everything agl created

# Interactive: pick preset → pick CLI → launch
agl
```

`--prepare` creates, in the project root:

- `.claude/skills/` and `.agents/skills/` — only the preset's skills
- `AGENTS.md` + `CLAUDE.md` / `GEMINI.md` / `KIMI.md` — the coding guidelines
  (skipped if you already have your own file by that name)

Everything is tracked by markers; `--unprepare` removes only what `agl` made and
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

| Preset | Use case |
|---|---|
| `dev-workflow-core` | Meta — auto-merged into every preset (brainstorm, planning, git, review) |
| `backend-dev` | Node/Python/Go backend, DB, API |
| `frontend-dev` | React/Vue/Angular, CSS, perf |
| `ui-ux` | UI design + UX architecture |
| `wireframing` | Discovery, low-fi, user flows |
| `sales-driven-page` | Landing pages, conversion copy |
| `ai-ml` | LLM, RAG, embeddings, evals |
| `data-science` | Analysis, modeling, notebooks |
| `security-audit` | Threat modeling, code review |
| `devops-sre` | CI/CD, infra, observability |
| `product-discovery` | User research, behavioral science |
| `pm-ops` | Project management, experiment tracking |
| `content-marketing` | Content strategy, SEO, long form |
| `sales-ops` | Outreach, data extraction, sales eng |
| `onboarding` | Entering an unfamiliar codebase |
| `inclusive-visuals` | Accessibility, brand, visual storytelling |

---

## Remote / portable mode (`--remote`)

Symlinks don't survive cloud agents (Claude Code Web, Cursor cloud) or a fresh
`git clone` on another machine. For portable setups, copy content instead:

```bash
agl --prepare backend-dev --remote   # copies skill + guideline content
git add .agents .claude AGENTS.md     # commit as part of the project
```

Trade-off: edits in your library no longer propagate — re-run `--prepare`.

---

## Per-project config (`AGL_CONFIG`)

Skip the global `~/.agl/config.yaml` for a monorepo with its own setup:

```bash
mkdir -p .agl
cat > .agl/config.yaml <<EOF
skills_dir:   /opt/skills
presets_dir:  /opt/agl/presets
core_preset:  dev-workflow-core
context_file: /opt/agl/AGENTS.md
EOF

export AGL_CONFIG=$(pwd)/.agl/config.yaml
agl --prepare backend-dev
```

---

## Command reference

```bash
# Presets
agl --new <name>       new preset (fzf multi-select)
agl --list             list presets
agl --info <name>      what's in a preset
agl --edit <name>      edit in $EDITOR
agl --validate <name>  check every skill resolves + has frontmatter

# Project
agl --prepare <name>      link skills + guidelines into cwd
agl --prepare <name> -r   remote mode (copy instead of symlink)
agl --status              active preset + mode
agl --unprepare           remove everything agl created

# Diagnostics
agl --check     flag skills missing frontmatter
agl --config    open config.yaml

# Launch
agl                  interactive
agl <preset>         pick CLI
agl <preset> <cli>   run directly
```

---

## Docs

- `AGENTS.md` — coding guidelines (read by all CLIs as project context)
- `agl-summary.md` — full architecture, design evolution, known limits

## License

MIT — see [LICENSE](LICENSE). Bundled presets and guidelines only; third-party
skill content is licensed by its respective upstream projects (all MIT).
