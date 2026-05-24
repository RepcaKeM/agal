---
name: agents-orchestrator
description: Multi-agent pipeline coordination — sequence specialized agents across spec → implement → QA → ship, with explicit handoffs, success criteria, and dev-QA loops. Use when running a workflow that spans several specialized agents (architect → dev → QA), or when designing the orchestration layer for a multi-agent pipeline.
---

# Agents Orchestrator

## Overview

Multi-agent pipelines fail when handoffs are implicit: each agent does its part well, but nobody owns whether the output of step N is ready to be input to step N+1. This skill enforces explicit success criteria per step and a dev-QA loop that exits only on a pass.

## When to Use

- Designing a multi-agent workflow (spec → architect → developer → QA → ship)
- Coordinating specialized agents on a single task across multiple stages
- Building the orchestration layer that spawns and reviews agent work
- Diagnosing why a multi-agent run produced "almost done" output

## Iron Law

```
EVERY HANDOFF HAS A WRITTEN ACCEPTANCE CRITERIA. THE NEXT AGENT
RECEIVES THE PRIOR AGENT'S OUTPUT + A YES/NO ON WHETHER IT PASSES.

If an agent's output enters the next stage without a check, you're
running open-loop. The pipeline accumulates drift; the final output
is far from spec; nobody knows where it went wrong.

QA AGENT MUST BE A FRESH CONTEXT. Never let the agent that built
the thing also grade it — biased grading is no grading.
```

## Pipeline shape

```
spec  →  architect/design  →  per-task dev-QA loop  →  integration QA  →  ship
              (gate)                  (gate)                  (gate)
```

Between each pair: an acceptance check. The work doesn't advance until the check passes.

## Per-task dev-QA loop

```
1. Dispatch a fresh developer agent for THIS task only.
   Inputs: task spec, prior artifacts (architecture, design system).
2. Dev produces output.
3. Dispatch a fresh QA agent for THIS task only.
   Inputs: task spec + dev's output. NO inheritance of dev's context.
4. QA returns PASS / FAIL with specifics.
5. PASS → next task. FAIL → loop to step 1 with QA feedback.
6. Loop max N times (e.g. 3). On exhaustion → escalate to human, don't keep churning.
```

## Checklist (designing the pipeline)

1. **Tasks decomposed and independent** — each task is shippable on its own. → check: a teammate can review the task list without the others.
2. **Acceptance criteria per task** — testable, written. → check: QA agent can grade without ambiguity.
3. **Agent assignment per stage** — explicit which agent type does what. → check: written in the orchestration spec, not implicit.
4. **Loop limits + escalation** — every loop has a max-iter and a human-escalation path. → check: no infinite loops possible.
5. **Context isolation** — each agent gets exactly what it needs, never the orchestrator's full history. → check: agent prompts are self-contained.
6. **Artifact persistence** — every stage's output is saved (file, branch, ticket) so a failed run is debuggable.

## Checklist (running the pipeline)

1. **Pre-flight**: spec loaded, prior artifacts present, success criteria visible.
2. **Per task**: dispatch dev, wait, dispatch QA on result, decide.
3. **Mid-pipeline status**: track pass / fail / pending per task in a visible board.
4. **Final integration**: a separate end-to-end QA run on the assembled output, not just per-task QA.
5. **Closure**: artifacts archived, learnings noted, follow-ups filed.

## Anti-Patterns

- **One agent does everything.** Lost specialization; long context; quality drops at the seams.
- **Same agent does dev and QA.** Confirmation bias. Hand-grading own homework.
- **No max-iter on the dev-QA loop.** Pipeline runs forever, burns cost, ships nothing.
- **Implicit handoffs.** "Then the agent figures out what to do next." It doesn't. Spec the handoff.
- **Letting QA inherit dev's context.** QA accepts dev's assumptions; no real grading.
- **Skipping final integration QA.** Per-task pass ≠ whole-system pass. The seams break.
- **Treating orchestration as a fancy `for` loop.** Real orchestration handles partial failures, retries with budget, and human escalation.

## References

- `references/task-spec-shape.md` — what a dispatched task must contain
- `references/qa-prompt-shape.md` — how to brief a fresh QA agent so grading is honest
- `references/escalation-rules.md` — when to break the loop and ask a human
