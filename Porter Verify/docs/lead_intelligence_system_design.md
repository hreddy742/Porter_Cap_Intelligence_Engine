# NY pilot — source validation addendum to the Cobalt plan

> **Superseded note**: the first version of this document proposed a
> competing architecture. It was wrong to do so — [`cobalt_analysis_and_plan.md`](cobalt_analysis_and_plan.md)
> already specifies a more complete data model and build order for this exact
> capability (§4, `source_observations` / `signals` / `lead_scores` /
> `lead_candidates` / `salesforce_outbox` / `lead_outcomes` / `compliance_cases`,
> plus the correct scoring contract with separated identity/intent/ICP/risk
> dimensions). **That document is the architecture.** This one now only
> contributes what the Cobalt plan doesn't have: live-tested, adversarially
> re-verified findings about which specific public data sources actually work,
> and the corrections an engineering review surfaced in the first draft.

## What was wrong in the first draft, and why

An engineering review (2026-08-24) caught five P0 and four P1 defects by
checking specific claims against the actual code and primary sources, not
trusting the draft. Recorded here so the mistakes aren't repeated:

1. **"Porter Verify can't notice new companies" was false.**
   [`recent_businesses.py`](../src/porter_verify/services/recent_businesses.py)
   already filters CO/CT/OR/OH entity tables for newly-formed, active,
   domestic, non-shell entities. [`UccExitSignal`/`UccLead`](../src/porter_verify/db/models/ucc.py:86)
   already implement a UCC-3-termination-to-tracked-sales-lead pipeline. The
   real gap is cross-source enrichment, identity resolution across sources,
   qualification, dedup, routing, and outcome measurement — not discovery
   itself.
2. **"Reuses existing Prefect orchestration" was false.** The actual scheduler
   is [`apscheduler.schedulers.background.BackgroundScheduler`](../src/porter_verify/scheduler.py),
   running in-process, cron-triggered. `pyproject.toml` has no Prefect
   dependency. An in-process scheduler is unsafe with multiple API replicas —
   every replica would run the same discovery job. For a first pilot: keep
   APScheduler, run one designated worker, and take a database advisory lock
   plus durable `ingestion_runs` rows so a crash mid-run is recoverable, not
   Prefect, unless real operational scale later justifies the migration
   (Cobalt plan's own recommendation).
3. **"Reuses the built Salesforce export path" was false.** [`salesforce.py`](../src/porter_verify/services/salesforce.py)'s
   `record_sync` explicitly raises `SalesforceNotConfiguredError` without a
   supplied client — it's a deliberately inert foundation, not a working
   integration. Production discovery needs the full thing: OAuth connected
   app, an approved field map, idempotent external IDs, an outbox with
   retry/dead-letter handling, duplicate-collision behavior, and inbound
   disposition/funded-outcome sync — all already scoped in the Cobalt plan's
   `salesforce_outbox` and `lead_outcomes` tables.
4. **The evidence-reuse proposal doesn't work as stated.** `RawSourceEvent.verification_run_id`
   and `EvidenceItem.verification_run_id` are both `nullable=False` in
   [`verification.py`](../src/porter_verify/db/models/verification.py:80).
   A discovery run cannot write through the existing evidence tables without
   a schema change. Use the Cobalt plan's generalized lineage instead:
   `ingestion_run → raw source artifact → source_observation → company-link
   decision → signal → scoring snapshot → lead candidate`, with every
   score-bearing fact carrying its source, parser version, event time,
   observation time, and identity-decision reference.
5. **The checklist scoring model was invalid.** Counting "how many signals
   cleared" gives identity (SOS record), ICP classification (PEO license),
   operations (website), financing visibility (UCC), distress (tax warrant),
   and positive capacity (grant/federal contract) interchangeable weight —
   they measure different things and shouldn't average together. The Cobalt
   plan's separated-dimension contract (`identity_confidence`, `evidence_quality`,
   `intent_strength`, `intent_recency`, `icp_fit`, `contactability`,
   `risk_penalty`, each 0..1, combined by a versioned weighted function, with
   weak identity forcing `Hold` regardless of other scores) is the correct
   model — adopt it as written.
6. **"No UCC lien found" was stated too absolutely.** UCC searches are
   jurisdiction-, date-, and exact-name-sensitive; a clean search result is
   not proof of no financing. Correct language: *"No matching UCC filing
   found under the searched legal names in the searched jurisdictions,
   processed through [date]."* A negative result must carry one of:
   `clear_search`, `not_covered`, `source_stale`, `search_incomplete`,
   `identity_uncertain`, `manual_review_required` — never a bare "clean."
7. **`SourceConnector` is the wrong contract for bulk/incremental ingestion.**
   [`base.py`](../src/porter_verify/connectors/base.py:83) only has
   `search()`/`fetch()`/`health()` — no cursor, watermark, pagination
   checkpoint, schema version, or tombstone handling. Don't force bulk
   registries into it. Add a separate ingestion contract —
   `discover(cursor, window) → page of raw observations + next cursor` —
   and leave `SourceConnector` as the interactive lookup contract it already
   is.

