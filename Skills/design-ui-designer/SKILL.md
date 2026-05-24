---
name: design-ui-designer
description: Visual design execution — component design, layout, color, typography, spacing systems. Use when designing or refining a UI component, building or extending a design system, deciding tokens (color/space/typography), or critiquing a screen for visual consistency.
---

# UI Designer

## Overview

Most "design problems" are systems problems: unnamed tokens, ad-hoc spacing, inconsistent component states. This skill makes you design the system first, then the screen.

## When to Use

- Designing a new component or refining an existing one
- Adding tokens (color, type, space, radius, elevation) or extending a design system
- Auditing a screen for visual inconsistency
- Choosing between Tailwind / CSS Modules / native CSS for a component library
- Bridging design tool (Figma) to implementation (handoff specs)

## Iron Law

```
NO ONE-OFF VALUES. Every color, spacing, font-size, radius, shadow MUST
reference a token. If a token doesn't exist for what you need, name and
add one BEFORE using it.

EVERY INTERACTIVE COMPONENT HAS DESIGNED STATES: default, hover, focus,
active, disabled, loading, error, empty. Missing a state = the bug shows
up at the worst time.
```

## Checklist (component)

1. **States designed**: default, hover, focus-visible (keyboard ring), active, disabled, loading, error, empty. → check: all eight rendered in the component playground.
2. **Tokens, not literals** — color/space/type/radius/shadow all reference design tokens. → check: zero hex codes or pixel values in the component CSS that should be tokens.
3. **Min-width / max-width / wrapping behavior** — define how it shrinks and grows. → check: try at 320px, 768px, 1440px.
4. **Density variant if used in dense UIs** (tables, sidebars). → check: variant exists OR an explicit "single density" decision.
5. **A11y baseline**: contrast ratio (≥4.5:1 text, ≥3:1 non-text), focus indicator visible, no color-only signaling. → check: WCAG AA verified with a tool.
6. **Hand-off** — Figma spec links the implementing component; tokens used are listed. → check: a frontend dev can build it from the spec without asking.

## Checklist (design system change)

1. Token name describes the role, not the value (`color-bg-danger` not `color-red-500`). → check: rename a value in light vs dark mode is a 1-line change.
2. Breaking change to a token = major version + migration note. → check: changelog entry exists.
3. Reference component(s) updated in the same PR as the token. → check: nothing left using the old token.

## Anti-Patterns

- **Magic numbers** — `padding: 14px` for no reason. Use the spacing scale.
- **Color-only signaling** (red border = error, no icon/text). Fails for ~8% of users with color vision differences.
- **Designing only the happy path.** Empty / loading / error states get drawn at the end and look bolted on.
- **Pixel-perfect at 1440px, broken at 320px.** Mobile-first or no-first; pick.
- **Reinventing the dropdown / modal / tooltip.** Use Radix / Headless UI / ARIA Authoring Practices. Hand-rolled = a11y debt.
- **Inconsistent corner radii / shadow scales.** That's the eye saying "not a system." Audit and consolidate.

## Related skills

- [[design-ux-architect]] — when the issue is layout / IA / nav, not visual treatment
- [[design-brand-guardian]] — when the question is "does this match the brand" not "is the system right"
- [[engineering-frontend-developer]] — handoff partner; tokens / states the engineer implements

## References

- `references/design-tokens.md` — naming conventions, hierarchy, light/dark, density
- `references/states-checklist.md` — what each component state must communicate
- `references/handoff-template.md` — Figma → dev handoff spec shape
