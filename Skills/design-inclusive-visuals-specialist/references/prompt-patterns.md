# Prompt patterns — getting past biased defaults

## Anatomy of a good human-subject prompt

```
[role/action] +
[age range] +
[ethnicity / cultural background, when representation matters] +
[body / physical specifics] +
[setting, contextually accurate] +
[lighting / camera / style]
```

## Examples (replace and adapt)

❌ "A doctor smiling at the camera in a hospital."
✅ "A South Asian woman in her 50s, doctor, mid-action examining an x-ray on a wall-mounted lightbox, white coat over a navy shalwar kameez, surgical clinic, natural light, documentary style."

❌ "An athletic person doing yoga."
✅ "A plus-size Black woman in her 40s holding a warrior II pose on a wooden floor, plain studio backdrop, warm side lighting, photographic, eye contact with the camera."

❌ "A successful CEO at their desk."
✅ "A man in his 60s with a visible hearing aid, light brown skin, gray hair, seated at a wooden desk reviewing printed documents, modest office with a window and plants, indirect daylight, editorial portrait."

❌ "A diverse group of friends laughing."
✅ "Four people in their 20s outside on a bench: one with vitiligo, one wearing a hijab, one in a wheelchair with sport rims, one with a curly red beard — sharing food from a takeout container, candid moment, golden hour, 35mm photography."

## Anti-patterns in prompting

- **"Beautiful" / "attractive" / "professional"** — model defaults bias hard on these words. Specify the actual attributes instead.
- **"Ethnic" / "exotic"** — vague, loaded, defaults to stereotype. Name the specific background.
- **"Disabled person" alone** — adds the disability as the subject. Instead: name the person, then the assistive device or condition in context.
- **Adding skin tone as the only diversity marker** — body, age, ability, style all matter.

## Iteration approach

Generate 4–8 images per prompt; pick from variations rather than refining endlessly. Save the prompts that work in a team-shared library.
