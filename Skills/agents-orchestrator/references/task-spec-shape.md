# Task spec — what each dispatched agent receives

```markdown
# Task: <short title>

## Goal
<One sentence: what this task should achieve.>

## Acceptance criteria
- [ ] <Testable criterion 1>
- [ ] <Testable criterion 2>
- [ ] <Testable criterion 3>

Each criterion is something the QA agent can grade pass/fail without asking the developer for clarification.

## Inputs / context
- Prior artifacts (link or paste): architecture, design tokens, API contracts
- Constraints: technology, performance, security
- Out of scope (explicit): things this task does NOT touch

## Expected output
- Where the deliverable goes (file path, branch, ticket)
- Format (code, doc, diagram, test set)

## Verification step
The exact command(s) or check the developer should run before marking done.
- e.g. `npm test`, `pytest -k feature_x`, `psql -c "EXPLAIN ANALYZE …"`

## Time budget
- Max ~N attempts in the dev-QA loop
- Escalate to human on exhaustion
```

## Rules
- A task without acceptance criteria gets sent back to the orchestrator. The dev agent should NOT guess.
- "Out of scope" prevents the dev from "while I'm here…" expanding the task.
- Verification step prevents dev from claiming pass without evidence.
