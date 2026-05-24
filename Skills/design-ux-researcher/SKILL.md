---
name: design-ux-researcher
description: Plan and run user research (usability tests, interviews, surveys, card sorts, tree tests, diary studies); synthesize findings into actionable insights. Use when validating a design assumption, planning user research, analyzing interview/test transcripts, or writing a research report.
---

# UX Researcher

## Overview

Most "I think users want…" claims dissolve on contact with five actual users. This skill makes you test the riskiest assumption first, with the cheapest method that can answer it.

## When to Use

- Validating a design assumption before committing engineering effort
- Planning usability tests / interviews / diary studies / card sorts / tree tests
- Synthesizing raw qualitative data (notes, transcripts) into themes
- Quantifying behavior — surveys, analytics deep-dive, A/B test design
- Building or updating persona / journey-map artifacts grounded in real data

## Iron Law

```
NAME THE ASSUMPTION AND THE RISK BEFORE PICKING A METHOD.

"We need user research" is not a research goal. Write the specific
belief being tested, what would falsify it, and what decision rides
on the answer. If no decision rides on it — don't run the study.

5-USER MINIMUM FOR QUALITATIVE; STATISTICAL POWER CALC FOR QUANTITATIVE.
n=3 isn't research, it's vibes.
```

## Method picker

| Question you have | Best method | Sample size |
|---|---|---|
| "Can users complete task X with this design?" | Usability test (moderated or unmoderated) | 5 per major persona |
| "What problem are users actually trying to solve?" | Interviews + diary study | 6–10 |
| "How many of our users do X?" | Survey + analytics | n for ±5% CI; usually 200+ |
| "Is label A or B clearer?" | Tree test / 5-second test | 30+ |
| "Does the new design beat the old?" | A/B test | power calc per metric |
| "Why did metric X drop?" | Funnel analytics + 5 qualitative follow-ups | mixed |

## Checklist (any study)

1. **Decision statement**: "After this study, we will decide ___." → check: a real choice, not "we'll learn."
2. **Riskiest assumption first**: which belief, if wrong, costs the most? → check: that's the one this study tests.
3. **Recruit the right users** — match the persona, screen out edge cases. → check: screener questions exclude unqualified.
4. **Tasks framed as goals, not steps** — "schedule a meeting" not "click Calendar > New." → check: no task reveals the answer.
5. **Pilot 1–2** before the real run; revise the script. → check: pilot notes captured.
6. **Synthesize within 48h** while context is fresh — themes, not anecdotes. → check: theme = ≥3 instances across users, citation per instance.

## Anti-Patterns

- **Leading questions.** "Do you like this?" → "Yes." Use "Walk me through what you'd do here."
- **Reporting in averages from n=5.** Use frequencies and quotes; "4 of 5 users…" beats "average satisfaction 4.2."
- **Designer in the room moderating.** They'll defend the design. Use a neutral moderator or recording.
- **Skipping observation, jumping to interview.** What people say they do ≠ what they actually do. Watch first.
- **"Users want X" without quotes / clips.** If you can't cite the moment, it's your opinion.
- **Personas with no data.** Persona built from imagination is anti-research.
- **Quant alone**: numbers tell you what; qual tells you why. Pair them.

## Related skills

- [[academic-psychologist]] — when "why do users do X" needs a framework, not more interviews
- [[design-ux-architect]] — when research surfaces an IA / nav problem to fix
- [[project-management-experiment-tracker]] — for quant validation (A/B test, statistical sizing)

## References

- `references/usability-test-script.md` — moderator script + observer note template
- `references/synthesis-method.md` — affinity mapping + theme criteria
- `references/research-report-template.md` — 1-page format that decisions actually use
