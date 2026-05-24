# Rule metadata (Sigma-compatible YAML)

```yaml
title: <short, descriptive>
id: <UUID>
description: |
  What attacker behavior this catches, in plain language.
  Note any prerequisites (e.g. "requires sysmon event id 1 with command-line logging").

author: <name>
date: YYYY-MM-DD
modified: YYYY-MM-DD
status: experimental | test | stable | deprecated

references:
  - https://attack.mitre.org/techniques/T1078/
  - <other links: research, prior incidents, vendor advisories>

tags:
  - attack.t1078            # MITRE technique
  - attack.persistence      # MITRE tactic
  - <custom tags per your SOC>

logsource:
  product: <e.g. windows / linux / aws / okta>
  service: <e.g. sysmon / cloudtrail / system-log>

detection:
  selection:
    EventID: 4624
    LogonType: 10
  filter:
    User|endswith: '$'      # exclude machine accounts
  condition: selection and not filter

fields:                     # what analysts will need in the alert
  - User
  - SourceIp
  - WorkstationName
  - TimeGenerated

falsepositives:
  - Vendor scanner during quarterly audit (excluded by IP in filter)
  - Legitimate admin RDP from jump host (excluded by source subnet)

level: low | medium | high | critical
runbook: runbooks/<rule-id>.md
owner: <person or team>
last_reviewed: YYYY-MM-DD
expected_fp_rate: <%>       # measured, not assumed
```

## Required fields for stable status
- `id`, `description`, `author`, `tags` (with ATT&CK), `logsource`, `detection`, `fields`, `falsepositives`, `level`, `runbook`, `owner`, `last_reviewed`, `expected_fp_rate`

A rule missing any of these can be `experimental` or `test` but does NOT graduate to `stable`.
