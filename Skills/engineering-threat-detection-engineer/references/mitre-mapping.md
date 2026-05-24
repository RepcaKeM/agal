# MITRE ATT&CK mapping — how to do it usefully

## What it is
A framework of attacker tactics (the "why" — Initial Access, Persistence, etc.) and techniques (the "how" — Valid Accounts, PowerShell, etc.). Mapping your detections to it gives a coverage view.

## How to map
1. For each rule, identify the **most specific technique** it catches. Avoid mapping to a tactic only — too broad.
2. If the rule catches multiple techniques, list all. Don't pick one arbitrarily.
3. If the rule catches a sub-technique (e.g. T1078.002 Domain Accounts), use the sub-technique ID.

## Coverage matrix
For each technique relevant to your environment:
- **Number of rules**: count, but…
- **Confidence**: do those rules actually fire on a real attempt? Tested?
- **Data source coverage**: do we have the logs the rule needs?

A technique with 5 rules but no logs to back them = false coverage.

## Prioritization
Don't try for 100% MITRE coverage — many techniques are irrelevant to your stack (e.g. macOS techniques on a Windows-only env). Prioritize:
1. Techniques observed in your past incidents
2. Techniques in threat-intel reporting for your industry
3. Techniques the Red Team / pentest report flagged as missing detection
4. Common-tradecraft techniques (initial access, lateral movement, credential access)

## Anti-patterns
- **Mapping every rule to a tactic** ("Defense Evasion") with no technique. Useless for coverage.
- **Counting rules as coverage** without testing if they fire on real activity.
- **Mapping aspirational rules** that have never been tuned and either fire never or constantly.
