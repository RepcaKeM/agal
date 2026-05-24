---
name: project-management-experiment-tracker
description: Design and run experiments — A/B tests, holdouts, feature-flag rollouts — with hypothesis-driven statistical rigor. Use when designing an A/B test, sizing the sample, defining success/guardrail metrics, deciding go/no-go on a running test, or post-mortem-ing a launch.
---

# Experiment Tracker

## Overview

Most A/B tests yield "no significant result" not because nothing works but because the test was underpowered, the metric was vague, or the launch was decided before the data. This skill enforces pre-registration, power analysis, and explicit decision rules.

## When to Use

- Designing an A/B test or feature-flag rollout with measurement
- Choosing primary and guardrail metrics for an experiment
- Sizing the test (sample size, expected MDE, runtime)
- Deciding go / no-go / extend / kill on a running experiment
- Post-mortem-ing a launch: did the lift hold?

## Iron Law

```
PRE-REGISTER: HYPOTHESIS · PRIMARY METRIC · MDE · SAMPLE SIZE ·
GUARDRAILS · STOPPING RULE · DECISION RULE. BEFORE THE TEST STARTS.

If any of those is decided after results come in, you're p-hacking,
not experimenting. Pre-registration prevents your future self from
moving the goalposts.

NO PEEKING. Predefine the analysis date or the sequential-test rule.
Eyeballing a daily-updated dashboard inflates false-positive rate.
```

## Checklist (designing the test)

1. **Hypothesis** — "If we <change>, then <metric> will move by <≥MDE> because <user mechanism>." → check: written; mechanism is plausible, not hand-waved.
2. **Primary metric** — one. Aligned with the user outcome, not a proxy. → check: instrumentation exists and is validated against historical data.
3. **MDE (Minimum Detectable Effect)** — the smallest effect worth shipping. → check: agreed by stakeholders; sample size derived from it (not the other way around).
4. **Guardrails** — metrics that must not degrade (latency, error rate, retention, revenue per other surface). → check: 1–3 named with red-line thresholds.
5. **Sample size + runtime** from power calc. Account for novelty/seasonality. → check: enough traffic to detect MDE at 80% power, 95% confidence; runtime ≥1 full business cycle.
6. **Randomization unit** — user / session / org / device. Match to where the effect actually applies. → check: no leakage (e.g. user-level treatment for an org-level feature).
7. **Decision rule** — explicit `if-then`. "If primary lifts ≥X% at p<0.05 AND no guardrail breach → ship. If guardrail breach → kill regardless. If null → 80% lift confidence interval that excludes ±MDE → ship/kill." → check: written before launch.

## Checklist (running / closing)

1. **Sanity check at day 1**: SRM (sample-ratio mismatch) — is traffic actually 50/50? If skewed, halt and debug. → check: chi-squared p > 0.01.
2. **Don't peek + decide.** Stick to the predefined analysis date OR use a sequential test (always-valid p-value).
3. **Apply the predefined decision rule.** Don't post-hoc reinterpret a null.
4. **Post-mortem the lift** 4 weeks after launch. Novelty effects fade; some lifts evaporate. → check: tracked in the dashboard, not just at launch.

## Anti-Patterns

- **Multiple comparisons unaccounted for** — 20 metrics tested, 1 hit p<0.05 at random.
- **Stopping early because "looks like it works."** Inflates false positives massively.
- **Underpowered test → "no result" interpreted as "no effect."** Absence of evidence ≠ evidence of absence.
- **HARKing** (Hypothesizing After Results are Known) — generating the "winning" hypothesis from the data is storytelling, not science.
- **Shipping based on stat-sig with no MDE check.** A 0.3% lift at p=0.04 may be statistically real but not worth the complexity.
- **Treatment leakage**: a user in control sees the treatment via shared org / device / cache. Voids the experiment.

## Related skills

- [[product-manager]] — when the experiment is part of a larger PRD decision; metric alignment matters
- [[design-ux-researcher]] — when qual context is missing for interpreting the quant result
- [[engineering-data-engineer]] — when the metric instrumentation isn't reliable enough to test

## References

- `references/preregistration-template.md` — fill before you turn the flag on
- `references/power-and-mde.md` — when sample-size calcs save you from underpowered tests
- `references/post-launch-followup.md` — 4-week, 12-week check structure
