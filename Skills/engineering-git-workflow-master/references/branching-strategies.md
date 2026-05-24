# Branching strategies

## Trunk-based (default)

```
main ───●───●───●───●───●─────→
              \         /
              feat/x──●
                    (PR, squash)
```

- Everyone branches from `main`, merges back within 1–2 days
- Branches: `feat/<short>`, `fix/<short>`, `chore/<short>`
- CI runs on every PR; main is always green and deployable
- Feature flags for in-progress work

**Good for**: continuous deploy, single product, small-to-medium teams.

## Release branches (for release trains)

```
main ───●───●───●───●───●───●───●───●───●─────→
              \         \
              release/v2 release/v3
              (cherry-pick fixes)
```

- `main` is HEAD; release branches cut from `main` at code-freeze
- Hotfixes cherry-picked from `main` → release branch
- Useful when you ship versioned software (mobile, on-prem, libraries)

## Gitflow (avoid for SaaS)

```
main (production tags)
 │
 develop
 │    \
 │   feature/x ── merged to develop
 │
 release/1.2 ── merged to main + develop, tagged
 │
 hotfix/1.2.1 ── merged to main + develop, tagged
```

- 4 branch types, double-merges on every release
- High overhead; designed for sequential release cycles
- Default to trunk-based unless you have a release-train operation

## Worktrees

```bash
# Work on two branches in parallel without stashing
git worktree add ../my-repo-feat-x feat/x
cd ../my-repo-feat-x

# When done
git worktree remove ../my-repo-feat-x
```

Use worktrees when you need to context-switch between branches without losing in-progress work. Better than `git stash`.
