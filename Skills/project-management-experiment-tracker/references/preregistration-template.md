# Pre-registration (fill before launch)

**Experiment name**:
**Owner**:
**Stakeholders sign-off (PM, eng, data)**:
**Pre-registration date**:

## Hypothesis
"If we <change>, then <metric> will move by <≥MDE> because <user mechanism>."

## Primary metric
- Name:
- Definition (SQL or instrumentation link):
- Baseline (rolling 4-week average):
- MDE (minimum detectable effect):
- Direction (lift / drop):

## Guardrail metrics (1–3)
| Metric | Baseline | Red-line threshold | Direction |
|---|---|---|---|

## Sample size & runtime
- Statistical power: 0.8
- Significance threshold (α): 0.05
- Power calc inputs: baseline conversion = ?, MDE = ?, splits = 50/50
- Required sample per arm:
- Expected runtime at current traffic:
- Earliest analysis date:

## Randomization
- Unit (user / session / org / device):
- Source of randomization (which experiment platform):
- Validation: SRM check at day 1, day 7

## Decision rule
- **Ship** if: primary lift ≥ MDE, p < 0.05, no guardrail breach
- **Kill** if: any guardrail crosses red-line threshold OR primary moves ≥ MDE in wrong direction
- **Extend** if: trend toward ship-criteria but not yet stat-sig at analysis date — up to 2× original runtime, then close
- **Null result** (CI excludes ±MDE) → kill

## What we will NOT do
- Will not run additional segment analyses unless pre-specified
- Will not change MDE after seeing data
- Will not stop early without a sequential-test plan
