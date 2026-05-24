# Threat Model: <system name>

**Date**: YYYY-MM-DD &nbsp;|&nbsp; **Version**: 1.0 &nbsp;|&nbsp; **Owner**:

## System overview
- **Architecture**: monolith / microservices / serverless / hybrid
- **Stack**: languages, frameworks, datastores, cloud
- **Data classification**: PII / financial / health (PHI) / credentials / public — list each
- **Deployment**: k8s / ECS / Lambda / VM
- **External integrations**: payment processors, OAuth/OIDC IdP, third-party APIs, webhooks

## Trust boundaries

| Boundary | From | To | Controls |
|---|---|---|---|
| Internet → App | end user | API gateway | TLS, WAF, rate limit |
| API → Service | gateway | service | mTLS, JWT verify (alg whitelist) |
| Service → DB | service | DB | parameterized queries, encrypted connection |
| Service → Service | A | B | mTLS, service-mesh policy |
| Service → 3rd party | service | external API | outbound allowlist, secret from vault, retry/circuit-break |

## STRIDE per critical component

| Threat | Component | Risk | Attack scenario | Mitigation |
|---|---|---|---|---|
| Spoof | auth endpoint | high | credential stuffing, token theft | MFA, token binding, lockout |
| Tamper | API requests | high | param manipulation, replay | HMAC sigs, input validation, idempotency keys |
| Repudiate | user actions | med | denying unauthorized tx | immutable audit log, append-only |
| Info-disclose | error responses | med | stack/schema leak | generic errors to client, structured logs server-side |
| DoS | public API | high | resource exhaustion, algorithmic complexity | rate limit, request size cap, circuit breakers |
| Elevate | admin panel | crit | IDOR to admin fns, JWT role tamper | server-side RBAC, session isolation |

## Attack surface

- **External**: public APIs, OAuth/OIDC callbacks, file uploads, WebSocket, GraphQL
- **Internal**: service-to-service RPC, message queues, shared caches, internal admin APIs
- **Data**: DB queries, cache, log storage, backups
- **Infra**: container orchestration, CI/CD, secrets manager, DNS
- **Supply chain**: third-party deps, CDN scripts, external APIs

## Open risks / accepted residual

| # | Risk | Severity | Accepted by | Compensating control | Review date |
|---|---|---|---|---|---|
| 1 | example | M | <person> | <control> | YYYY-MM-DD |
