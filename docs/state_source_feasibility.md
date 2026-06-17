# US State Business-Data Feasibility Map

**Goal:** decide *how* Porter Verify acquires business-registration data directly
(the "build Cobalt" approach), state by state, ordered by **legal risk** and
**engineering cost**. This is the prerequisite the team chose before building any
real state connector.

> **Honesty note.** No single official API covers all US businesses; each state runs
> its own Secretary-of-State (SOS) system (verified via research below). Entries
> marked **✅ verified** are confirmed from a named source; entries marked
> **⚠️ unverified** are the conservative default (assume live-query/scraping until a
> portal check proves otherwise). **Verify a state before building its connector** —
> do not build on an unverified row.

## How a "build Cobalt" system actually works

Cobalt's own model: *every live API request goes directly to the official SOS
website for the requested state, pulls the current record, and normalizes it* — i.e.
**per-state live querying/scraping** across all 50 states (officers in ~28). That is
the moat: 50 adapters + anti-bot handling + perpetual maintenance. Our
`SourceConnector` contract is built for exactly this — **one connector per state**.

## Tier definitions

| Tier | Meaning | Legal risk | Build effort |
|------|---------|-----------|--------------|
| **F — Federal API** | Official free federal API | None | Low |
| **A — Open data / bulk** | State publishes a free/paid downloadable dataset or open-data API | None (licensed/open) | Low–Med (ingest a file) |
| **B — Portal, no bulk** | Public search portal, no API/bulk → live query | **Needs legal review** | Med–High (scrape + parse) |
| **C — Restricted** | Anti-scraping rules, paywalls, or CAPTCHA-hardened | **High — legal sign-off required** | High |

## Tier F — Federal (build now, legal)

| Source | Provides | Access | Status |
|--------|----------|--------|--------|
| **OFAC** sanctions | SDN + consolidated lists | Free official files | ✅ build now (no key) |
| **SAM.gov** Entity API | Federal registration, UEI, CAGE, exclusions | Official REST + bulk (free key) | ✅ build now (needs a free API key) |

## Tier A — Open data / bulk (build now, legally clean)

These have a confirmed free or licensed dataset — ingest the file, no scraping.

| State | Source | Status |
|-------|--------|--------|
| **Colorado** | `data.colorado.gov` "Business Entities in Colorado" (1M+ records, free) | ✅ verified — **recommended pilot** |
| **Connecticut** | `data.ct.gov` open data + SOTS bulk data | ✅ verified |
| **Oregon** | State Open Data API | ✅ verified |
| **Ohio** | SOS free monthly bulk files | ✅ verified |
| **Arkansas** | SOS Corporation Bulk Data Download | ✅ verified |
| **Minnesota** | MBLS bulk data (free for non-commercial; confirm Porter's use class) | ✅ verified (license caveat) |
| **California** | SOS "Master Unload" bulk files ($100) | ✅ verified (paid) |
| **Texas** | Comptroller open data portal (registration subset) | ✅ verified (scope check needed) |
| **Washington** | High open-data rating; CCFS data | ⚠️ verify bulk/download path |
| **Iowa** | Noted as open-data friendly | ⚠️ verify dataset |
| **Illinois** | Recently removed fees **and** anti-scraping rules; data now open | ✅ verified (newly opened) |

## Tier B / C — Live query or restricted (legal review required)

The remaining ~38 jurisdictions (incl. DC, PR, USVI) have **no confirmed free
bulk/API** and default to **live-query/scraping**, which requires Porter legal
sign-off per state (ToS, and — important — *scraping legality varies by state*:
Illinois criminalized it until a recent reform). Treat all of these as
**⚠️ unverified → Tier B/C** until a portal check says otherwise:

`AL AK AZ FL GA HI ID IN KS KY LA ME MD MA MI MS MO MT NE NV NH NJ NM NY NC ND
OK PA RI SC SD TN UT VT VA WV WI WY · DC PR USVI`

(Several of these *may* have open data — e.g. some publish on Socrata; each needs a
5-minute portal check that moves it up to Tier A. This list is the safe default, not
a verdict.)

## Recommended build order

1. **Tier F now:** real **OFAC** connector (no dependency) → then **SAM.gov** (needs your free API key). *(OFAC connector is being built in this slice.)*
2. **Pilot Tier A state — Colorado:** free full dataset; build a real bulk-ingest
   connector end-to-end behind the existing contract. Proves the real-data path
   with zero legal risk.
3. **Remaining Tier A states:** CT, OR, OH, AR, IL, CA, TX, MN — each a bulk-ingest connector.
4. **Tier B/C (only after legal sign-off):** live-query connectors using the
   approved scraping tooling, prioritized by Porter's actual lead volume per state.
   Each state: ToS review → connector → contract tests → monitoring for site changes.

## Legal & operational guardrails (per plan §15, Risk #4)

- **No scraping without written legal sign-off** — confirmed varies by state.
- Respect robots.txt, rate limits, and per-state ToS; prefer official bulk/open data
  wherever it exists.
- Each connector preserves the **raw** response (already enforced) for auditability.
- Budget for **maintenance**: live-query connectors break when states change their
  sites — this is the ongoing cost the plan's risk register calls out.

## Sources

- [LLC University — SOS business search, all 50 states](https://www.llcuniversity.com/50-secretary-of-state-sos-business-entity-search/)
- [OpenCorporates — why US company data is hard](https://blog.opencorporates.com/2025/05/28/why-is-it-so-hard-to-find-us-company-data/)
- [Colorado open data — Business Entities](https://data.colorado.gov/Business/Business-Entities-in-Colorado/4ykn-tg5h)
- [Connecticut SOTS — Bulk Data and Images](https://portal.ct.gov/SOTS/Business-Services/Bulk-Data-and-Images)
- [Arkansas — Corporation Bulk Data Download](https://portal.arkansas.gov/service/ar-corp-bulk-data-download/)
- [Cobalt Intelligence — multi-state SOS coverage](https://blog.cobaltintelligence.com/post/cobalt-intelligence-secretary-of-state-api-multi-state-coverage-jurisdiction-tracking)
- [Middesk — Secretary of State API overview](https://www.middesk.com/blog/secretary-of-state-api)
