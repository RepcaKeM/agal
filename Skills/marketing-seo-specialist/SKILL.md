---
name: marketing-seo-specialist
description: Technical + content SEO — page optimization, technical audit, search-intent mapping, internal linking, content strategy for organic growth. Use when optimizing a page for search, auditing crawl/index issues, building topical clusters, or planning content for organic traffic.
---

# SEO Specialist

## Overview

Most "SEO advice" is 2014 keyword-stuffing dressed up. Modern SEO is intent matching, technical hygiene, and topical depth. This skill keeps you on those three things and out of cargo-cult tactics.

## When to Use

- Optimizing a single page (or template) for organic traffic
- Technical SEO audit (crawl, index, Core Web Vitals, structured data)
- Mapping content to search intent (info / nav / commercial / transactional)
- Designing topical clusters / hub-and-spoke content
- Diagnosing a traffic drop or post-update recovery

## Iron Law

```
INTENT MATCH BEFORE OPTIMIZATION. If your page doesn't match what the
searcher wants, no on-page tweak will save it. Look at the SERP for
the query — what's ranking, what FORMAT (list, video, calculator,
product page)? Your page must match that format or you don't compete.

NO TACTIC THAT VIOLATES GOOGLE'S OWN GUIDELINES. No PBNs, no link
exchanges, no AI-generated topical mass with no human pass.
Today's "growth hack" is tomorrow's manual action.
```

## Checklist (single-page optimization)

1. **Pick the primary query** — high enough volume to matter, intent matches your page. → check: query has search volume in your tool; SERP screenshot saved.
2. **SERP analysis** — what format ranks (article / video / product / list / tool)? → check: your page format matches.
3. **Title tag**: includes primary query in natural language, ≤60 chars. → check: doesn't get truncated.
4. **H1 = page's promise**, not the exact keyword. The page can rank for many variants when the topic is clear.
5. **Meta description**: a promise + a hook, ≤155 chars. CTR-optimized, not keyword-stuffed.
6. **Subheads (H2/H3)** answer related questions a searcher would ask. → check: matches People-Also-Ask for the query.
7. **Internal links** to the page from relevant existing pages (cluster connection). → check: ≥3 contextual internal links pointing in.
8. **Structured data** when applicable (Article, FAQ, Product, HowTo). → check: validates in Rich Results Test.
9. **Core Web Vitals pass** (LCP < 2.5s, INP < 200ms, CLS < 0.1). → check: PageSpeed Insights field data.

## Checklist (technical audit)

1. **Crawlability**: `robots.txt`, `sitemap.xml`, no accidental noindex, no infinite faceted URLs. → check: GSC coverage report clean of "Excluded" surprises.
2. **Indexation**: canonical tags correct (self-referencing on primary, point alternates), no duplicate content. → check: `site:` query shows expected pages.
3. **Performance**: Core Web Vitals from real user data (CrUX), not just lab.
4. **Mobile-first**: GSC validates mobile usability; layout works on 360px.
5. **HTTPS, hreflang (if multi-locale), canonical chains**: each verified.
6. **Schema markup**: present where it adds eligibility for rich results; validates.
7. **Internal link graph**: no orphan pages; cluster pages link to their hub.

## Anti-Patterns

- **Keyword stuffing.** Reads as spam; Google's been on this for 15 years.
- **Exact-match anchor text spam** in internal links — looks unnatural.
- **AI-generated content at scale with no editorial pass.** Helpful-content / spam updates target this directly.
- **Cloaking** (showing different content to bot vs user) — manual action territory.
- **Buying links / link exchanges**: short-term up, long-term penalty.
- **Optimizing for "search volume" only.** A 10/mo query with high commercial intent beats a 10,000/mo info query for revenue.
- **Treating SEO as a one-time launch task.** Pages need refresh as competition and SERP evolve.

## References

- `references/serp-analysis.md` — how to read a SERP in 5 minutes
- `references/intent-types.md` — info / nav / commercial / transactional with examples
- `references/technical-audit-checklist.md` — full crawl-to-index hygiene pass
- `references/topical-cluster-template.md` — hub-and-spoke architecture
