# Chart picker — match the question

| Question | Best chart | Watch out |
|---|---|---|
| How has X changed over time? | Line chart (or area if cumulative) | Don't use bar for a continuous time series |
| How do categories compare? | Horizontal bar chart, sorted | Pies for >4 slices: don't |
| What's the distribution? | Histogram or box plot | Avg-only hides the shape |
| What's the relationship between X and Y? | Scatter plot (+ trend line, optional) | Correlation ≠ causation |
| What's the composition? | Stacked bar OR 100% stacked, OR small multiples | Stacked makes comparison hard — use small multiples |
| Where on the map? | Choropleth (for normalized data) or symbol map | Don't choropleth raw counts — normalize by population |
| Single number worth seeing? | Big number (BAN) + tiny sparkline + comparison | Don't put one number on a chart |
| Flow through stages? | Funnel or Sankey | Sankey overused; reach for it only when flow is the story |

## Universal hygiene
- Sort categorical bars by value, not alphabet (unless ordering is semantic).
- Direct-label series instead of legend when there are ≤4 series.
- Use color sparingly; gray everything but the highlighted series.
- Annotate the insight on the chart with an arrow + label.
