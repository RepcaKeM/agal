# <repo-name> — onboarding doc

**Author**: <you>   **Date**: YYYY-MM-DD   **Commit at time of write**: <sha>

## What it does
One sentence. Cite: <README.md:1 OR primary docstring>.

## How to run locally
1. `<cmd>` — from `<Makefile / package.json / docs>`
2. `<cmd>`
3. Verify: `curl <local URL>` should return `<expected>`.

If build fails, document the failure here (and the missing dep / config).

## Architecture (Level 2 — containers)

Sketch + file citations:

- **<service / module name>** — purpose. Entry: `<file:line>`.
  - Reads from: `<dep>` (`<config-file:line>`)
  - Writes to: `<dep>`
  - Publishes: `<topic / event>`
  - Subscribes: `<topic / event>`

## Key modules
| Module | Purpose | Entry file |
|---|---|---|

## External dependencies
| Name | Used for | Config / env |
|---|---|---|

## Build & test commands
- Build: `<cmd>`
- Test: `<cmd>`
- Lint: `<cmd>`
- Local dev (hot reload): `<cmd>`

## Hot files (most-changed last 6 months)
1. `<path>` — <inferred reason from commit messages>
2. ...

## Conventions observed
- Branching: <observed pattern>
- Commit messages: <conventional? prefixed? free-form?>
- Test placement: <next to source / in test/ dir>
- Naming: <camelCase / snake_case / etc.>

## Unknowns (need a human)
- Why does `<module>` exist? No callers found in this repo.
- What's the runtime ordering between `<X>` and `<Y>`?
- ...
