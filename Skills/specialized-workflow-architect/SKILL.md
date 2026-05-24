---
name: specialized-workflow-architect
description: Map complete workflow trees BEFORE build — happy path, branches, failure modes, recovery, handoff contracts, observable states. Produces build-ready specs. Use when specifying a multi-step user/agent flow, defining handoff contracts between systems, or building a state-machine spec a team will implement against.
---

# Workflow Architect

## Overview

Most workflow bugs are unspecified states: the case nobody drew, the failure nobody named, the handoff with implicit contract. This skill makes you draw every node, name every edge, and write the contract for every handoff before implementation starts.

## When to Use

- Specifying a new multi-step user journey or agent pipeline
- Defining handoff contracts between systems, services, or agents
- Building a state-machine spec a delivery team will implement against
- Auditing an existing workflow for unspecified states (where bugs live)
- Designing recovery paths for an existing flow that has only the happy path

## Iron Law

```
NO WORKFLOW SHIPS WITHOUT: ALL NODES NAMED · ALL TRANSITIONS WITH
GUARDS · ALL TERMINAL STATES (SUCCESS, FAIL, ABORT) · ALL FAILURE
MODES MAPPED TO RECOVERY · EVERY HANDOFF WITH A SCHEMA + IDEMPOTENCY
KEY.

A workflow where "and then it works" stands in for actual specification
is a workflow that will surprise its operator. If you can't draw it
end-to-end, you don't understand it well enough to build it.
```

## Required artifact: workflow tree

For every workflow, produce:
1. **State diagram** — all states (boxes), all transitions (arrows), guards on transitions, terminal states marked.
2. **State table** — one row per state with: name, entry conditions, expected inputs, allowed transitions, on-failure behavior, observability (what we log).
3. **Handoff contracts** — for each cross-system / cross-agent transition: payload schema, idempotency key, retry policy, error contract.

See `references/workflow-tree-template.md`.

## Checklist (any workflow)

1. **Happy path drawn first** — the simplest end-to-end success. → check: drawn.
2. **Branches enumerated** — every decision node with each branch labelled. → check: zero "and then it figures it out."
3. **Failure modes mapped** per node: input invalid, dependency down, timeout, partial result. → check: each has a destination (recovery / fail / abort).
4. **Recovery paths defined** — for each failure: retry (with limits), compensate, escalate to human, dead-letter. → check: no infinite-retry, no silent drops.
5. **Idempotency keys at every handoff** — repeating the same request must produce the same outcome. → check: spec'd per handoff.
6. **Observability** — what fires a metric, what's logged at info / warn / error per state. → check: dashboard list-able from the spec.
7. **Timeouts everywhere** — every external call, every wait-for-event, every user-input gate. → check: no "wait forever" in any state.

## Checklist (handoff contract)

1. **Schema** of the payload (typed). → check: validates with a schema tool (JSON Schema, Pydantic, protobuf).
2. **Idempotency key** field defined and required. → check: receiver dedupes on it.
3. **Versioning** — `schema_version` field; receiver handles ≥ current. → check: future change path defined.
4. **Error contract** — what failures the receiver can return, what each means, what sender does. → check: not "200 with `success: false`."
5. **Retry semantics** — at-most-once / at-least-once / exactly-once. → check: documented; matches reality.

## Anti-Patterns

- **Prose-only workflow spec.** Words gloss over branches; diagrams force them.
- **"Should not happen" branches with no destination.** They DO happen. Map them.
- **Implicit retry** — "the client will retry on 500." Specify retry budgets and backoff; otherwise you get retry storms.
- **Side effects in branches without compensation.** If you partially completed action X and then need to abort, what undoes X? Specify.
- **Workflow that depends on a state held only in a human's memory.** Encode the state.
- **No timeout on a user-input gate.** "User will respond" — eventually, never, or in 6 months?
- **Adding a step to fix a bug without redrawing the tree.** Local fixes accumulate into untraceable workflows.

## References

- `references/workflow-tree-template.md` — state diagram + state table + handoff contract template
- `references/failure-mode-checklist.md` — common per-step failures and standard recoveries
- `references/idempotency-patterns.md` — idempotency-key handling, deduplication storage, retry semantics
