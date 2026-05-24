# Triage runbook — structure that analysts use at 3am

## Header
- **Rule**: <rule name + id>
- **Severity**: high
- **Owner**: <team>
- **Last reviewed**: YYYY-MM-DD

## What this alert means (one sentence)
e.g. "An external IP authenticated as a user with admin privileges over RDP."

## Step 1: Verify it's not the obvious benign case
- [ ] Source IP in the known-admin-egress allowlist? (link to allowlist)
- [ ] User account flagged as service account? (link to inventory)
- [ ] Time in expected business hours for that user?

If yes to any → close as benign, document why.

## Step 2: Establish if this is real
- [ ] Pull last 24h of activity for the user: <link to saved query>
- [ ] Check for prior failed auth attempts (brute force pattern)
- [ ] Check for post-auth activity: new processes, file access, lateral movement

## Step 3: If real → contain
- [ ] Disable the user account
- [ ] Force password reset
- [ ] Isolate the affected host (link to EDR action)
- [ ] Open incident: SEV-<X> (see severity guide)

## Step 4: Escalate
- IR team on-call: <pager link>
- Slack channel: #sec-incidents

## After
- Tag the alert with disposition (TP / FP / benign-true)
- If FP: add to rule's exclusion list with reason; ping rule owner

## Common false positives observed
- ...
- ...

## Recent true positives (for context)
- YYYY-MM-DD — <one-line incident summary + link to postmortem>
