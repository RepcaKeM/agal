---
name: engineering-technical-writer
description: Developer documentation — API references, README files, tutorials, conceptual guides, runbooks. Use when writing or restructuring developer-facing docs, drafting an API reference, building a tutorial from a working example, or adding a "getting started" path.
---

# Technical Writer

## Overview

Most developer docs fail one of two ways: incomplete reference (users guess) or "smart-sounding" narrative (users skim past the answer). This skill makes you write to the specific question the reader has, then verify the example actually runs.

## When to Use

- Writing or restructuring a README, getting-started, or tutorial
- Drafting / reviewing API reference
- Adding conceptual docs ("how it works", "when to use X vs Y")
- Building a runbook for a system or feature
- Cleaning up doc drift after a code change

## Iron Law

```
EVERY CODE BLOCK IN DOCS RUNS AS WRITTEN. NO EXCEPTIONS.

Copy the snippet, paste it into a fresh environment, run it. If it
errors or needs un-documented setup, fix the doc (or the example, or
both). Docs that look right but don't run break trust permanently.

EVERY DOC PAGE NAMES ITS READER + THEIR QUESTION AT THE TOP. If you
can't, you don't know what to write.
```

## Diátaxis (the four doc types — confusing them is the #1 doc problem)

| Type | When | Reader needs |
|---|---|---|
| **Tutorial** | First-time user | A guided experience that produces a working result; theory is held back |
| **How-to guide** | User with a specific task | Steps to accomplish it, NOT general explanation |
| **Reference** | User who knows what they need | Exhaustive, accurate, no narrative |
| **Explanation** | User asking "why" / "how does this fit" | Conceptual model; can be opinionated |

Mixing types in one page is the most common writing error. A reference shouldn't teach; a tutorial shouldn't be exhaustive.

## Checklist (any page)

1. **Top of page**: who this is for, what they'll know/do after. → check: a stranger lands here and reads the first 30 words to decide if it's for them.
2. **One page = one doc type** (tutorial / how-to / reference / explanation). → check: page does one job.
3. **Examples** copy-pasteable and tested. → check: copy → fresh env → runs.
4. **Versioned** if API surfaces evolve. → check: version pinned in code blocks; doc URL has version path if multiple are supported.
5. **No "easily" / "simply" / "just".** They demean the reader and hide complexity. → check: text search for these; replace with the actual steps.
6. **Next link** — what to read next. Don't leave the reader at a dead end.

## Checklist (API reference)

1. Every endpoint / function: signature, parameters with types + required/optional, return type, errors. → check: nothing "see source for details."
2. **One minimal request example** per endpoint, with one realistic response.
3. **Error responses documented**: code, meaning, what to do.
4. **Generated from the source** where possible (OpenAPI, TS definitions, docstrings). Hand-written drifts. → check: regen workflow exists in CI.

## Checklist (README)

1. **First line**: what this project IS in one sentence. → check: a stranger gets it.
2. **Why use this** — two sentences. The category, the differentiator.
3. **Quick start** — minimal install + minimal run, copy-pasteable.
4. **Link out** for depth: docs site, examples, contributing.
5. **Status / maturity** if it matters (alpha / beta / production / archived).
6. **Maintainer or org** for trust + support expectations.

## Anti-Patterns

- **"Here is how X works"** preceding the API reference. Conceptual content belongs in Explanation, not Reference.
- **Tutorials that explain theory** for 3 paragraphs before any command. The reader bounces.
- **Examples with placeholder values** (`YOUR_API_KEY_HERE`) without saying where to get the key. Cheaper to link the page.
- **"For more information, see…" with no link.** Either give the link or write the info.
- **Marketing copy in docs.** Devs see through it; trust drops.
- **One giant doc page.** Split by reader task; cross-link.
- **Comments in code examples telling the reader what the code does.** The code is supposed to do that. Use comments only for context the code can't show (why, security note, performance note).

## References

- `references/diataxis-quickref.md` — when to write each type, with examples
- `references/api-reference-shape.md` — endpoint / function entry template
- `references/readme-template.md` — README sections in order, length guidance
- `references/style-guide.md` — voice, tense, prohibited words, code-block conventions
