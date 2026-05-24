---
name: engineering-devops-automator
description: Build and operate CI/CD pipelines, IaC, container orchestration, and observability for cloud-native apps. Use when adding a deploy pipeline, writing Terraform/CDK, designing a rollout strategy (blue-green/canary), wiring monitoring/alerting, or fixing a broken build.
---

# DevOps Automator

## Overview

Three things cause most production incidents: manual steps that drift, deploys without rollback, and "we'll add monitoring later." This skill makes you do them up front.

## When to Use

- New service needs a CI/CD pipeline
- Writing or modifying IaC (Terraform, CDK, CloudFormation, Pulumi)
- Designing deploy strategy: blue-green / canary / rolling / feature-flagged
- Setting up observability — metrics, logs, traces, alerts, dashboards
- Diagnosing a flaky build, slow pipeline, or failed deploy

## Iron Law

```
EVERY DEPLOY MUST HAVE A ROLLBACK PATH AND A HEALTH SIGNAL.

Rollback = a single command (or auto-trigger) that reverts to the last
known-good version in <5 minutes. Health signal = a metric or check that
proves the new version is serving traffic correctly. No rollback or no
signal → no deploy.

EVERY ALERT MUST BE ACTIONABLE. If the runbook is "investigate", the
alert is noise. Tune the threshold or delete the alert.
```

## Checklist (new pipeline / new service)

1. **Pipeline stages**: lint → unit → build → SAST + SCA + secrets scan → integration → deploy → smoke. → check: a failure in any stage blocks the next.
2. **Artifacts immutable + versioned** — image tag is the commit SHA, never `latest` in prod. → check: prod image references SHA in the manifest.
3. **IaC for everything that holds state** — no click-ops on prod. → check: `terraform plan` against prod shows zero drift.
4. **Secrets via vault / SM / sealed-secrets**, never in env or repo. → check: `gitleaks` clean; runtime fetches from vault.
5. **Rollout strategy explicit** — canary % + bake time, or blue-green with traffic switch, or feature flag. → check: written in the deploy manifest, not implied.
6. **Rollback rehearsed** — actually run it in staging once. → check: timestamped record of a successful rollback drill.
7. **Health checks**: liveness (process up), readiness (can serve traffic), startup (slow-start protection). → check: all three defined; readiness gates the rollout.
8. **Observability**: RED metrics (Rate, Errors, Duration) per service + a dashboard + at most 5 page-worthy alerts. → check: dashboard URL in the runbook; each alert links to a runbook section.
9. **Cost guardrails**: budget alert + autoscaling caps + spot/preemptible where safe. → check: monthly cap set per env.

## Anti-Patterns

- **`docker push :latest` to prod.** You lose the audit trail and can't roll back deterministically.
- **One giant pipeline that does everything for every service.** Split per service; shared library for the common steps.
- **Long-lived credentials in CI** (`AWS_ACCESS_KEY_ID` static). Use OIDC federation (GitHub → AWS/GCP) for short-lived creds.
- **Terraform `-auto-approve` against prod.** Plan in CI, apply with a human gate, or use a controlled mechanism (Atlantis / Terraform Cloud).
- **Mutable infra debugging.** SSH-into-prod-and-fix → drift → next deploy breaks. Reproduce in a fresh env from IaC instead.
- **Pinning to "the latest stable" image base.** Pin to a digest or specific tag; rebuild on a schedule, not at deploy time.
- **Alert on CPU > 80%.** Alert on user-visible symptoms (error rate, p99 latency, queue lag). CPU is a diagnostic, not a page.
- **No deploy windows + no blackout calendar.** Friday-5pm deploys are how outages start the weekend.

## Related skills

- [[support-infrastructure-maintainer]] — runtime ops, incident response, alert hygiene after deploy
- [[engineering-security-engineer]] — security gates in the pipeline (SAST, secrets scan, IAM review)
- [[engineering-backend-architect]] — when deploy strategy interacts with service architecture choice

## References

- `references/github-actions-pipeline.yml` — lint/test/scan/build/deploy with OIDC + image SHA
- `references/terraform-skeleton.tf` — backend, providers, modules, lifecycle/prevent_destroy
- `references/k8s-deployment.yaml` — Deployment + Service + HPA + readiness/liveness + PDB
- `references/observability-bootstrap.md` — RED metrics, log fields, trace propagation, alert rules that page
- `references/rollout-strategies.md` — when to pick canary vs blue-green vs feature flag, with examples
