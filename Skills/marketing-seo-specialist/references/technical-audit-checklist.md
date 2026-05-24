# Technical SEO audit — full pass

## Crawl / index
- [ ] `robots.txt` — nothing important blocked
- [ ] `sitemap.xml` — submitted in Search Console; matches what should be indexed
- [ ] No accidental `noindex` on important pages
- [ ] No duplicate content (canonical chosen and self-referencing on primary)
- [ ] Faceted URLs not creating infinite crawl space (canonical or `robots: noindex` for non-canonical variants)
- [ ] 404 vs 410 used correctly (410 for permanently gone)
- [ ] Redirect chains ≤2 hops; no loops

## Performance / UX
- [ ] CWV pass on field data (CrUX), not just lab
- [ ] Mobile-friendly check passes
- [ ] No interstitials triggering "intrusive interstitial" penalty on mobile
- [ ] HTTPS everywhere; no mixed content

## On-page structure
- [ ] One H1 per page; logical heading hierarchy
- [ ] Image alt text descriptive (or empty for decorative); never keyword-stuffed
- [ ] Internal link graph: no orphan pages
- [ ] Breadcrumbs with structured data where helpful

## International
- [ ] `hreflang` correct (reciprocal + self-reference) on multi-locale
- [ ] `lang` attribute on `<html>`

## Structured data
- [ ] Schema present where eligible (Article, FAQ, Product, HowTo, Breadcrumb)
- [ ] Validates in Rich Results Test
- [ ] Doesn't claim FAQs that aren't on the page (recent abuse → eligibility removed)

## Monitoring
- [ ] Search Console: weekly review of Coverage, Performance, Core Web Vitals
- [ ] Log-file analysis on big sites: where is Googlebot spending its budget?
