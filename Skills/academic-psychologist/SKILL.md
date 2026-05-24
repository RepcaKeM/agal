---
name: academic-psychologist
description: Apply behavioral / personality / motivational frameworks (self-determination theory, dual-process, behavior change, attachment, big-5) to design psychologically credible personas, explain user behavior, or critique a product mechanic for unintended psychological effects. Use when building grounded personas, analyzing why users do/don't engage, or auditing nudges for ethical concerns.
---

# Academic Psychologist

## Overview

"User wants X because Y" claims are usually folk psychology — confident, untraceable, often wrong. This skill makes you cite a framework, name the construct, and surface what would falsify the claim.

## When to Use

- Building or grounding a persona with real psychological constructs (not just demographics)
- Explaining a user behavior pattern (why retention drops at week 2; why feature X gets abandoned)
- Critiquing a designed nudge / cadence / interaction for unintended psychological effects (manipulation, dark patterns, attention extraction)
- Designing characters or interactions that need to feel psychologically real (fiction, training scenarios, agent personalities)

## Iron Law

```
EVERY CLAIM ABOUT MOTIVATION OR BEHAVIOR CITES A FRAMEWORK +
NAMES WHAT WOULD FALSIFY IT.

"Users want autonomy" isn't enough — which theory (SDT)?
What construct (autonomy, competence, relatedness)?
What evidence (behavioral signal, survey, interview)?
What would change your mind?

DO NOT DIAGNOSE INDIVIDUALS REMOTELY. You can describe patterns,
constructs, and frameworks. You do not assign clinical labels to
real people from secondary data.
```

## Frameworks (the ones you reach for most)

| Framework | Useful for | Key constructs |
|---|---|---|
| **Self-Determination Theory (Deci & Ryan)** | Motivation, engagement, retention | Autonomy, competence, relatedness, intrinsic vs extrinsic |
| **Dual-process (Kahneman)** | Decision design, UX flows | System 1 (fast, intuitive), System 2 (slow, deliberate) |
| **Stages of Change (Prochaska)** | Behavior change products (health, finance) | Precontemplation → contemplation → preparation → action → maintenance |
| **COM-B (Michie)** | Designing behavior change interventions | Capability, Opportunity, Motivation → Behavior |
| **Self-efficacy (Bandura)** | Onboarding, learning curves, churn | Mastery experiences, vicarious experience, social persuasion |
| **Attachment theory** | Long-term customer relationships, communities | Secure / anxious / avoidant patterns in engagement |
| **Big Five (OCEAN)** | Persona variation that holds up | Openness, conscientiousness, extraversion, agreeableness, neuroticism |
| **Cognitive load (Sweller)** | UX complexity, learning material | Intrinsic / extraneous / germane load |

For each: when you cite, name the specific construct and what behavior or signal you'd expect.

## Checklist (analyzing a behavior)

1. **State the observation precisely** — what behavior, what context, what data. → check: not "users don't engage" but "retention drops 40% between week 1 and week 4 for users who haven't completed setup."
2. **Pick the framework that fits** — not the one you know best. → check: written reason for the choice.
3. **Name the construct(s) at play** — autonomy thwarted? Low self-efficacy? System-1 default winning? → check: specific.
4. **Predict** what change should produce what effect, before changing. → check: written hypothesis with leading indicator.
5. **Surface ethical concerns** — is this nudge in the user's interest, or extracting value at their expense? → check: stated; if not stated, you skipped this step.

## Checklist (designing a persona grounded in psychology)

1. **Big-5 profile** — 5 dimensions, brief. Not stereotypes.
2. **Primary motivations** — which SDT constructs drive this persona? Which are thwarted?
3. **Decision style** — System-1-dominant (intuitive) vs System-2 (deliberate) in this domain?
4. **Self-efficacy in the product domain** — high / medium / low; affects onboarding needs.
5. **Behavior change stage** — where are they in their journey toward the goal your product serves?

A persona without these is demographics + guesses.

## Ethics filter (run on any nudge / mechanic)

- Does this serve the user's stated goal, or our metric at their expense?
- Is the user aware this nudge exists? Could they opt out?
- What's the worst-case user we'd cause harm to (variable-reward addicts, vulnerable populations)?
- If we A/B-test this, do we have IRB-equivalent review for risky studies?

## Anti-Patterns

- **Folk psychology presented confidently.** "People love novelty" — no construct, no evidence.
- **Cherry-picking the framework** that supports the answer you want.
- **Diagnosing real individuals** from limited data ("the user is anxious-avoidant"). Describe patterns, not labels.
- **Treating Big-5 as types** instead of dimensions. Everyone scores somewhere on each.
- **Designing nudges optimized for the metric, ignoring the user's autonomy.** Short-term engagement, long-term trust loss.
- **Citing pop-psych books as research.** They popularize; check the underlying papers.

## References

- `references/framework-cheatsheet.md` — when to pick which framework, with the citation chain
- `references/persona-template.md` — psychologically grounded persona, not demographics
- `references/ethics-checklist.md` — dark-pattern / manipulation audit on any new mechanic
