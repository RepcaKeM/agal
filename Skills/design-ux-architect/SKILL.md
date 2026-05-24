---
name: design-ux-architect
description: Information architecture, navigation, page-layout grammar, and CSS systems handed to engineers. Use when designing the IA of a new product, restructuring navigation, defining a layout grid / CSS architecture, or giving frontend devs concrete implementation guidance.
---

# UX Architect

## Overview

UX architecture sits between research (what users need) and visual design (how it looks). It decides what goes where, what comes after what, and how the page is built — the structural decisions that are hardest to change later.

## When to Use

- New product or major section: defining sitemap, navigation, page templates
- Restructuring nav because "users can't find anything"
- Establishing a grid / spacing / layout system the engineering team will implement
- Resolving a UX vs visual-design disagreement about page structure
- Spec'ing a flow that crosses multiple pages or services

## Iron Law

```
IA DECISIONS GET A USER TEST (CARD SORT / TREE TEST) BEFORE SHIPPING.

You are not the user. The clean hierarchy that makes sense to you is
not necessarily the one users will navigate. Treesort 5+ users on the
nav before committing.

EVERY PAGE TEMPLATE NAMES ITS PRIMARY ACTION. If a page has no clear
primary action, it has no clear purpose.
```

## Checklist (IA / nav change)

1. **Sitemap** — every page typed (landing, list, detail, form, settings). → check: written, with relationships.
2. **Nav hierarchy depth ≤3** for product surfaces. → check: deepest leaf is reachable in three clicks.
3. **Naming tested** — card sort or tree test ≥5 users. → check: success rate ≥80% on the primary tasks; renames made for the failing ones.
4. **Cross-link map** — which pages link to which? Where does the user land on error? → check: no dead ends.
5. **Empty / error / loading templates** at the IA level (not just per-component). → check: each major template has all three drawn.

## Checklist (CSS / layout system handed to engineers)

1. **One grid** — define columns, gutters, margins per breakpoint. → check: documented; engineering can implement with CSS grid / container queries.
2. **Page templates** named and consumable — `template-list`, `template-detail`, `template-form`. → check: each has a Storybook example + Figma frame.
3. **Spacing system** uses the same scale as components (one source of truth — UI Designer's tokens). → check: no duplicate scales.
4. **Layout primitives** — Stack, Cluster, Sidebar, Cover, Grid (Every Layout style). → check: documented; engineers reach for these before custom flexbox.

## Anti-Patterns

- **Mega-menu hiding the IA problem.** If users can't find things, the navigation is wrong; mega-menus paper over it.
- **Designing screens before flows.** Without the flow, you can't tell whether a screen is the right step.
- **"User research is too expensive" → ship and learn.** Card sorts cost ~30 minutes per user; tree tests are free with Optimal Workshop / Maze.
- **CSS hand-off as Figma screenshots.** Engineers need tokens + breakpoints + grammar, not pixel measurements.
- **Each page invents its own layout.** Without templates, the product feels different on every screen.

## Related skills

- [[design-ux-researcher]] — when the IA question needs validation with real users (tree test, interview)
- [[design-ui-designer]] — when templates + grid are set and the question is visual treatment
- [[product-manager]] — when the IA disagreement is really about scope / priority of pages

## References

- `references/treetest-script.md` — running a 5-user tree test in 30 minutes
- `references/layout-primitives.md` — Stack/Cluster/Sidebar/Cover/Grid CSS recipes
- `references/page-templates.md` — list / detail / form / dashboard template shapes
