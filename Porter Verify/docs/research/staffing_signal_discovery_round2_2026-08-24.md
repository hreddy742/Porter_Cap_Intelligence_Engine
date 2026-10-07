# Lead-scoring signal discovery — round 2 — 2026-08-24

Continuation of the round-2 discovery batch launched (and cut off mid-run) in the
2026-08-21 session ([full transcript](./session_2026-08-21_full_transcript.txt),
lines 3690+). Six finder agents each live-tested one candidate signal category;
a separate adversarial verifier independently re-ran the live claims for each
before any verdict was accepted. Round 1's validated result (NY State Tax
Warrants as a real distress signal) is not repeated here — this is additive.

## Summary table

| # | Signal | Verdict | Build it? |
|---|---|---|---|
| 1 | Website timeline forensics (RDAP / Wayback / crt.sh) | **RDAP: WORKS. Wayback: works but flaky. crt.sh: broken. "Domain age ≈ company age": OVERSTATED** | RDAP registration-date only, as one weak weighted feature |
| 2 | State PEO registration/licensing | **CONFIRMED-WORKS** | Yes — TX, FL, NC all free/live/open |
| 3 | County money judgments + federal tax liens | **CONFIRMED-WORKS, fragmented** | Yes, but per-county connector work; NYC/ACRIS bot-blocks scripts |
| 4 | NY tax-warrant recurrence pattern mining | **WORKS but OVERSTATED** | Yes, with mandatory `warrant_id` dedup; "staffing recurs more than average" is unproven |
| 5 | UCC amendment mining (collateral-increase detection) | **OVERSTATED** | Amendment-type detection yes; "collateral increase" signal no |
| 6 | Weak contextual signals bundle (5 sub-items) | **2 of 5 WORK** (registered-agent proxy, state ESD grants); 3 broken/useless | Build #1 and #3 only |

## 1. Website timeline forensics

