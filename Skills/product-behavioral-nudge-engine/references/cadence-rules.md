# Cadence rules — touches per user per behavior

## Defaults
- **Max 3 active nudges** per behavior per user.
- **Tapering** between touches: T+1 day, T+4 days, T+11 days (geometric, not arithmetic).
- **Total nudges per user per week** ≤ 5 across the whole product. Beyond that, unsubscribe / disable rates climb hard.
- **Quiet hours** respected per timezone.

## Taper, don't escalate

❌ Escalating language across touches:
- T1: "Hey, complete your profile."
- T2: "Don't forget your profile."
- T3: "Final reminder — your profile is still incomplete."

The product moves from helpful to nagging. Users churn or unsubscribe.

✅ Tapering touches:
- T1: contextual prompt ("12 teammates have linked their portfolio — would you?")
- T2: different angle ("Designers with portfolios get 4× more requests")
- T3: silent removal of the nudge slot; "Not now" forever

If they didn't respond by T3, the product is wrong, the timing is wrong, or they don't want this — none is fixed by another email.

## When to RESET the cadence
- The behavior is no longer relevant (e.g. they completed it via a different path)
- A meaningful change in product would make it newly relevant (new feature, new context)
- The user explicitly asks ("remind me again later")

## What to NEVER do
- Daily nudges for a non-urgent behavior
- Multiple channels for the same nudge same day (email + push + banner)
- Persistent red-dot badge for items that aren't actually urgent
- "We miss you" sequences that increase frequency on non-response
