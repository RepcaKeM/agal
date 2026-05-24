# Style guide

## Voice
- Second person ("you"), not "the user" or "one"
- Present tense for behavior, not future ("The API returns 200", not "will return")
- Active voice unless passive is genuinely clearer

## Words to avoid
- **easily, simply, just, obviously, of course, clearly** — they demean the reader and skip steps
- **trivial, straightforward** — same problem
- **leverage, utilize, robust, seamless** — marketing words; use plain alternatives
- **next-generation, world-class, revolutionary** — never

## Code blocks
- Specify the language for syntax highlighting: ​```bash, ​```python, ​```ts
- One concept per block
- Inputs and outputs labelled when both shown
- Pin versions in install commands where it matters
- Use `$ ` prefix for shell commands only if you also show output; otherwise no prefix

## Naming
- Product / project names always in the canonical capitalization (`PostgreSQL` not `Postgres SQL`; `npm` not `NPM`)
- Acronyms expanded on first use unless universally known (ATM, HTTP)
- API method names in `code font`, not Title Case

## Headings
- Sentence case ("Configure the client") not Title Case ("Configure The Client")
- Headings answer questions the reader is asking
- Skip "Introduction" / "Overview" — start with the content

## Links
- Link text describes the destination ("see the API reference"), not "click here" / "see this"
- External links open in same tab unless they'd lose state

## Numbers / units
- Spell out one through nine; numerals from 10
- Always include units (`50 ms`, not `50`)
- Money: include currency code on first mention (`USD 50`, then `$50`)

## Examples
- Use realistic data, not `foo / bar / baz` (unless intentionally generic)
- Don't use real user names unless given permission
- Truncate long outputs with `# …` rather than padding with placeholders
