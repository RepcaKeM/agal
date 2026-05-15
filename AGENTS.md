# Agent coding guidelines

Four working habits that keep agent-written code small, correct, and easy to
trust. They bias toward care over raw speed; for throwaway or trivial work, use
judgment.

## 1. Reason first, then write

Treat uncertainty as something to expose, not bury.

- Spell out the assumptions your solution depends on. If one is shaky, ask.
- When a request can be read more than one way, lay out the readings instead of
  quietly committing to one.
- If there's a leaner path than the one implied, name it — disagreement is fine.
- Hitting something genuinely unclear is a stop signal: say what's unclear and
  get an answer before continuing.

## 2. Smallest thing that works

Write the minimum that solves the actual problem. Nothing on spec.

- No capabilities that weren't requested.
- No abstraction layer over code with a single caller.
- No configuration knobs or "future-proofing" nobody asked for.
- No guards against states that cannot occur.

Sanity check: if the draft is 200 lines and the problem fits in 50, the draft is
wrong — redo it. If an experienced engineer would call it over-built, it is.

## 3. Change only what the task touches

Edit narrowly. Leave the rest of the file as you found it.

- Don't polish neighbouring code, comments, or whitespace.
- Don't rewrite things that already work.
- Follow the surrounding style even when your taste differs.
- Spot unrelated dead code? Mention it; don't remove it on your own.
- If your edit strands an import, variable, or helper, remove that orphan —
  but only the orphans your change created, not pre-existing cruft.

Test for every modified line: it should trace straight back to what was asked.

## 4. Drive toward a checkable outcome

Convert vague asks into something you can verify, then iterate until it holds.

- "Add validation" becomes "tests for the bad inputs, then make them pass."
- "Fix the bug" becomes "a test that reproduces it, then make it pass."
- "Refactor X" becomes "green tests before and green tests after."

For anything multi-step, write the plan as steps paired with their checks:

```
1. <step>  → check: <how you'll know it worked>
2. <step>  → check: <how you'll know it worked>
3. <step>  → check: <how you'll know it worked>
```

Concrete success criteria let you loop on your own. Vague ones ("make it work")
force a round-trip for every ambiguity.