## Source-specific corrections

- **NY tax warrants**: the dataset begins 2025-07-01 and mixes warrants with
  satisfactions/vacates/amendments in the same table — lifecycle reduction by
  `warrant_id` is mandatory (confirmed live: naive row-counting overstated
  recurrence by ~54% in testing), and the historical-recurrence window is
  shorter than it first appears. The $2,000 materiality floor used in testing
  is a research heuristic, not a validated threshold — make it configurable
  and calibrate against actual accepted/funded outcomes once `lead_outcomes`
  data exists.
- **ESD grants and PEO registrations are ICP/operational-context signals, not
  distress or financing-intent signals.** ESD data is quarterly, project-level,
  and a positive signal of legitimacy/activity — it says nothing about present
  cash need. PEO rosters establish licensure/classification (including many
  large national and out-of-state PEOs) — they don't identify newly-formed
  companies or funding need on their own. Score them under `icp_fit`, not
  under `intent_strength`.
- **USAspending.gov matching must use the Recipient UEI, not name text.** SOS
  entity records generally don't carry a UEI — that bridge has to be built
  (e.g. a name/address candidate search against USAspending's own
  autocomplete, generating review candidates that a human or a high-precision
  matcher confirms before the UEI is trusted) rather than assumed away.

## Data-source coverage — live-tested, corrected

This table (from two rounds of adversarially-verified live research —
[Aug 21 transcript](research/session_2026-08-21_full_transcript.txt),
[round-2 report](research/staffing_signal_discovery_round2_2026-08-24.md))
is genuinely new information the Cobalt plan doesn't contain. Treat it as
input to that plan's `source_policies`/`source_quality_daily` tables, not as
a standalone roadmap — each row still needs a maintained record with official
URL, acquisition method, fee, terms, robots status, legal-approval status,
and last live-verification date, as the Cobalt plan's data model requires.

| Tier | States | Notes |
|---|---|---|
| Already ingested | CO, CT, OR, FL, **OH** (also used by `recent_businesses.py` — omitted from the first draft) | |
| Free/open, straightforward | CA, ID, NY, IA, MN, MT, NE, KY, WI, MD | CA's official master bulk unload is **$100**; only the weekly incremental feed is free — not a literal zero-spend initial load |
| Real data, paid/gated | AZ, AR, HI, ME, IL, IN, NC, ND, OK, WY, SC, SD, VT, WV, NJ | Budget decision, not an engineering blocker |
| Reachable, needs reverse-engineering | GA, DE, NM, PA, WA, RI, MO, NH, UT, MA | One bounded project per state |
| Automation prohibited by policy pending legal review | AL, VA, KS, LA, MI | `robots.txt: Disallow: /` is a crawler-policy signal per [RFC 9309](https://www.rfc-editor.org/rfc/rfc9309), not itself a legal determination — status is "pending source-owner/legal approval," not a permanent "never," and should be tracked as such in `source_policies` |
| Confirmed unreachable | AK, TN | AK: bot-hardened at every fetcher tier tried. TN: connection failure, not bot defense — needs retest from Porter's own network before concluding anything |

Porter's actual sales states (FL, TX, OK, NY, GA, AL): FL done; NY fully
buildable now with the richest validated signal set; TX has free PEO data but
paid-only full entity data (SOSDirect); GA is reachable but needs one-state
reverse-engineering, no free bulk found; OK requires a budget decision
($500/mo or $150/wk); AL needs a legal-policy decision, not engineering.

## Corrected build order

1. Reconcile fully with the Cobalt plan — this document is now a source
   addendum, not an alternative architecture.
2. NY vertical slice: NY entity snapshot → tax-warrant lifecycle reducer
   (dedup by `warrant_id`) → entity matching → human review → signal display.
   No auto-export.
3. Shadow evaluation: label at least 200 candidates; measure identity
   precision, accepted-lead precision, coverage, staleness, cost per accepted
   lead, before any Salesforce write.
4. Production controls: dedicated worker + DB advisory lock, durable retries,
   object-lock evidence, SSO, suppression rules, monitoring, Salesforce
   outbox.
5. Add ESD/PEO as ICP/operational context — not distress points.
6. Expand states by Porter's actual sales volume and measured ROI, not by
   which connector is easiest to write.

## Approval gates (from the engineering review, adopted as-is)

- False company-link rate below 1%.
- 100% of score-bearing facts linked to retrievable evidence.
- Unknown/uncovered states never represented as a negative ("no lien found")
  result.
- Sales-approved precision target met in shadow mode before any live export.
- Source freshness and schema-drift canaries working.
- Legal/source-policy approval recorded per source.
- Salesforce duplicate and retry tests passing.
