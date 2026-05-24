---
name: engineering-codebase-onboarding-engineer
description: Map an unfamiliar codebase by reading source — entry points, layering, key modules, build & test paths — and report ONLY facts grounded in the code. Use when entering a new repo, building a mental model fast, or producing an onboarding doc for the next person.
---

# Codebase Onboarding

## Overview

Most "what is this repo?" answers are guesses dressed up with confidence. This skill enforces a strict rule: every claim cites a file + line. Anything not grounded in the code is "unknown," not "probably."

## When to Use

- You (or a teammate) enters an unfamiliar repository
- Producing an onboarding doc, architecture map, or sequence trace
- Diagnosing "what does this service even do?" before changing anything
- Mapping dependencies between modules / services before a refactor

## Iron Law

```
EVERY CLAIM CITES A FILE AND LINE (or commit hash). NO INFERENCE
PRESENTED AS FACT. Anything not visible in the source is "unknown,"
not "probably," not "I think."

READ BEFORE GUESSING. If the answer requires speculation, surface it
as a question for a human, don't fabricate.
```

## Checklist (mapping a new repo, in order)

1. **Inventory** — `README`, top-level dirs, package manifest, build system, test runner. → check: 1-page summary of what files exist where.
2. **Entry points** — what runs when this starts? `main()` / `index.ts` / Dockerfile CMD / Procfile / k8s deployment. → check: named with file:line.
3. **Build & test paths** — how do I build, run, test locally? → check: actually executed (or noted as "build fails because X — needs <missing dep>").
4. **Top-level architecture** — services, modules, layers. → check: drawn as a C4 Level 2 (containers) sketch with file paths as citations.
5. **Dependencies external** — DBs, queues, APIs, vendors. → check: each named with where it's configured.
6. **Hot files** — `git log --pretty=format: --name-only | sort | uniq -c | sort -rg | head -30` to see what changes most; that's where the action is.
7. **Tests as documentation** — read the test files; they often state intent more clearly than docs.
8. **Open questions** — list things you couldn't determine from source. → check: surface for a human, don't guess.

## Output shape (onboarding doc)

```markdown
# <repo-name> — onboarding

## What it does (1 sentence)
Cite: README.md:1 or a docstring.

## How to run
1. <command> — cited from <Makefile / package.json / docs>
2. <command>

## Architecture (Level 2)
- Service A → reads from DB X (file:line)
- Service A → publishes to topic Y (file:line)
...

## Key modules
| Module | Purpose | Entry file |
|---|---|---|
| auth | session + JWT | src/auth/index.ts |

## External dependencies
| Name | Used for | Config |
|---|---|---|
| Postgres | primary DB | env: DATABASE_URL, config: config/db.ts:12 |

## Hot files (most-changed in last 6 months)
Listed; suggests where the active development is.

## Unknowns (need a human)
- Why does <module Z> exist? No callers found in this repo.
- What's the runtime ordering between <X> and <Y>? Both subscribe; race possible.
```

## Anti-Patterns

- **Inferring from names.** A directory called `auth/` might be deprecated. Read it.
- **Trusting the README.** Often stale. Verify against code.
- **Generating architecture diagrams from imagination.** If you didn't trace it in code, it's not architecture, it's hope.
- **Skipping the test directory.** Tests are the most honest documentation; many "what does this do?" questions are answered there.
- **Big-bang summary without inviting questions.** The onboarding doc should end with "what couldn't I determine?" — that's the conversation starter with the team.

## References

- `references/repo-recon-commands.md` — grep / find / git log / ripgrep patterns for fast mapping
- `references/onboarding-doc-template.md` — the doc shape above, ready to fill
