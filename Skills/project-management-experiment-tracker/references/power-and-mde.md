# Power and MDE — why so many tests give "no result"

## Quick formula (binary metric, two arms)
For 80% power, α=0.05, baseline rate p:
```
n per arm ≈ 16 × p × (1-p) / MDE²        (MDE expressed as absolute lift)
```
At p=10% baseline and MDE=1% absolute lift: `n ≈ 16 × 0.1 × 0.9 / 0.0001 = 14,400 per arm`.

## What pulls sample size up
- **Smaller baseline** (10% → 1% baseline means 10× the sample for the same relative lift)
- **Smaller MDE** (halving MDE = 4× the sample)
- **Higher variance metric** (revenue per user >> conversion rate)
- **Splits other than 50/50**

## What pulls runtime up
- Low daily traffic
- Weekly seasonality (need ≥1 full week)
- Effect builds over time (novelty / habituation)

## When you can't get the sample
Three legitimate options:
1. Raise the MDE — only test for effects worth the complexity.
2. Reduce variance — use CUPED (covariate adjustment) or pre-experiment baseline.
3. Use a different methodology — switchback, holdout cohort, before/after with interrupted time series.

## When NOT to A/B test
- Total available users < 2× required sample size
- Change is required (compliance, security) — just ship
- The lift you'd need to "win" is implausibly large for the change
