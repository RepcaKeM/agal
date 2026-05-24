# Typography rules

## Font stack
- **Primary** (display + body): <Font Name>, weights <300, 400, 600, 700>
- **Secondary** (data / mono / accent): <Font Name>
- Fallback: system stack — `-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif`

## Type scale
Use the documented scale (`text-xs` through `text-4xl`). No off-scale sizes.

## Weight pairing
- Headlines: 700 (or 600 for product UI; pick one and stick to it)
- Body: 400; never below 400 for body
- Emphasis: 600. Italic only for titles of works (books, films), foreign phrases.

## Emphasis rules
- **NO ALL CAPS for emphasis.** Reads as shouting; bad for SR users.
- ALL CAPS allowed only for: short labels (`STATUS: LIVE`), eyebrows, and the documented display style.
- Underline reserved for links.
- Color-only emphasis fails accessibility — pair with weight or icon.

## Hierarchy
A page has ONE h1. Subsequent headings descend without skipping levels.
Visual hierarchy comes from scale + weight + spacing, not from random color shifts.

## Numbers
Tabular figures (`font-variant-numeric: tabular-nums`) in data tables, prices, timestamps. Proportional elsewhere.
