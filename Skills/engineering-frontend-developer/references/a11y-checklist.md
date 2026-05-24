# Accessibility patterns — the ones you reach for most

## Buttons / links
- **Action** (changes state, submits, opens modal) → `<button type="button">`
- **Navigation** (changes URL) → `<a href>`
- Icon-only → `aria-label="<verb> <noun>"` (e.g. "Delete row")

## Modal / dialog
- Use `<dialog>` element with `.showModal()` when possible (handles focus trap + Esc + backdrop).
- If not: manual trap — `aria-modal="true"`, focus the first focusable on open, restore focus on close.

## Forms
- Every input has a `<label for>` (visible). Placeholder is not a label.
- Error message linked via `aria-describedby`; element has `aria-invalid="true"`.
- Group related fields with `<fieldset><legend>`.

## Live regions (async updates)
- `aria-live="polite"` for non-urgent updates (toast saved).
- `aria-live="assertive"` only for errors that require immediate attention.
- Don't toggle the element in/out — change its text content; SR observes the live region.

## Tables
- `<table>` with `<thead>`, `<tbody>`, `<th scope="col">`. Don't fake with `<div>`s.
- Empty state inside the same `<tbody>` so SR users know the table is empty.

## Tabs / menu / combobox
- These are not "just CSS". Use a vetted library (Radix, Headless UI, ARIA Authoring Practices reference impl). Hand-rolled tab interaction is almost always broken for SR users.

## Quick checks
- Tab through your feature with no mouse — can you reach and operate everything?
- Run `axe` DevTools — fix Critical and Serious.
- Test with screen reader once per major feature (VoiceOver on Mac, NVDA on Win).
