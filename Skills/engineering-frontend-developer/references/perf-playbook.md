# Core Web Vitals — attribution → fix

## LCP (Largest Contentful Paint) — slow loading
Diagnose: DevTools Performance → "LCP" marker; Lighthouse identifies the element.

| Cause | Fix |
|---|---|
| Hero image too big | `<img srcset>` + `sizes`, modern format (AVIF/WebP), `loading="eager"` + `fetchpriority="high"` ONLY for the LCP image |
| Web font swap | `font-display: swap`, preload critical font: `<link rel="preload" as="font">` |
| JS-rendered LCP element | SSR / static-render the LCP element so it's in initial HTML |
| Slow API blocking render | Skeleton / streamed render so LCP isn't gated on data |

## CLS (Cumulative Layout Shift) — visible content jumping
Diagnose: Performance Insights → "Layout shifts" timeline.

| Cause | Fix |
|---|---|
| Image without `width`/`height` | Always set both attributes (or `aspect-ratio` CSS) |
| Ads / embeds | Reserve fixed-size container before they load |
| Web font swap reshapes text | `size-adjust`, `ascent-override`, or preload font |
| Dynamic content inserted above viewport | Reserve placeholder height; don't shift existing content |

## INP (Interaction to Next Paint) — laggy clicks/typing
Diagnose: Performance → "Interaction" → long task attribution.

| Cause | Fix |
|---|---|
| Long JS task on click | Break with `scheduler.yield()` or `setTimeout(0)`; move heavy work to a Web Worker |
| Sync state cascade re-rendering huge tree | `useDeferredValue`, `startTransition`, or split state |
| Expensive CSS recalc (large selectors, complex grids) | Simplify selectors; `contain: layout paint` on islands |
| 3rd-party script (analytics) blocking input | Load via `defer`, or only on idle (`requestIdleCallback`) |

## Bundle size
- Per-route budget (e.g. 170 KB gzip). Fail CI when exceeded.
- `import()` heavy components at route boundary or interaction.
- `webpack-bundle-analyzer` / `rollup-plugin-visualizer` to find the offender.
- Modern target: drop polyfills for evergreen browsers (`browserslist: 'last 2 versions, not dead'`).
