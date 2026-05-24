# Task entry

```yaml
id: T-042
title: "Wire user-profile API to settings page"
owner: <person>
estimate_days: 1.5
status: pending | in-progress | done | blocked
acceptance:
  - "Settings page reads name, email, avatar from /api/profile"
  - "Saving sends PATCH /api/profile with changed fields only"
  - "Error states match design spec"
depends_on: [T-021, T-030]
blocks: [T-061]
notes: |
  Profile API not yet versioned — coordinate with backend team
  before T-021 lands.
```

## Estimation guide
- 0.5 day  — small, well-understood (a known component change)
- 1 day    — typical feature slice
- 2 days   — upper limit; if bigger, split
- "I don't know" → spike (1 day timebox) to make it estimable
