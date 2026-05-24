---
name: design-brand-guardian
description: Enforce brand identity consistency — voice, visual tokens, logo usage, naming, tone. Use when reviewing assets/copy/UI for brand consistency, defining or extending brand guidelines, onboarding a new team to the brand system, or auditing third-party material that uses your brand.
---

# Brand Guardian

## Overview

Brand drift is gradual: a tone shift here, a logo recolor there, a one-off illustration that becomes the new style. This skill stops drift at the artifact level by giving every choice a token to point at.

## When to Use

- Reviewing copy, asset, or UI for brand consistency before publish
- Defining or extending brand guidelines (voice, color, typography, illustration, motion)
- Auditing third-party material that uses your brand (partner, vendor, press)
- Onboarding a new contributor (agency, freelancer, internal team) to brand standards

## Iron Law

```
NO BRAND ELEMENT WITHOUT A TOKEN OR A WRITTEN RULE TO POINT AT.

If you can't say "this violates rule 3.2" or "this should use
color-brand-primary", you're enforcing taste, not brand. Taste-based
review doesn't scale and creates resentment.

LOGO + WORDMARK + VOICE ARE THE ONLY THREE LINES THAT NEVER MOVE.
Everything else (color, type, illustration, motion) can flex within
documented ranges.
```

## Checklist (asset / copy review)

1. **Identify the asset type** — landing page, social post, slide, email, ad, product UI. Different latitude per type. → check: type named.
2. **Voice & tone**: matches the documented voice attributes (e.g. "direct, warm, never clever-for-its-own-sake"). Cite the rule. → check: rule cited per flagged line.
3. **Logo usage**: clear-space, min-size, color variants, never recolored / stretched / boxed. → check: pass per `references/logo-rules.md`.
4. **Color**: from the token palette; semantic role respected (don't use error red for celebration). → check: zero off-token colors.
5. **Type**: brand fonts, scale from system, no typewriter-style emphasis (ALL CAPS for emphasis is brand-policy). → check: per `references/typography-rules.md`.
6. **Illustration / photo style**: matches documented style traits (e.g. flat / 3D / line-only; subject + composition rules). → check: passes the style sniff test or flagged.
7. **Verdict**: pass / minor-fix / blocking, with line items linked to rules. → check: feedback is actionable, not "feels off."

## Checklist (extending the brand)

1. **Why the new element / rule?** — what couldn't be expressed before? → check: a real gap, not "I'd like more options."
2. **Token added**, named by role not value. → check: integrated into the design system.
3. **Examples + counter-examples** in the guideline. → check: both included so others can apply consistently.
4. **Versioned change** with an effective date + migration note for existing assets. → check: changelog entry.

## Anti-Patterns

- **"Looks off-brand" without naming the rule.** Either the rule exists (cite it) or it doesn't (don't enforce).
- **Adding rules retroactively to win an argument.** If it wasn't a rule, fix it forward, don't backdate.
- **Brand-as-aesthetic-purity.** Brand serves the user and the business. A perfect-looking artifact that buries the CTA is broken.
- **Locking out flexibility entirely.** Brand should have ranges (e.g. "60–80% brand palette + 20–40% accents") not single answers.
- **Bottom-of-the-funnel review only.** Catching drift in the published version costs 10× catching it at the brief.

## References

- `references/voice-and-tone.md` — voice attributes, tone modifiers per channel, do/don't examples
- `references/logo-rules.md` — clear-space, min-size, on-color, on-photo, what you may NOT do
- `references/typography-rules.md` — font stack, scale, weight pairings, emphasis rules
- `references/review-template.md` — structured review note to send back to creators
