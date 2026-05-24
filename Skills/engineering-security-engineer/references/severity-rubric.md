# Severity rubric (CVSS-aligned, shortened for review use)

## Critical
Unauthenticated remote impact OR full account/data compromise.
- RCE on a production host
- SQL injection that returns rows
- Authentication bypass (any user can log in as any other user)
- Hard-coded credentials with prod access in the repo
- Public bucket containing PII, secrets, or backups

**Response**: fix today. Page on-call if exploited.

## High
Authenticated impact at scale, or unauthenticated impact on a narrow surface.
- Stored XSS in an authenticated app surface
- IDOR / BOLA exposing other users' sensitive data
- Privilege escalation (user → admin) via parameter tampering
- SSRF reaching cloud metadata service
- JWT signature not verified, or `alg=none` accepted

**Response**: fix this week. Block release.

## Medium
Requires user interaction or specific conditions; meaningful but bounded.
- CSRF on a state-changing endpoint without SameSite=Lax/Strict
- Reflected XSS gated behind a click
- Verbose error responses leaking stack/schema
- Missing rate limit on a sensitive endpoint
- Open redirect (in a phishing chain)

**Response**: fix next sprint.

## Low
Defense-in-depth gaps; low realistic impact.
- Clickjacking on a non-sensitive page
- Missing security header on a static asset host
- Minor info disclosure (version banner)

**Response**: backlog with deadline.

## Informational
Best-practice deviation, no current exploit path.
- Dependency a major version behind, no known CVE
- Hardening recommendation (e.g. stricter CSP)

**Response**: note; address opportunistically.
