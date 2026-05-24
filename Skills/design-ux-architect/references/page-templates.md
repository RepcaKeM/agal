# Page templates — shapes most products need

## List template
- **Header** with page title + primary action (e.g. "+ New").
- **Filter / search / sort row** (sticky on scroll).
- **List** (table or card grid) — virtualized if >100 rows.
- **States**: empty (with CTA), loading (skeleton matching rows), error (with retry).
- **Pagination or infinite scroll** — pick one and stick to it.

## Detail template
- **Breadcrumb** to parent list.
- **Title + key metadata** (status, last updated, owner).
- **Primary action** + overflow menu for secondary.
- **Tabs or accordion** for grouped info (overview / activity / settings).
- **States**: not-found (with go-back), loading (skeleton of the layout).

## Form template
- **Single column** by default; two columns only when fields are short and related.
- **Group with `<fieldset>` + `<legend>`** when sections exist.
- **Inline validation** on blur, NOT on every keystroke.
- **Sticky submit** at the bottom for long forms.
- **Errors summary** at the top + per-field; both linked.

## Dashboard template
- **Filter bar** that scopes every widget (date range, segment).
- **KPI row** — 3–5 numbers at the top, biggest insight first.
- **Charts** below — one chart answers one question.
- **States**: no-data (per widget), partial-data (warn), error (per widget, not whole dashboard).

## Settings template
- **Sidebar nav** by category.
- **Section per panel** with clear save / cancel; never auto-save destructive changes.
- **Danger zone** at the bottom with red-bordered confirmation.
