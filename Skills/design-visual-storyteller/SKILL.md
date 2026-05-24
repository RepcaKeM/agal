---
name: design-visual-storyteller
description: Turn data, concepts, or arguments into visual narratives — infographics, slide decks, charts, motion sequences. Use when communicating a complex idea visually, designing a deck for execs/customers, picking the right chart for a dataset, or building a multi-frame story (case study, launch teaser).
---

# Visual Storyteller

## Overview

Most visual artifacts fail not from bad aesthetics but from no story spine. This skill makes you write the headline first, pick the chart second, decorate last.

## When to Use

- Designing a slide deck (pitch, exec update, customer-facing)
- Building an infographic / case study / launch landing-page hero
- Picking the right chart for a dataset (and resisting "any chart")
- Sequencing a multi-frame narrative (scrollytelling, motion, video storyboard)

## Iron Law

```
ONE FRAME, ONE TAKEAWAY. Write the takeaway as a full sentence
BEFORE designing the frame. If the takeaway doesn't fit a sentence,
the frame is doing too much.

NO CHART WITHOUT A POINT. The headline IS the point — not "Revenue
by month." If the point is "Revenue stalled in Q3," that's the title.
```

## Checklist (a deck or document)

1. **Story spine** — the deck's one sentence: "We <are doing X> because <Y>, and the next step is <Z>." → check: written before any slides.
2. **One takeaway per slide**, written as the slide title. → check: every title is a full sentence, not a category ("Q3 results" → "Q3 revenue stalled at $12M").
3. **Chart picker** for each data slide (see `references/chart-picker.md`). → check: chart type matches the question.
4. **Visual hierarchy** — the eye lands on the takeaway first. → check: squint test; the headline is what you see.
5. **Cut everything that doesn't serve the takeaway**: extra series, axes, gridlines, logos in the corner, footers. → check: every element justifies itself.
6. **End frame** with the ask / next step. → check: nobody leaves wondering "so what do you want me to do?"

## Checklist (a chart)

1. **The question this chart answers** — written above or in the title. → check: a non-data person can read the headline and understand.
2. **Chart type matches the question** — see picker.
3. **Annotate the insight** directly on the chart (arrow + label), don't make readers find it. → check: anchor for the eye exists.
4. **Color used for meaning, not decoration**. Default to grayscale, color only the series you're highlighting. → check: max 1–2 colored series.
5. **Axes start at zero** for bar charts; can clip for line charts if change is the point — disclose. → check: scale is honest.

## Anti-Patterns

- **Title is a category** ("Revenue"), not an insight ("Revenue dropped 12% in Q3"). The biggest design fix in any deck.
- **Stacked bars for "comparison"** — they fight comparison; use grouped bars or small multiples.
- **Pie charts with >4 slices.** Use a bar chart.
- **3D, perspective, drop-shadows, gradients on data.** They distort perception; remove.
- **Brand logo on every slide.** People know whose deck this is.
- **Slides that read like the speaker notes.** Each slide is a billboard; speak the rest.
- **Building the visual before knowing the story.** Open the doc, not the design tool.

## References

- `references/chart-picker.md` — question → chart type mapping with anti-patterns
- `references/deck-spine.md` — story spine templates (problem-solution, before-after, narrative arc)
- `references/data-ink-cleanup.md` — Tufte-style cleanup checklist
