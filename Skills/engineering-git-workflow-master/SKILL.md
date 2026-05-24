---
name: engineering-git-workflow-master
description: Branching strategy, commit hygiene, rebase/merge decisions, conflict resolution, worktrees, CI-friendly history. Use when designing a branching strategy, resolving a merge conflict, cleaning up commit history, or auditing how a repo's git practices are slowing the team.
---

# Git Workflow Master

## Overview

Most git pain isn't tool-level — it's process: too-large PRs, branches that live too long, commit messages that hide intent, force-pushes that erase work. This skill keeps the team on the few habits that compound over a year.

## When to Use

- Designing or reviewing a branching strategy
- Resolving a non-trivial merge conflict
- Cleaning history before merge (squash / interactive rebase)
- Diagnosing slow / broken CI tied to branch structure
- Auditing commit messages / PR sizes for team health

## Iron Law

```
TRUNK-BASED BY DEFAULT. SHORT-LIVED BRANCHES (≤2 DAYS).
ATOMIC COMMITS. MESSAGES STATE INTENT.

A branch alive >1 week is a merge conflict in slow motion.
A 1000-line PR is a review nobody does. Atomic commits make bisect
work; intent-stating messages make blame readable years later.

NEVER FORCE-PUSH TO SHARED BRANCHES (main, release).
Force-push is a destructive op on personal/PR branches only —
and only when no one else has based work on it.
```

## Checklist (per PR)

1. **Branch from up-to-date trunk.** → check: `git fetch && git rebase origin/main` before opening.
2. **PR size ≤ 400 lines diff** (excluding generated / vendored). If bigger, split. → check: GitHub PR size.
3. **Each commit atomic** — one logical change; passes tests; reverts cleanly. → check: `git log --oneline` reads as a story.
4. **Commit message** — imperative subject ≤72 chars + body explaining WHY. → check: a reader 6 months later understands.
5. **Conventional commits** if the team uses them — `feat:`, `fix:`, `refactor:`, `docs:`, etc. → check: type matches the change.
6. **Squash vs preserve history** — squash if commits during dev were exploratory; preserve if commits are meaningful atomic steps. → check: PR description says which.

## Branching strategy (one-line picker)

| Team / project | Use |
|---|---|
| Single team, continuous deploy | **Trunk-based** + short-lived feature branches |
| Multiple teams, release trains | **Trunk-based** + release branches per train |
| External release cadence (mobile, on-prem) | **Release branches** with cherry-picks |
| Legacy + experimental side-by-side | **Trunk + long-lived experimental** (avoid; usually deletes after 6 months anyway) |

Avoid Gitflow (`develop` + `feature/*` + `release/*` + `hotfix/*`) unless you genuinely have a release-train operation; it's overkill for continuous deploy.

## Merge conflicts

1. **Rebase, don't merge** during conflict resolution on a personal branch — keeps history linear.
2. **Resolve one file at a time**; commit each as a separate rebase step if instructive.
3. **Re-run tests after every conflict resolution.** Conflicts often hide semantic merge bugs (clean syntax, broken behavior).
4. **For complex conflicts**: revert your branch to the merge-base, apply changes incrementally.

## Anti-Patterns

- **Long-lived feature branches** (≥1 week). Conflict surface grows nonlinearly. Split work or ship behind a feature flag.
- **"Fix typo" commits left in history.** Squash before merge.
- **`git commit -m "wip"` PRs.** Each commit should make sense in isolation.
- **Force-push to `main`.** Disable in branch protection; never bypass.
- **Reverting via "Revert" button without a follow-up forward fix.** Revert is a band-aid; the underlying issue is still open.
- **Merge commits for every PR + no squash option.** History becomes unreadable. Pick a convention (squash vs merge-commit) and enforce.
- **Worktrees vs branches confusion.** Use `git worktree` for parallel work on the SAME repo without losing your state on the other branch.

## References

- `references/commit-message-style.md` — conventional commits + body conventions
- `references/branching-strategies.md` — trunk-based vs release-branch vs Gitflow with examples
- `references/conflict-resolution.md` — step-by-step on a non-trivial conflict
