---
name: engineering-threat-detection-engineer
description: Write SIEM detection rules, map MITRE ATT&CK coverage, hunt threats, tune alerts, and run detection-as-code pipelines. Use when authoring or tuning a SIEM detection rule, auditing MITRE coverage, performing a threat hunt, or addressing alert fatigue in a SOC.
---

# Threat Detection Engineer

## Overview

A noisy SIEM is worse than no SIEM — it trains analysts to ignore alerts. This skill enforces precision: every rule has a known attack technique, expected false-positive rate, owner, and tested response. Detections are code; they're versioned, tested, and reviewed like any other code.

## When to Use

- Writing or modifying a SIEM detection rule (Splunk SPL, Elastic EQL, Sigma, Sentinel KQL)
- Mapping or auditing detection coverage against MITRE ATT&CK
- Performing a threat hunt (hypothesis-driven search of telemetry)
- Tuning a noisy alert or reducing false-positive rate
- Building / maintaining a detection-as-code pipeline (rules in git, CI, deploy)

## Iron Law

```
EVERY DETECTION RULE HAS: NAME · ATT&CK MAPPING · OWNER · DESCRIPTION ·
DATA SOURCE · TESTED FALSE-POSITIVE RATE · TRIAGE RUNBOOK ·
LAST-REVIEWED DATE.

A rule without ALL of these is debt. New rules without runbooks =
analysts paged at 3am with no idea what to do.

NO RULE SHIPS UNTESTED. Test on a known TRUE positive (real attack
data or red team) AND historical telemetry (expected FP rate ≤5%
for high-severity alerts).
```

## Checklist (new detection rule)

1. **Hypothesis** — what attacker behavior are we trying to catch? Name the technique. → check: mapped to MITRE T-ID (e.g. T1078 Valid Accounts).
2. **Data source** named and validated — the log we depend on is shipping reliably. → check: log volume tracked; alert on absence.
3. **Logic** is the smallest sufficient — over-broad logic = false positives. → check: rule scoped to specific binaries / processes / users when possible.
4. **Test on known TP** — replay a known true positive (red team telemetry, public sample) and confirm fires. → check: test case stored alongside the rule.
5. **Test on historical telemetry** — run against last 30 days, count fires, sample for false positives. → check: FP rate ≤5% for SEV-high; ≤15% for SEV-medium.
6. **Runbook** — first action, second action, escalation. → check: written in `runbooks/<rule-id>.md`.
7. **Severity assigned** with explicit criteria (what data exfil / what blast radius justifies the sev level). → check: matches your SOC tier definitions.

## Checklist (tuning a noisy rule)

1. **Quantify the noise** — fires per day, action rate (acted on / total). → check: data, not "feels noisy."
2. **Find the FP class** — what category of benign event is firing this? Scheduled task? Admin behavior? Vendor scanner? → check: identified by sampling 20 alerts.
3. **Tune surgically** — exclude the specific class, not the whole vector. → check: known TPs still fire after tuning (regression test).
4. **Document the exclusion** — what / why / when reviewed. → check: in the rule file, not a separate doc.
5. **Re-baseline FP rate** — run 14 days; confirm. → check: numbers.

## Checklist (MITRE coverage audit)

1. **Map current rules to techniques.** → check: list per technique with rule-IDs.
2. **Identify gaps** — techniques with zero detections relevant to your environment. → check: prioritized by attacker-relevance to your stack (not by raw count).
3. **Detection types** — prevention / detection / response. Many techniques can only be detected post-event; clarify per technique.
4. **Don't conflate coverage with effectiveness.** A rule that exists but fires only on perfect telemetry isn't real coverage.

## Anti-Patterns

- **"Alert on anything anomalous."** Behavior-anomaly without baseline tuning = noise factory.
- **Rules without owners.** When the noise audit comes, no one defends or fixes them. Delete unowned rules.
- **Coverage reports that count rules, not techniques.** 200 rules on 1 technique ≠ broad coverage.
- **Detection-as-code without CI.** Rules deployed by hand drift between environments.
- **Hunting without a hypothesis.** "Look for weird stuff in last week's logs" → finds something always, means nothing.
- **Treating a SIEM rule as "set it and forget it."** Log formats change, attacker tradecraft changes; rules need review (quarterly minimum).

## References

- `references/rule-template.md` — required fields and shape (Sigma-compatible)
- `references/mitre-mapping.md` — how to map and audit coverage; pitfalls
- `references/triage-runbook.md` — runbook structure analysts will actually use at 3am
- `references/hunt-hypothesis.md` — turning a hypothesis into a search
- `references/detection-as-code-ci.yml` — GitHub Actions to lint + test rules on PR
