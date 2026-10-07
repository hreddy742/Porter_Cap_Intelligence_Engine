# CT Lien vs. Porter Verify — Evaluation Before Building Further

**Purpose:** decide whether Porter Verify is worth continuing, given Porter already
uses **CT Lien / iLien (Wolters Kluwer)**. Fill this in after talking to John.

> Bottom line up front: CT Lien is a strong, licensed **data source**. Porter Verify
> is only worth continuing if Porter wants a **workflow/automation/system-of-record
> layer on top** of that data. If occasional manual lookups are enough, CT Lien alone
> covers it. **Don't rebuild what CT Lien already does — orchestrate it.**

## Part 1 — Questions to ask John

### What we use from CT Lien today
- [ ] Which exact modules? (iLien UCC search, UCC **filing**, business **entity** search, bankruptcy/tax-lien/judgment/litigation, real-property?)
- [ ] Does it cover **entity verification** (is the company real/active/registered), or **UCC liens only**?
- [ ] Who uses it (sales / underwriting / ops) and for what step?
- [ ] How is it used — **manual portal** searches only? Any integration with Salesforce or our other systems?
- [ ] Roughly how many lookups/searches per month? Filings per month?

### Cost
- [ ] Pricing model: per-search? per-filing? per-seat subscription? annual contract?
- [ ] Total monthly / annual spend.
- [ ] Cost **per UCC search**, per **entity search**, per **filing**.
- [ ] Volume tiers / overage charges.

### API / integration availability (the key unlock)
- [ ] Is the **iLien API** available on our plan? At what extra cost?
- [ ] Can we **bulk search** and/or **export results (CSV)**?
- [ ] What would Wolters Kluwer charge to enable API access?

### Pain points (these justify a layer on top)
- [ ] Time spent per lookup, and per analyst per week.
- [ ] Manual re-keying of results into Salesforce / notes?
- [ ] Any auditable, timestamped record of what was checked and when?
- [ ] Do we re-check funded deals for new liens / dissolution (monitoring)?

## Part 2 — The decision

**Continue Porter Verify only if 2+ of these are true:**
- We verify **many** leads (manual one-at-a-time is a bottleneck).
- We want results **auto-pushed into Salesforce** / lead routing.
- We need a **Porter-owned, auditable system of record** (evidence + confidence + review + audit) for exams.
- We want **monitoring** (alert on new senior lien / dissolution on the funded book).
- We want **cost control** (route free sources — OFAC, state open data — first; reserve paid CT Lien lookups for when needed).

**Stop / don't build more if:**
- Lookups are occasional and manual is fine, and
- There's no need for Salesforce automation, an audit system of record, or monitoring.

## Part 3 — If we continue: the correct architecture

- **CT Lien / iLien = the primary rented data source** (entity + UCC), via its **API**
  (or CSV export until API is enabled). **Do NOT scrape states ourselves.**
- **Porter Verify = the owned platform** already built: company profiles, immutable
  evidence + audit, confidence scoring, review queue, Salesforce sync, async pipeline.
- Free sources (OFAC ✅ done, Colorado/other state open data) stay as **cost-saving
  fallbacks**.
- **Required to proceed:** confirm the iLien **API** (or export) — without it, the
  automation value can't use our best data source.

## Part 4 — Rough cost comparison to complete after John

| | CT Lien alone (today) | CT Lien + Porter Verify (layer) |
|---|---|---|
| Data cost | CT Lien spend (fill in) | Same CT Lien spend, **minus** lookups served by free sources |
| Labor | Manual searches + re-keying (analyst hours) | Mostly automated |
| API / integration cost | — | iLien API fee (fill in) + app hosting (low) |
| Audit / monitoring | Manual / none | Built in |
| One-time build | — | Remaining dev to wire CT Lien + Salesforce |

## Status of what's already built (sunk, reusable)
Working platform on branch `claude/porter-verify-mvp`: verification pipeline,
immutable evidence + audit, explainable scoring, review workflow, RBAC API, React
dashboard, async backbone, real OFAC screening, a Colorado open-data connector
(proof the connector pattern works), Salesforce foundation. All of this is the
"layer on top" — none of it competes with CT Lien.
