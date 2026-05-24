# Escalation rules — when to break the loop

The dev-QA loop is not infinite. Escalate to a human when:

## Hard limits
- **Loop iteration cap reached** (e.g. 3 dev-QA cycles per task). Don't burn more cost on the same task.
- **Same failure mode in 2+ iterations.** Dev isn't making progress; QA feedback isn't landing. Reformulate or hand off.
- **Conflicting acceptance criteria discovered mid-task.** Spec is wrong; fix the spec before more attempts.

## Soft signals
- Dev producing radically different solutions each iteration → spec is ambiguous
- QA flip-flopping pass/fail on the same kind of evidence → criteria are subjective
- Total wall-clock on the task > 3× original estimate → re-scope

## What to send to the human
- Original task spec
- Each iteration: dev's deliverable + QA's feedback
- Your (orchestrator's) diagnosis of why the loop isn't converging
- The specific decision you need: "should we lower the bar?", "should we re-scope?", "should we hand it to a different agent type?"

## Don't escalate
- A single failed iteration. That's normal; dev-QA exists for it.
- A criterion you find unclear in retrospect. Try to rewrite it once; only escalate if dev still can't satisfy.

## After escalation
- Document the resolution in the task. Next time a similar pattern arises, the orchestrator learns to escalate earlier (or self-resolve).
