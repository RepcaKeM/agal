# Merge-conflict resolution — non-trivial case

## Setup
You're on `feat/x` and `main` has moved on. You want to bring your branch up to date AND resolve conflicts safely.

## Steps

```bash
# 1. Update local main
git fetch origin
git checkout main
git pull --ff-only

# 2. Rebase your branch onto current main
git checkout feat/x
git rebase main
```

## When conflicts appear

For each conflicting file:

```bash
# See what's conflicting
git status

# Open the file, resolve markers
#   <<<<<<<  HEAD
#   ours
#   =======
#   theirs
#   >>>>>>>  <hash>

# Use a 3-way diff tool for tricky cases
git mergetool

# Re-run tests after EACH file (not just at the end)
npm test       # or pytest, cargo test, etc.

# Mark resolved and continue
git add <file>
git rebase --continue
```

## Semantic conflicts (compile-clean, behavior broken)

Syntactic conflict markers are visible; **semantic conflicts** aren't:
- Both branches added a method with the same name but different signatures → compiles, but callers split.
- One branch deleted a function the other branch added a caller for → compiles, runtime error.

Mitigation: re-run the full test suite after rebase, not just compile.

## When to give up and re-do

If a rebase spawns conflicts in 20+ files or repeats across iterations, consider:
```bash
git rebase --abort

# Create a fresh branch from current main
git checkout -b feat/x-v2 main

# Cherry-pick your meaningful commits one at a time
git cherry-pick <sha1> <sha2> ...
# Resolve each conflict in isolation
```

This is often faster than untangling a long rebase.

## Never
- `git push --force` to a branch others have based work on. Use `git push --force-with-lease` if you must, but coordinate.
- Resolving with "take theirs" / "take ours" wholesale without reading the diff. That's how features silently revert.
