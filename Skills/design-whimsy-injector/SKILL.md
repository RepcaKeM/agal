---
name: design-whimsy-injector
description: Add personality and small moments of delight to product / brand experience — micro-interactions, empty states, error pages, copy with character. Use when designing micro-interactions or empty states, refreshing the personality of an app, writing UI copy that earns the brand a smile, or auditing where the product feels generic.
---

# Whimsy Injector

## Overview

Most products try to be either "professional" (read: boring) or "fun" (read: random pop culture references). Both age badly. Real whimsy is small, specific, and earned — moments where the product noticed something and acknowledged it.

## When to Use

- Designing empty states, error pages, loading states, success confirmations
- Auditing UI copy for places that could carry personality
- Building micro-interactions (button feedback, transitions, easter eggs)
- Refreshing a product that feels functional but cold
- Writing onboarding moments that build affinity, not just instruction

## Iron Law

```
WHIMSY MUST BE EARNED AND DISMISSIBLE. Earned = it lands BECAUSE
of context, not despite it. Dismissible = power users see it once
and the product respects them by not repeating.

NEVER LET WHIMSY BLOCK THE CORE TASK. A delightful confirmation
animation that takes 2 seconds longer than necessary is a tax on
the user, not a gift.

WHIMSY THAT WORKS FOR A 22-YEAR-OLD ON LAUNCH DAY OFTEN FAILS FOR A
TIRED 45-YEAR-OLD ON A WEDNESDAY. Test across moods + contexts.
```

## Where whimsy lands

| Surface | Why it works there |
|---|---|
| **Empty states** | The user expects nothing; specific text + visual is a pleasant surprise |
| **Error messages** | A frustrated moment; warmth + concrete recovery is memorable |
| **Loading / waiting** | Forced pause; tiny copy / animation makes time pass |
| **Success confirmations** | Reward moment; one beat of acknowledgement |
| **First-run experience** | Forming the relationship; voice sets expectations |
| **Easter eggs** | Discovered, not flaunted; rewards the curious |

## Checklist (each whimsy touch)

1. **What just happened?** Whimsy responds to context, not the abstract category. → check: the copy / interaction couldn't be lifted to another product unchanged.
2. **Earned by specificity** — name the actual thing. "You sent your first invoice — that's a real one, not a test." Beats "Yay!" → check: specificity present.
3. **One beat, not three.** A 200ms delay, one line of copy, one micro-animation. Not all three at once. → check: total interaction cost < 2s for normal users.
4. **Power-user respect** — repeat users skip the celebration automatically (state remembered). → check: how does this feel on use #50?
5. **Voice consistency** — matches the brand voice doc; not random whimsy that varies per screen. → check: same writer/voice across all whimsy.
6. **Accessibility** — animations respect `prefers-reduced-motion`; emoji has alt text; humor doesn't rely on hard-to-parse references. → check: WCAG-respecting.
7. **Mood test** — read it aloud as a tired user, an angry user, a user who just got bad news. → check: it doesn't sting in any mood.

## Where whimsy fails (almost always)

- **Errors that are funny instead of useful.** Tell the user what to do; the joke can come after, not instead of.
- **Loading messages that are random fortunes.** Cute the first time; annoying the tenth.
- **Pop culture references.** Date the product instantly; alienate the half of users who don't know.
- **Modal dialogs with jokes.** Modals interrupt; the joke compounds the friction.
- **Mascots that comment.** Clippy was a warning.
- **Excessive emoji.** One per touch, max. Three is too many.

## Voice principles

- **Specific over clever.** "You're the 47th person to import a CSV this morning" > "📊 Importing your data".
- **Warm over cute.** Cute pings, then ages out. Warmth (concern, acknowledgement, dry observation) keeps.
- **Earned wit > inserted wit.** If the line could be cut without losing meaning, cut it.

## Anti-Patterns

- **Random fun copy in serious workflows.** "Oopsie! 🙊" on a billing failure is not whimsy, it's tone-deaf.
- **Whimsy as a feature checklist** ("we need 3 delight moments per screen"). Defeats the spirit; engineer them where they earn their place.
- **Brand mascot anthropomorphism.** Avatars commenting on user behavior get creepy fast.
- **Localized humor that doesn't travel.** Idiom-heavy copy breaks in translation; ship globally or translate carefully.
- **Easter eggs that affect production behavior.** Discovery delight; production impact is a bug.

## References

- `references/whimsy-surfaces.md` — examples per surface (empty / error / loading / success / onboarding)
- `references/copy-voice-rules.md` — phrasing patterns that earn warmth
- `references/accessibility-and-mood.md` — reduced motion, alt text, mood-testing prompts
