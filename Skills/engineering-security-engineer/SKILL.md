---
name: engineering-security-engineer
description: Application security — threat modeling, secure code review, vuln classification, and remediation for web/API/cloud apps. Use when reviewing auth flows, input handling, secret management, IAM, or before shipping anything that touches user data, payments, or admin functions.
---

# Security Engineer

## Overview

Most production breaches are not novel exploits — they're the same dozen mistakes: missing authz check, unparameterized query, JWT with `alg=none`, secret in env var, public S3 bucket, IDOR. This skill catches them before the attacker does.

## When to Use

- Reviewing auth (login, session, JWT, OAuth, OIDC, MFA, passkeys)
- Reviewing any endpoint that reads or writes user-owned data (IDOR / BOLA territory)
- Adding a new third-party dep, integration, or webhook (supply chain + SSRF risk)
- Changing IAM, secrets, encryption, or network policy
- Shipping a new public endpoint, file upload, admin function, or payment flow

## Iron Law

```
EVERY FINDING GETS: SEVERITY · EXPLOIT PATH · CODE-LEVEL FIX.

If you can't show the attacker's request and a copy-pasteable patch,
it's not a finding — it's a worry. Worries don't get prioritized,
worries don't get fixed.

NO RECOMMENDATION TO DISABLE A SECURITY CONTROL. Find the root cause.
NO HAND-ROLLED CRYPTO. Use libsodium / Web Crypto / vetted libs.
NO STRING-CONCAT SQL. Parameterized queries only.
```

See `references/severity-rubric.md` for the severity scale.

## When you find something

1. **Reproduce it** — write the actual exploit request (curl, Burp repro, or test).
2. **Classify** — Critical / High / Medium / Low / Informational (see rubric).
3. **Trace the blast radius** — how many users, what data, lateral movement?
4. **Write the patch** — code diff, not advice.
5. **Add a regression test** — a failing test that proves the vuln, then passes after the fix.

## Threat-model checklist (any new system or significant change)

1. **Data classification** — PII / financial / health / credentials / public. → check: written, per dataset.
2. **Trust boundaries** — list every place control crosses (Internet → API, API → service, service → DB, service → 3rd party). → check: each row has a control listed.
3. **STRIDE** per component — Spoof, Tamper, Repudiate, Info-disclose, DoS, Elevate. → check: at least one mitigation per realistic threat.
4. **Attack surface inventory** — public endpoints, file uploads, webhooks, OAuth callbacks, GraphQL introspection. → check: each item has rate limit + authn + input validation noted.
5. **Failure modes** — what happens when the auth service is down, the secrets manager is unreachable, the WAF is in monitor-only? → check: fails closed, not open.

See `references/threat-model-template.md` for the doc structure.

## Common vuln classes to check (when reviewing code)

- **Authn**: JWT — `alg` whitelist, issuer/audience verified, expiry checked, signing key rotated.
- **Authz**: every record-fetching endpoint enforces ownership (no IDOR/BOLA).
- **Injection**: SQL/NoSQL/cmd/template/LDAP — parameterized, never string-concatenated.
- **XSS/CSRF**: output-encoded by default, SameSite cookies, CSRF tokens on state changes.
- **SSRF**: any URL fetched from user input goes through an allowlist + private-IP block.
- **Secrets**: not in repo, not in env vars without encryption, not in client bundles, not in logs.
- **Headers**: HSTS, CSP (nonce-based), `X-Content-Type-Options`, COOP/COEP, CORS allowlist.
- **File upload**: magic-byte check, size cap, off-host storage, no executable mime allowed back.
- **Errors**: no stack traces / version banners / SQL errors to client.
- **Rate limit + lockout** on auth, password reset, MFA, and any expensive endpoint.

See `references/vuln-classes.md` for fix patterns per class.

## Anti-Patterns

- **Blacklist input filtering.** Always allowlist; blacklists are eternally incomplete.
- **Client-side authz "for UX".** The server MUST enforce; the client may hint.
- **Custom crypto / custom token format.** Use JWT/Paseto + a library, or get pen-tested. No shortcuts.
- **"We'll add a WAF" as a fix.** WAFs are defense in depth, never the only line.
- **`Access-Control-Allow-Origin: *` with credentials.** This is just "no CORS"; spec disallows it but bugs exist.
- **Disabling SSL verification "just for dev".** It ends up in prod. Use a proper local CA instead.
- **Logging request bodies on auth endpoints.** Passwords land in your log search index.

## Related skills

- [[engineering-backend-architect]] — when threat-modeling a new service before it's built
- [[engineering-threat-detection-engineer]] — runtime detection rules for what preventive controls miss
- [[engineering-devops-automator]] — secrets management, IAM, CI security gates

## References

- `references/threat-model-template.md` — STRIDE-shaped doc to fill
- `references/severity-rubric.md` — CVSS-aligned Critical/High/Medium/Low examples
- `references/vuln-classes.md` — fix patterns per OWASP class with code
- `references/secure-api-skeleton.py` — FastAPI with authn, validation, rate limit, audit
- `references/ci-security-pipeline.yml` — SAST + SCA + secrets scan in GitHub Actions
