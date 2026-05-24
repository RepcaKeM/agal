# Design tokens — naming and hierarchy

## Three layers
1. **Primitive** — raw values. `color-blue-500`, `space-4`, `font-size-14`.
2. **Semantic** — role-based aliases. `color-bg-primary` → `color-blue-500`.
3. **Component** — per-component aliases. `button-bg-primary` → `color-bg-primary`.

Apps and components use **semantic or component tokens, never primitives.** Primitives can be renamed; semantic tokens are the API.

## Color
- Role-based names: `bg-surface`, `bg-surface-raised`, `bg-danger`, `text-primary`, `text-muted`, `border-default`, `border-focus`.
- Pair with intent suffix: `-default`, `-hover`, `-active`, `-disabled`.
- Light + dark: same semantic name resolves to different primitives per theme.

## Spacing
- One base scale: `0, 2, 4, 8, 12, 16, 24, 32, 48, 64, 96` (px or rem). No `14px` exceptions.
- Negative space is more important than positive: padding/gap should be larger by default than instinct suggests.

## Typography
- Scale max ~6 sizes: `xs, sm, base, lg, xl, 2xl`. Heading sizes derive from this.
- Pair with `line-height`, `letter-spacing`, `font-weight` as one token per role (`text-body`, `text-heading-md`).

## Radius / elevation
- Radius scale: `none, sm, md, lg, full`.
- Elevation scale: `0, 1, 2, 3` (each pair: blur + opacity, light + dark).

## Density (optional)
If your app needs compact / regular / spacious modes, the spacing scale gets a density multiplier and component padding tokens use it.
