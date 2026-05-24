---
name: product-behavioral-nudge-engine
description: Design in-app prompts, notification cadences, and behavioral flows that move users toward an outcome — without dark patterns. Use when designing onboarding nudges, re-engagement sequences, copy that drives a specific action, or auditing existing nudges for psychological harm.
---

# Behavioral Nudge Engine

## Overview

"Add a nudge" usually means "add a notification." But the right nudge is sometimes silence; sometimes a default change; sometimes removing a step. This skill makes you diagnose the behavior blocker first (COM-B), then design the smallest intervention.

## When to Use

- Onboarding flows that lose users at a known step
- Re-engagement sequences for dormant users
- Designing in-app prompts / banners / empty states for an action
- Copy decisions where wording will shift behavior (CTA, error, confirm dialog)
- Auditing existing nudges for ethical harm or diminishing returns

## Iron Law

```
DIAGNOSE THE BLOCKER BEFORE DESIGNING THE NUDGE.

If the user lacks the ABILITY to do X (Capability blocker), a louder
notification won't help. If they lack the OPPORTUNITY (env / time),
guilt-tripping makes it worse. Only when MOTIVATION is the real
blocker is "nudge" the right tool. (COM-B model: Capability,
Opportunity, Motivation → Behavior.)

THE BEST NUDGE IS OFTEN A DEFAULT CHANGE, NOT A NEW NOTIFICATION.
Defaults are silent and respected. Notifications are loud and
ignored.

NEVER USE A DARK PATTERN TO HIT THE METRIC. The metric will pass;
trust will erode.
```

## Diagnose first (COM-B)

For the target behavior B (e.g. "complete profile"):
- **Capability**: do they know HOW? Have they done similar before?
  - If NO → fix instruction, lower complexity, show a worked example.
- **Opportunity**: do they have the time / context / env / data?
  - If NO → reduce required inputs, move the ask to a better moment, prefill what you can.
- **Motivation**: do they see the value?
  - If NO → this is when you reach for a nudge: copy, framing, social proof, loss aversion (used ethically).

## Nudge tool-belt (ordered by invasiveness — try less first)

1. **Default change** — set the desired option as default. Silent, respectful.
2. **Reduce friction** — fewer fields, prefill, smarter empty state.
3. **In-context affordance** — visible cue at the moment of choice (a button placed where the user already looks).
4. **In-app message** — empty state, banner, tooltip. Only when the affordance isn't enough.
5. **Notification** (push / email / SMS) — out-of-app interruption. Lossy; expensive in attention.
6. **Re-engagement sequence** — for dormant users; should taper if they don't respond, not escalate.

## Checklist (any nudge)

1. **State the target behavior precisely** — "complete profile" not "engage more." → check: a teammate can identify success.
2. **COM-B diagnosis** — which of C / O / M is the actual blocker? Cite evidence (analytics, interview, log). → check: written.
3. **Pick the least invasive tool that addresses the blocker.** → check: justify why a stronger tool isn't needed.
4. **Pre-register the success metric + ethical guardrails** (no opt-out abuse, no escalation past N attempts). → check: written before deploy.
5. **Cap the cadence** — total touches per user per period. Most users tolerate 1–3 nudges per behavior; beyond that, churn risk > conversion lift.
6. **A/B test against doing nothing.** Many "successful" nudges are noise; the control reveals it.
7. **Audit for ethics** — see `references/dark-pattern-checklist.md`.

## Anti-Patterns

- **Notification because notification is easy.** Most behavior change problems aren't motivation problems.
- **Escalating cadence** (3 emails over a week → daily → twice daily). Trains the user to unsubscribe.
- **Confirmshaming copy** ("No thanks, I don't want to save time"). Short-term lift, long-term churn.
- **Variable rewards / streaks in unrelated products.** Borrowed from games where engagement IS the product; in productivity tools it's attention extraction.
- **Persistent badges / red dots** for non-urgent items. Trains users to ignore the badge entirely.
- **Survey within 5 seconds of first use.** They haven't done anything yet; you're surveying their initial confusion.
- **"You haven't visited in 30 days" emails.** Almost never reactivate; often unsubscribe.

## References

- `references/com-b-diagnosis.md` — diagnosing capability vs opportunity vs motivation blockers
- `references/nudge-templates.md` — copy patterns per blocker type (NOT dark patterns)
- `references/cadence-rules.md` — touches per user per period; how to taper, not escalate
- `references/dark-pattern-checklist.md` — what NOT to design, with examples
