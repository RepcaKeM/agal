# Layout primitives (Every Layout style)

Composable CSS components that solve 90% of layout. Give engineers these; avoid bespoke flex/grid per page.

## Stack — vertical rhythm
```css
.stack > * + * { margin-block-start: var(--space-md); }
```
Use for: paragraphs, form fields, dashboard cards.

## Cluster — horizontal group that wraps
```css
.cluster { display: flex; flex-wrap: wrap; gap: var(--space-sm); align-items: center; }
```
Use for: button rows, tag lists, nav links.

## Sidebar
```css
.sidebar { display: flex; flex-wrap: wrap; gap: var(--space-md); }
.sidebar > :first-child { flex-basis: 16rem; flex-grow: 1; }
.sidebar > :last-child { flex-basis: 0; flex-grow: 999; min-inline-size: 50%; }
```
Use for: docs (nav + content), settings (menu + panel).

## Cover — full-viewport hero
```css
.cover { display: flex; flex-direction: column; min-block-size: 100vh; }
.cover > * { margin-block: auto; }
.cover > :first-child { margin-block-start: 0; }
.cover > :last-child  { margin-block-end:   0; }
```

## Grid — true responsive grid
```css
.grid {
  display: grid;
  gap: var(--space-md);
  grid-template-columns: repeat(auto-fit, minmax(min(20rem, 100%), 1fr));
}
```

## Switcher — N items in a row, stacking when no longer fit
```css
.switcher {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-md);
}
.switcher > * { flex-grow: 1; flex-basis: calc((40rem - 100%) * 999); }
```