- **RDAP (rdap.org)** — the standout. Free, fast, no auth, no rate-limiting hit. Returns a clean domain-registration date for effectively any gTLD. Reproduced byte-for-byte by the independent verifier.
- **Wayback Machine CDX API** — mechanically free and real, but Internet Archive was mid-outage during testing (`503`/timeout on repeated calls) — needs retry/cache, not a synchronous dependency. Also structurally weak for the target population: brand-new small LLC sites are under-crawled, so sparse snapshot history looks like "unestablished" even for a legitimately growing company.
- **crt.sh** — confirmed broken (502 Bad Gateway) on 5/5 test domains including global controls (google.com, example.com), independently reproduced by the verifier. Known single-maintainer service with recurring outages — don't build on it without a fallback.
- **Core premise ("domain age ≈ company establishment")** — demonstrated noisy on live data: a 2001-registered domain (`staffagency.com`) currently reads as a generic template/lead-gen page, consistent with being resold to a brand-new LLC (false positive: looks established, isn't). The reverse is also common and non-suspicious: a real company operates as a DBA for years before incorporating, so the domain legitimately predates the LLC (false negative on any simple "domain older than LLC = suspicious" rule).
- **Verdict: use RDAP registration date as one weak input; do not build a standalone "site-establishment score" on this category.**

## 2. State PEO (Professional Employer Organization) registration

Distinct population from the general staffing-agency licensing already used in this project (PEO = co-employment/payroll/HR, not worker placement) — confirmed via Massachusetts, which runs both registers separately.

- **Texas**: `data.texas.gov/resource/7358-krk7.json?license_type=Professional Employer Organization` — free Socrata API, 501 current licensees (name, address, phone, expiration, geocoded). Live-reproduced exactly by the verifier. *Correction*: the original finder's claim that Texas licenses staffing agencies under a separate program was checked by the verifier and found unsupported — TDLR's combined dataset has no general staffing/employment-agency license category at all. Drop that comparison point; the PEO-license fact itself stands.
- **Florida**: `www2.myfloridalicense.com/sto/file_download/extracts/lic63elc.csv` — free CSV, 1,104 rows, 161 active PEO ("EL") entities including major players (Insperity, Paychex PEO). Reproduced exactly.
- **North Carolina**: originally left untested by the finder — the verifier found it in two minutes: `files.nc.gov/insurance/2026-07/Active PEO Listing .csv`, free, no auth, 256 companies. This should be added as a third confirmed source, upgrading the original's count from "2 of 5 states" to **3 of 5**.
- **New Jersey**: confirmed gated — only paper forms, no public roster.
- **Massachusetts**: inconclusive — Cloudflare 403 blocked both the finder's and verifier's automated attempts; the state's own page claims it publishes an Excel list, matching the pattern this project already uses for MA DLS. Needs a real-browser check, not ruled out.

## 3. County money judgments + federal tax liens

- Real, free, unauthenticated: **SearchIQS** (searchiqs.com) is the shared vendor platform behind dozens of NY (and CT/ME/NJ/PA/RI) county clerk offices. "Search as Guest" needs no login/CAPTCHA. A live test on Oneida County for party name "Smith" + Document Group = Judgments returned a real multi-thousand-record result set with full docket detail (viewing free, only document images cost $0.65/page). The verifier's own attempt lost browser-session state mid-task and couldn't reproduce the exact row count, but independently confirmed every other mechanic (guest access, the county list, and the document-type taxonomy).
- **Federal tax liens are filed at the same county-clerk level**, in the identical free interface, as a distinct document type (`FEDERAL TAX LIEN`, `FEDERAL TAX LIEN RELEASE`, etc.) — verbatim-confirmed by both agents.
- **Illinois** runs a rare state-level combined UCC + Federal Tax Lien index (`apps.ilsos.gov`) — the original finder couldn't render it; the verifier did and confirmed it live.
- **NYC ACRIS is free for humans but explicitly detects and blocks scripted/automated access** ("Further access to ACRIS is denied... detection of automated scripts/robots") — confirmed verbatim by both agents. Any pipeline needs a human-in-the-loop or a different data path for the 4 NYC boroughs.
- **Bottom line**: real signal, but this is a 50-state/3,000-county patchwork of different vendors, not a single API — treat as a per-jurisdiction connector-building project, not a quick win.

## 4. NY tax-warrant recurrence pattern mining

Extends round 1's validated single-warrant signal by checking whether *repeated* warrants against the same company (over time) are a stronger distress indicator.

- The satisfied/released field (`warrant_satisfaction_date`) is real and populated — you can tell open vs. resolved warrants apart.
- **Critical structural gotcha, confirmed by both agents**: the dataset is an event log, not a warrant registry — a single warrant appears as two rows (Added, then Closed) when it resolves. Naively counting rows per company overstates recurrence. The verifier re-ran the exact dedup query and found the finder's own reported false-positive rate was itself **wrong in the safe direction** — 7 of 20 naive "multi-warrant" companies were lifecycle duplicates, not 5 as originally reported (54% overstatement, not 40%). **Any implementation must dedupe on `warrant_id`, and this matters more than the first draft said.**
- Real recurring-warrant examples exist and are dated/verifiable (e.g. Quality Assure Health Staffing: two distinct open warrants 10 months apart).
- **The stronger claim — "staffing companies recur more than other industries" — is not established.** The live sample (13/109 staffing-keyword companies, 11.9%) sits inside the statistical noise band of the dataset-wide base rate (9.6%, n=484K). Don't ship "staffing companies show elevated recurrence" as a fact; ship "open-warrant-count with mandatory dedup" as the defensible feature.

## 5. UCC amendment mining (collateral-increase detection)

- **Amendment TYPE is real, structured, and reliably scrapable** — Massachusetts's UCC portal exposes both a "Filing Type" (UCC-1 / AMENDMENT / ASSIGNMENT / CONTINUATION / TERMINATION) and a finer "Action" code (`InitialFiling`, `DebtorChange`, `Assignment`, `CollateralRestate`, `Continuation`) on the filing-history detail page. Independently reproduced byte-for-byte by the verifier, including a second cherry-pick check (a different amendment in the same result set) that confirmed the taxonomy isn't hand-picked to manufacture ambiguity.
- **"Collateral increase" is not a field the state exposes anywhere** — no dollar amount, no directional flag, ever, on any UCC-1/UCC-3. The one live collateral-touching example found (`CollateralRestate`) collapsed a long, specific collateral description down to generic "All ASSETS" — and it fired 30 minutes after a UCC-3 Assignment to a third-party lien-servicing agent, meaning it's much more likely a paperwork standardization from a lien changing hands than evidence of new borrowing.
- **Verdict: do not build a "growth watch" trigger on `CollateralRestate`** without manually reading the underlying PDF for each hit — the automatic interpretation would likely be wrong on real data.

## 6. Weak contextual signals bundle

| Sub-signal | Verdict | Notes |
|---|---|---|
| Registered-agent choice (formation-mill vs. corporate agent) | **WORKS, weak** | Real, live-tested on the project's own 11.6M-row Florida dataset. Needs a new index on `agent_name` (currently unindexed, full-table scan) and a maintained alias list — 20+ real spelling variants found for "Northwest Registered Agent" alone, including OCR-garbled ones. Correlational only, not causal. |
| Local business-journal "fastest growing" lists (Crain's, etc.) | **BROKEN** | Hard paywall, confirmed word-for-word by both agents. Not worth building — no free tier exists across the ACBJ/Crain's network. |
| State economic-development grant/tax-credit databases | **WORKS, and better than first reported** | NY's Empire State Development dataset (`data.ny.gov/resource/26ei-n4eb`) is free, 65,237 rows, has `recipient_name`/`ein`/`industry` fields, and — missed by the original finder — has a documented public REST API, not just a downloadable file. Genuinely clean, positive, low-noise signal. |
| Google Trends search-interest curve | **OVERSTATED / not worth building** | Confirmed blank for a real small-LLC name (no chart data reached the page at all) and separately hit a 429 rate-limit — exactly the population (brand-new tiny companies) that Trends structurally can't measure. |
| SOS filing velocity/frequency | **BROKEN — data doesn't exist yet** | Every ingested state connector (FL/CO/CT/OR) stores one current snapshot per entity, no filing-event history, no amendment/sequence field anywhere in the schema. Six more state tables (AL/GA/TN/TX/VA/MS) exist but are empty. Building this would mean switching the connectors to incremental/diff ingestion — a real new data-engineering project, not a bolt-on feature. |

## What actually changes in the pipeline

Worth building next, in priority order:
1. **State PEO registries** (TX, FL, NC — all free, live, structured) as a new connector, distinct population from existing staffing-agency sourcing.
2. **NY Empire State Development grants** as a positive-signal join (free REST API, already discovered fields).
3. **RDAP domain-registration date** as one weak input feature (not a standalone score) — skip crt.sh, treat Wayback as optional/cached.
4. **Tax-warrant dedup fix** — enforce `distinct warrant_id` counting in whatever already consumes the round-1 tax-warrant signal; the current naive approach measurably overstates recurrence.
5. **Registered-agent proxy** as a cheap additional weak feature on data already ingested, once `agent_name` is indexed and an alias list exists.

Explicitly **not** worth building: crt.sh dependency, Google Trends, Crain's-style paywalled lists, UCC "collateral increase" inference, or a "staffing companies recur more" claim (unproven at current sample size). County judgments/federal liens are real but scope as a dedicated multi-jurisdiction connector project, not a quick add — and NYC/ACRIS specifically requires a non-scripted access path.
