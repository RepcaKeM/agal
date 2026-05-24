---
name: engineering-minimal-change-engineer
description: Enforce minimum-viable diffs — fixes only what was asked, refuses scope creep, prefers three similar lines over a premature abstraction. Use before opening any PR, when a fix or feature risks ballooning, or when a junior/AI-generated diff needs trimming.
---

# Minimal Change Engineer

## Overview

Most AI tools — and most engineers — over-produce by default. A 5-line bug fix arrives with renamed variables, "while we're here" docstrings, defensive null checks, and a refactor. Each addition carries its own risk and review burden, and none was asked for. This skill is the discipline of doing exactly what was asked and nothing more.

## When to Use

- Before opening any bug-fix PR (the most common scope-creep moment)
- When the diff exceeds the size you'd predict from the task description
- When you're tempted to "clean up while you're here"
- When reviewing someone else's PR that touches more than it should
- When an AI tool generated a fix that includes "improvements" you didn't ask for

## Iron Law

```
EVERY CHANGED LINE MUST TRACE BACK TO THE TASK AS STATED.

Walk the diff line by line before submit. For each changed line, answer
literally: "Does the task require this exact line?" If the answer is
"no, but it would be nicer" — delete the line.

No "while I'm here." No defensive code for impossible cases. No
abstraction for a single caller. No type annotations / docstrings /
comments on code you didn't change.
```

## Checklist (before opening PR)

1. **Read the task literally** — underline the verbs. The verbs define your scope. → check: "fix" ≠ "improve"; "add" ≠ "redesign."
2. **List touched files; justify each one** — each file you opened must be strictly required. → check: zero files in the diff that you'd struggle to defend.
3. **Walk the diff line by line** — every line passes the "task requires this exact line" test. → check: lines you can't defend are deleted.
4. **List the "while I'm here" temptations as follow-ups** — capture, don't smuggle. → check: PR description has a "Noted but not done in this PR" section, or follow-up issues filed.
5. **Diff size sanity check** — if a 1-line bug requires a 47-line diff, the bug isn't a 1-liner OR the diff is wrong. Re-check. → check: median diff for single-task work stays under 30 lines.

## Example: fix done minimally vs. expanded

**Task**: "Fix the off-by-one error in `paginatePosts`."

❌ Over-eager (47 lines):
```typescript
// Renamed variables, extracted constants, added JSDoc, added null checks,
// cleaned up imports...
const POSTS_PER_PAGE = 20;
export function paginatePosts(
  posts: Post[] | null | undefined,
  pageNumber: number
): Post[] {
  if (!posts || posts.length === 0) return [];
  if (pageNumber < 1) pageNumber = 1;
  const startIndex = (pageNumber - 1) * POSTS_PER_PAGE;
  return posts.slice(startIndex, startIndex + POSTS_PER_PAGE);
}
```

✅ Minimal (1 line):
```diff
- const startIndex = pageNumber * POSTS_PER_PAGE;
+ const startIndex = (pageNumber - 1) * POSTS_PER_PAGE;
```

The off-by-one was the bug. The bug is fixed. The PR is reviewable in 10 seconds. The "improvements" each carry their own risk and deserve their own PR — or, more likely, don't deserve a PR at all.

## Example: feature done minimally vs. over-architected

**Task**: "Add a `--dry-run` flag to the import command."

❌ Over-architected: `RunMode` enum, `DryRunStrategy` interface, `RunModeContext`, config field, "future modes" hooks.

✅ Minimal:
```typescript
const dryRun = args.includes('--dry-run');
// ...
if (dryRun) {
  console.log(`[dry-run] would write ${records.length} records`);
} else {
  await db.insertMany(records);
}
```

Two `if` branches. No abstraction. If a third mode ever shows up, extract then. Until then, the strategy pattern is debt with no payoff.

## Anti-Patterns (scope-creep traps to recognize)

- **"While I'm here…"** — the most common. Capture as a follow-up, don't include.
- **"For future flexibility"** — abstractions for callers that never arrive. Wait for the third caller.
- **Defensive coding** for cases that cannot occur (internal invariants, framework guarantees).
- **Modernization on touched files** — rewriting working old-style code in new style.
- **Consistency creep** — "everything else uses X, let me convert this one too."
- **Silent cleanup** — removing things you assume are dead. Either delete with confirmation or leave alone.
- **Backwards-compat shims for unused code** — `_oldName`, `// removed`, dead exports. Just delete.

## When to push back (script)

- "This is intentionally a one-line change. The other things you noticed are real and belong in separate PRs."
- "I noticed the helper below is unused, but it's outside this task's scope — filing as #1234."
- "The task says 'fix the login error' — do you want only the symptom fixed, or the root cause investigated? Those are different scopes."
- "I'm not adding a config flag for that. One caller exists; no second is requested. We can extract when the second appears."
