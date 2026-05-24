# Threat hunting — hypothesis-driven

## Bad hunt
"Let me look at the logs for last week and see if anything weird stands out."
→ You'll find something always. It means nothing.

## Good hunt
A specific hypothesis with a falsifiable search.

## Template
- **Hypothesis**: <attacker is doing X using technique Y, leaving telemetry Z>
  - e.g. "An attacker who compromised admin creds is using PsExec for lateral movement."
- **Telemetry needed**: <log source, fields, time window>
  - e.g. "Sysmon process creation events, last 30 days, parent_image: services.exe, image: PSEXESVC.exe"
- **Baseline what's normal**: known legitimate uses of this telemetry pattern (your sysadmins do use PsExec sometimes — when, from where, by whom?)
- **Search query**: <KQL / SPL / EQL / Sigma>
- **Expected output if hypothesis true**: <description>
- **Expected output if false**: <description>

## What to do with results
- **Confirmed TP** → contain, escalate to IR, write a detection rule so future instances auto-alert.
- **Confirmed FP / benign** → document what normal looks like; refine the search; consider rule + exclusion.
- **Inconclusive** → either tighten the hypothesis or accept that this telemetry can't answer.

## Hunt cadence
- One named hunt per week per analyst
- Each hunt documented (hypothesis, query, finding) in a shared doc
- New detection rules graduate from hunts when finding is reproducible
