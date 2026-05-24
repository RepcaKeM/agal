# Figma → dev handoff (one per component)

## Component
- **Name** (matches code component name):
- **Figma file + node link**:
- **Storybook URL** (after build):

## Anatomy
Label every part: container, slot(s), icon, label, helper, hint, etc.

## States
List which states this component must support (from `states-checklist.md`).
Link the Figma frame for each.

## Tokens used
- color: `color-bg-…`, `color-text-…`, `color-border-…`
- spacing: `space-…`
- typography: `text-…`
- radius / elevation: `radius-…`, `elevation-…`

## Behavior
- Responsive: min-width, max-width, wrapping
- Interaction: keyboard, screen reader, motion preferences
- Props / variants the engineer must expose

## Edge cases
- Long content (overflow handling)
- Empty content
- RTL / i18n considerations
- Density / dark mode

## Acceptance
- [ ] axe clean
- [ ] tab order natural
- [ ] focus ring visible
- [ ] matches Figma at 320 / 768 / 1440
