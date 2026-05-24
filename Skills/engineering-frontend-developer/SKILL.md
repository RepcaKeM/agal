---
name: engineering-frontend-developer
description: Implement UI components, manage state, integrate APIs, and meet Core Web Vitals on React/Vue/Angular/Svelte. Use when building a new component, fixing a re-render / state bug, optimizing bundle / runtime perf, or hitting accessibility requirements.
---

# Frontend Developer

## Overview

Most frontend bugs are state bugs, most perf wins are loading wins, and most accessibility failures are missing labels. This skill keeps you focused on those three before reaching for shinier abstractions.

## When to Use

- Building or modifying a UI component
- Fixing a re-render loop, stale state, race condition, or hydration mismatch
- Bundle is too big / LCP too slow / interaction janks
- Adding interaction that must work with keyboard + screen reader
- Integrating a new API into the UI (loading / error / empty states)

## Iron Law

```
EVERY INTERACTIVE COMPONENT SHIPS WITH: KEYBOARD PATH · ARIA LABEL ·
LOADING STATE · ERROR STATE · EMPTY STATE.

A button without keyboard access is broken. A list without an empty
state is a bug report waiting to happen. "Happy path only" is not done.

NO PREMATURE useMemo / useCallback. Measure first; most are noise
and obscure the real re-render cause.
```

## Checklist (per component)

1. **Define the states explicitly**: loading, empty, error, success, partial. → check: each state is rendered in Storybook / dev playground and looks right.
2. **Keyboard path**: tab order, focus visible, Esc closes modals, Enter/Space activate. → check: navigate the feature without touching the mouse.
3. **Semantic HTML + ARIA** — `<button>` not `<div onClick>`, `aria-label` on icon-only buttons, `aria-live` for async updates. → check: passes `axe` in dev tools.
4. **Owns its own state minimally** — lift only what's shared. Don't put server data in component state; use a query lib (TanStack Query, SWR, RTK Query). → check: no `useEffect` to fetch on mount.
5. **Render cost** — for lists >100 items, virtualize. For frequent updates, profile re-renders (React DevTools Profiler) BEFORE adding memoization. → check: render count matches expectation; no parent-driven full re-renders.
6. **Bundle impact** — heavy deps lazy-loaded (`import()` on route or interaction). → check: route-level chunk size budget; new dep doesn't blow it.

## Checklist (per perf regression)

1. **Reproduce with throttling** — CPU 4× slowdown, Network "Fast 3G" in DevTools.
2. **Measure first, change second** — Performance tab, LCP/CLS/INP attribution, React Profiler. Save the trace.
3. **Diagnose**: which Core Web Vital? — LCP = loading; CLS = layout shift; INP = interaction handler cost.
4. **Fix the cause, not the symptom** — see `references/perf-playbook.md` for fix per metric.
5. **Re-measure** — same trace conditions. Show before/after numbers.

## Anti-Patterns

- **`useEffect` to fetch on mount.** Use a query library; you get cache, dedup, refetch, and SSR for free.
- **`useMemo` / `useCallback` everywhere "for perf"** without a profile. They cost the comparison every render and often re-create their deps anyway.
- **State in localStorage as source of truth.** It's a cache, not a database. Stale across tabs, lost on storage clear.
- **`onClick` on a `<div>`.** Loses keyboard activation, semantic role, focus ring, and Enter/Space handling. Use `<button type="button">`.
- **Index as React `key` on a reorderable list.** Breaks identity → wrong state moves with the wrong row.
- **CSS-in-JS in the hot path.** Runtime style generation tanks INP. Use compiled CSS for components rendered often.
- **Importing the whole `lodash` / icon set / chart library.** Use per-function imports or a tree-shakeable variant.

## Related skills

- [[design-ui-designer]] — when the spec / tokens you're implementing need design-system pass
- [[design-ux-architect]] — when layout / nav / template grammar is what's actually wrong
- [[systematic-debugging]] — for the state / hydration / race bugs that look frontend-only but aren't

## References

- `references/perf-playbook.md` — LCP / CLS / INP attribution → fix table
- `references/a11y-checklist.md` — patterns: dialog, combobox, tabs, menu, live region
- `references/state-decision-tree.md` — local / lifted / context / store / server-state
- `references/virtualized-table.tsx` — example: TanStack Virtual + a11y-correct row semantics
