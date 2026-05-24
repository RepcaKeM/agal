---
name: project-manager-senior
description: Decompose a spec into shippable tasks with realistic scope and sequencing — no gold-plating, no fantasy estimates. Use when breaking down a PRD/spec into a task list, planning a sprint/milestone, tracking scope drift against requirements, or doing a mid-project re-plan.
---

# Senior Project Manager

## Overview

Most plans fail at the seams: tasks too big to estimate, dependencies not surfaced, scope creep accepted without trading something out. This skill enforces small tasks, named dependencies, and explicit scope conservation.

## When to Use

- Converting a PRD or design spec into a task list a team can execute
- Sprint / milestone planning
- Re-planning mid-project when scope or dates shift
- Tracking scope drift against the original commitment

## Iron Law

```
NO TASK LONGER THAN 2 DAYS OF ONE PERSON'S WORK. If it's bigger, split.

If you can't split it, you don't understand it well enough yet.
Larger items hide assumptions; assumptions become slips.

SCOPE IS CONSERVED. Adding work means removing work or moving the
date. "We'll absorb it" is how every project becomes late.
```

## Checklist (initial breakdown)

1. **Acceptance criteria per deliverable** — written, testable, agreed with the PRD owner. → check: a tester could grade "done" without asking.
2. **Tasks ≤2 person-days** — each task has an owner, an estimate, and a verification step. → check: zero tasks marked "TBD" or "research."
3. **Dependencies surfaced** — task X blocked by task Y, owned by team Z. → check: dependency graph drawable.
4. **Critical path identified** — the chain that defines the date. → check: named; flagged for daily attention.
5. **Slack budget** — 15–20% buffer baked into the plan, not at the end. → check: written, not implicit.
6. **Risks named, owned** — top 3 risks with probability × impact and a mitigation. → check: revisited weekly.

## Checklist (during execution)

1. **Status uses 3 colors only**: green / yellow / red. Yellow means "needs help." Red means "date or scope at risk." No "amber-green."
2. **Slips reported within 24h of becoming likely**, not when they happen. → check: weekly cadence + ad-hoc escalation.
3. **Every "yes" to new scope is paired with a "no" to something** — show the trade. → check: scope log in the project doc.
4. **Decisions logged with date and owner** — so 3 weeks later you don't re-argue. → check: decision log appended in the project doc.

## Anti-Patterns

- **Hours estimates from someone who isn't doing the work.** Useless. Owners estimate.
- **"Buffer" added at the end of the plan.** Buffer is for absorbing the inevitable; spread it across the plan, not the last sprint.
- **Status: 80%, 90%, 90%, 90%, 95%...** — "asymptotic done" is red, not green. Force "what's left in hours."
- **Re-planning silently.** If dates moved, that's a stakeholder event. Communicate.
- **Plans without a critical-path callout.** Everything looks equally important; nothing is.
- **Tracking output (tasks completed) instead of outcome (the PRD's success metric).** Output-only PMs ship the wrong thing on time.

## References

- `references/task-template.md` — one-task entry with owner, estimate, acceptance, deps
- `references/risk-register-template.md` — risks with probability × impact + mitigation owner
- `references/status-report-template.md` — weekly format that exec readers actually use
