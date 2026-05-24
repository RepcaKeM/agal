# Accessibility + mood-testing

## Respect motion preferences

```css
@media (prefers-reduced-motion: reduce) {
  .whimsy-animation { animation: none; }
  .whimsy-transition { transition: none; }
}
```

If a user has reduced-motion set, your celebration confetti / page transitions / spinning emoji should respect that. Vestibular conditions are real; nausea isn't whimsy.

## Emoji and alt text

- Decorative emoji in copy: include via `<span aria-hidden="true">🎉</span>` so SR users don't hear "party popper emoji" while reading.
- Informational emoji (when emoji conveys meaning) needs accessible text alternative.
- Don't rely on emoji to carry information — accompany with text.

## Color and dark mode

- Whimsy that depends on color (red error icon as a sad face) needs an accessible alternative.
- Dark mode often breaks playful illustrations designed for light backgrounds. Audit.

## Translation

- Idiom-heavy whimsy doesn't translate. "We're cooking with gas" → 🤷‍♂️ in 80% of languages.
- Use a localization pass on every whimsy line. Some are tied to English idiom and need rewriting per locale.

## Mood-testing prompts

Read the whimsy as if you were:

- **A user who just lost work to a bug**. Does the next celebration land or sting?
- **A user using this for the 500th time today (data entry job)**. Is the whimsy in their way?
- **A user receiving bad news in life that day**. Does the cheerful empty state feel insensitive?
- **A user with English as a second language**. Is the joke / idiom comprehensible?
- **A user with a screen reader**. Does the personality come through, or does it sound like noise?

If your whimsy fails any of these, soften, contextualize, or remove.

## The repeat test

Click the same flow 20 times. By click 5, does the celebration feel rewarding or annoying? Whimsy that survives the repeat test is keeper material. Whimsy that gets annoying needs a "you've seen this" path.
