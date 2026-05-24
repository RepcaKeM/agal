# Component states — what each must communicate

| State | Signal | Common miss |
|---|---|---|
| **Default** | What this thing is and does. | Affordance unclear (looks like text, not button) |
| **Hover** | "Mouse is here, click would do X." | Same as default → user unsure if clickable |
| **Focus-visible** | "Keyboard is here." MUST be visible. | Removed with `outline: none`; SR/keyboard users blind |
| **Active** | "Click in progress." | No press affordance → feels unresponsive |
| **Disabled** | "Can't be used now." Explain why. | Greyed out with no reason; user stuck |
| **Loading** | "Working, please wait." Don't replace the whole thing. | Full content replaced with spinner → layout shift, no context |
| **Error** | What went wrong + how to recover. | Generic "error" with no action |
| **Empty** | What this view would show + how to fill it. | Blank screen; user thinks it's broken |

## Specifically
- **Focus ring** must have contrast ≥3:1 against any background it can appear on.
- **Disabled** should still have ≥3:1 contrast with background so it's readable; reserve the lowest contrast for true noise.
- **Loading** prefer skeleton + preserve layout > replace-with-spinner.
- **Empty** include illustration + 1-sentence explanation + primary CTA.
