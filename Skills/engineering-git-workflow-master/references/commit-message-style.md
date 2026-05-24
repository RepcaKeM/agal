# Commit message style

## Subject line (≤72 chars)
- Imperative mood: "Fix" not "Fixed" / "Fixes"
- No trailing period
- Convention prefix if used: `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`, `perf:`, `style:`, `build:`, `ci:`
- Scope optional: `feat(auth): add WebAuthn`

## Body (when warranted)
- Wrap at 72 chars
- State the WHY, not the WHAT (the diff shows the what)
- If it fixes an issue: include `Fixes #N` on its own line
- If it's a breaking change: `BREAKING CHANGE: <description>` on its own line

## Example
```
feat(auth): add WebAuthn passwordless login

Currently users can only log in with password + optional TOTP.
WebAuthn (passkeys) is now widely supported on consumer devices and
removes the password as an attacker surface. Sentry data shows 40%
of unauthorized-access investigations involved password reuse.

This adds the WebAuthn registration / verification flow. Existing
password flow remains; this is purely additive.

Fixes #1234
```

## Don't
- `WIP`, `wip`, `more`, `fixes`, `oops` — squash before merge
- `Update X.ts` — what's the change FOR
- A commit body that just repeats the diff in prose
- Including the PR description verbatim — the commit lives forever; the PR doesn't
