---
name: design-inclusive-visuals-specialist
description: Generate or critique AI image/video output for cultural accuracy and freedom from systemic bias — gender, race, age, ability, religion, body type. Use when prompting AI image/video tools for human-subject content, reviewing AI-generated visuals before publish, or correcting biased default outputs.
---

# Inclusive Visuals Specialist

## Overview

AI image / video models inherit the biases of their training data: male doctors, white CEOs, slim white women in fitness shots, "professional" defaulting to specific body types, religious dress styled as costume. This skill enforces specific prompting and a review step that catches the defaults the model would otherwise produce.

## When to Use

- Generating AI images / video for marketing, product UI, training material, or fiction
- Reviewing AI-generated visuals before they ship publicly
- Creating reference packs for a campaign that must read as inclusive across audiences
- Correcting biased defaults you see in initial generations

## Iron Law

```
THE PROMPT IS NOT NEUTRAL — IF YOU DON'T SPECIFY, THE MODEL DEFAULTS.
And the defaults are biased.

EVERY HUMAN-SUBJECT PROMPT SPECIFIES: AGE RANGE · ETHNICITY (when
representation matters) · BODY DIVERSITY · ABILITY/MOBILITY when
relevant · CULTURAL ACCURACY (clothing/setting matches the person
authentically, not as costume).

EVERY GENERATED IMAGE GETS A REVIEW PASS AGAINST THE BIAS CHECKLIST
BEFORE PUBLISH. Generation is fast; review prevents the embarrassment.
```

## Checklist (prompting)

1. **Who is this person?** Don't say "a doctor" or "a CEO" alone — the model picks defaults. Specify age, ethnicity, body, ability where representation matters. → check: prompt has 3+ specific descriptors.
2. **Cultural accuracy**, not borrowed aesthetics. If you're showing someone in cultural / religious dress, the setting and context match authentically. → check: would a person from that culture recognize themselves, not a stereotype?
3. **Action over pose.** What is the person doing? "A nurse adjusting an IV drip" beats "a smiling nurse looking at the camera" — generic poses lean on cliché.
4. **Diversity within the same shoot** if generating a set: don't have "the diverse one" and 5 defaults. → check: across the set, the distribution reflects who actually exists.
5. **Avoid stereotype anchors**: "successful businessman" → defaults skew; instead specify the actual scene without loaded shorthand.

## Checklist (review before publish)

1. **Who's NOT in the frame?** If every image in the set is the same demographic, that's a tell.
2. **Body diversity** — across the set, do bodies vary in size, shape, ability?
3. **Stereotyping signals** — older people only as patients / grandparents; disabled people only as inspiration porn; religious dress as exoticism; one demographic always as service worker, the other always as expert.
4. **Authentic cultural detail** — clothing, setting, props consistent within the depicted culture, not a remix?
5. **AI-generated artifacts** — extra fingers, weird teeth, garbled text. Common quality issue, embarrassing if shipped.
6. **Context consent** — if a real person, do you have rights? If clearly AI, is that disclosed where it should be?

## Anti-Patterns

- **Generic "diverse team" prompts.** Often produces one of each demographic in a row — looks like a stock photo of itself.
- **Defaulting to "professional" / "casual" / "American"** loaded shorthand that the model interprets via biased priors.
- **Adding "diverse" as a single word.** Specify the demographics you actually want represented; "diverse" alone produces token diversity.
- **Re-using the same model-face across generations** because it "looks polished." Identifies your set as same-source; defeats the inclusivity attempt.
- **Cultural mash-ups for "exotic" effect** — kimono + Native American headdress on a Western face = costume, not representation.
- **Hiding ability/disability** because the model is bad at it. Get it right or use commissioned photography for that subject.

## References

- `references/prompt-patterns.md` — specific prompt structures that produce non-default people, per scenario
- `references/bias-review-checklist.md` — exhaustive pre-publish review
- `references/cultural-accuracy-notes.md` — common misrepresentations to watch for, by culture
