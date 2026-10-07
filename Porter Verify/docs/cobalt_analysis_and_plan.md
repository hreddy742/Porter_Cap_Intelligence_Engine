# Cobalt Intelligence Analysis and Porter Lead Intelligence Build Plan

Version: 2.0
Date: June 18, 2026
Scope: public behavior and documentation only

## Evidence standard

- **Verified**: observed on Cobalt's public site, sign-in surface, or API documentation.
- **Inferred**: a reasonable architecture interpretation, not a claim about private code.
- **Unknown**: requires an authenticated product walkthrough, contract, or vendor answer.

The authenticated Quick Start URL redirects to sign-in in the available browser session.
Therefore, private dashboard layout, exact pricing, exports, saved-search behavior, user
management, and internal implementation are **unknown**. This document does not rely on
private APIs, bypass authentication, copy code/assets, or assume scraping permission.

## Executive recommendation

Cobalt is primarily a business-verification and underwriting data-access product. Its
publicly documented strengths are live Secretary of State (SOS) lookup, normalized
multi-state results, asynchronous jobs, batch CSV, source screenshots, UCC data where
available, TIN matching, sanctions screening, court cases, and API integration.

It is not publicly demonstrated as a complete outbound lead-generation system. Porter
should not clone it. Porter should use the best Cobalt patterns as one input to a larger,
owned lead-intelligence platform:

1. Buy or selectively ingest reliable verification data.
2. Preserve raw evidence and provenance.
3. Resolve each observation to a canonical company.
4. Detect time-bound funding-intent signals.
5. Rank evidence-backed Hot, Warm, and Cold opportunities.
6. Put reviewed, deduplicated leads into the existing Salesforce workflow.
7. Learn from sales outcomes before automating outreach.

The defensible asset is not another SOS API. It is Porter's labeled history connecting
signals, company identity, timing, salesperson action, and funded outcomes.

---

## 1. Cobalt product analysis

### 1.1 Problem and target users

**Verified problem:** alternative-finance teams manually visit inconsistent government
sites to confirm whether a company exists, is active, matches an application, and has
relevant officers, addresses, filings, or liens. Cobalt normalizes that work behind an
API and dashboard.

**Verified target users:** alternative lenders/funders, underwriting teams, processing
teams, KYB/compliance teams, and developers integrating verification into proprietary
systems. The public product page emphasizes faster underwriting and fraud reduction.

**Not publicly established:** prospect discovery, sales territory management, intent
monitoring, lead routing, contact sequencing, attribution, or closed-loop lead scoring.

### 1.2 Public user journey

1. User signs up or signs in.
2. User chooses Quickstart, Batch, Full Verification, Documentation, or Pricing.
3. In Quickstart, the likely flow is company/state input -> live lookup -> normalized
   result. Exact controls and result layout are **unknown** because authentication is
   required.
4. Batch users upload a CSV and receive SOS results in CSV form (**verified publicly**).
5. API users send an `x-api-key`, start a lookup, and receive either results or an ID to
   poll. Long jobs can send results to a callback URL.
6. Full Verification fans a name/person search across all 50 states plus DC and exposes
   partial state completion and historical requests.

### 1.3 Verified capabilities and data

| Area | Publicly verified behavior |
|---|---|
| SOS search | Search by business name, SOS/entity ID, person name, state, and optional address filters. |
| Freshness | `liveData=true` by default; cached lookup is optional; recent cached data may be returned when live lookup fails. |
| Async execution | Long state requests return `retryId`; polling and callback URL are supported. |
| Full verification | Starts all-state search with `searchGuid`; exposes per-state partial results and request history. |
| Business attributes | Name, status, filing date, formation/registration state, entity type, addresses, agent, officers, IDs, documents, history, assumed names, and selected contact fields. Coverage varies. |
| Evidence | Short-lived source-page screenshot URL where supported. |
| UCC | Optional UCC data where available; success is reported separately. Coverage is not universal. |
| Related businesses | Officer/agent names can be searched across states for related entities. |
| Entity matching | Candidate alternatives, `confidenceLevel`, `aiConfidenceLevel`, and address match indicators are returned. Exact algorithms are unknown. |
| TIN | Business name/TIN matching with IRS result codes, service status, and cached-check date. |
| Sanctions | Organization/person/vessel/aircraft fuzzy screening across multiple sanctions, debarment, PEP, and watchlist sources. |
| Court cases | Documented coverage for New York and Miami-Dade; async callback pattern. |
| Contractor licenses | Public docs list CA, FL, NY, and TX. |
| Delivery | Single lookup, API, CSV batch, polling, and callbacks. |
| Usage | API-key customer endpoint exposes usage and due date. |

### 1.4 Data collected, generated, and likely sourced

**Inputs collected:** API key, business/person name, state, entity ID, business/owner
address, TIN for TIN verification, callback URL, batch files, and optional search flags.

**Outputs generated:** normalized business records; alternatives and confidence values;
state-job status; screenshots; UCC, document, officer, history, sanction, and court-case
results; related-business links; and limited AI-generated review observations.

**Verified sources:** state SOS systems, IRS TIN matching, named sanctions/watchlists,
specified court systems, and supported contractor-license systems.

**Inferred implementation:** state-specific HTTP/browser adapters, per-state parsers,
job queues, cache, object storage, and schema normalization. Proxy/CAPTCHA services may
be used by this product category, but their use by Cobalt was not verified in this
review and must not be stated as fact.

### 1.5 Likely qualification and scoring

Cobalt publicly exposes candidate confidence and AI confidence, but not a published
decision model. It appears to support verification and underwriting triage rather than
sales-lead temperature. Likely matching inputs include normalized name, SOS ID, address,
state, and person association. This is **inferred** from request/response fields.

The documented full-verification example contains AI review flags for multiple related
businesses, inactive entities, young companies, and address differences. That is useful
analyst assistance, but it should not be treated as an auditable credit or lead score.

### 1.6 Strengths

- Broad state coverage behind one contract.
- Live-data option plus controlled cached fallback.
- Polling/callback pattern for slow sources.
- Rich source-specific fields without forcing one shallow record.
- Batch and API delivery support both operations and engineering users.
- Screenshots, document URLs, and timestamps help analysts validate results.
- Test modes allow integration without lookup charges.
- Per-capability success flags communicate partial coverage.

### 1.7 Weaknesses, gaps, and risks

- Coverage varies by state and field; a normalized field can look universal when it is not.
- Short-lived screenshot URLs are weaker than customer-owned immutable evidence.
- Confidence and AI fields are not publicly explainable or versioned.
- Public docs show inconsistent endpoint naming and large heterogeneous payloads.
- API-key-only examples do not establish enterprise SSO, fine-grained RBAC, or tenant controls.
- The public product is verification-led, not a proven intent-led sales pipeline.
- Live source automation creates reliability, legal/ToS, rate-limit, and maintenance risk.
- TIN, officer, address, and sanctions data require strict access, retention, and audit controls.
- Returning PII/contact fields does not itself establish permission for marketing use.

### 1.8 What Porter should learn and avoid

**Learn:** connector abstraction, live/cached modes, async job IDs, callbacks, partial
success, source screenshots, batch ingestion, test fixtures, and explicit coverage.

**Avoid:** copying UI/branding; treating vendor confidence as truth; broad collection
without purpose limits; building 50 brittle scrapers first; storing only normalized
records; hiding missing coverage; calling verification a Hot lead; or enabling automated
outreach before consent, quality, and suppression rules are proven.

---

## 2. Porter product definition

### 2.1 Product objective

Build an internal, evidence-backed lead-intelligence system that identifies businesses
with a plausible, timely need for factoring or working capital and gives sales a reason
to act. Every ranked lead must answer:

- Who is the canonical business?
- What changed, when, and at which source?
- Why might that change indicate funding need?
- How reliable and fresh is the evidence?
- Is the company eligible and safe to contact?
- Has Porter already worked, rejected, suppressed, or contacted it?
- What action should the rep take next?

### 2.2 Target users

- Sales reps: prioritized leads, evidence, contacts, and next action.
- Sales managers: territory load, pacing, conversion, and source ROI.
- Underwriting: verification, liens, identity, and risk context.
- Operations/reviewers: ambiguity, dedupe, suppression, and data corrections.
- Compliance/security: provenance, access, retention, and audit.
- Data/product teams: source health, model/version performance, cost, and outcomes.

### 2.3 Lead temperature contract

Temperature is not a synonym for business validity.

| Class | Meaning | Minimum conditions |
|---|---|---|
| Hot | Strong, recent funding-intent evidence and eligible company; prompt action is justified. | At least one high-value signal or corroborated medium signals; identity confidence above threshold; fresh evidence; no hard compliance/suppression block. |
| Warm | Plausible need or growth/change signal, but timing or identity is less certain. | One medium signal or multiple weak signals; verified active company; reviewable evidence. |
| Cold | Valid target profile without current intent evidence. | ICP fit and verified entity, but no timely signal. |
| Hold | Evidence is ambiguous, stale, duplicated, or incomplete. | Human review required; never pushed as Hot. |
| Blocked | Legal, compliance, sanctions, suppression, duplicate, or eligibility rule prevents outreach. | Hard rule with reason code and audit entry. |

### 2.4 Candidate funding-intent signals

Signals require legal/source approval and backtesting before production weights:

- Recent UCC filing, amendment, termination, or approaching lapse.
- New large customer contract, purchase order, award, or government contract.
- Rapid hiring, location expansion, equipment purchase, or new facility.
- Material receivables growth or cash-conversion pressure inferred from permitted data.
- New entity/reinstatement combined with operating evidence.
- Ownership/officer/address change requiring review, not automatically positive.
- Court/judgment/tax-lien/distress events, used conservatively and with compliance review.
- Trade, shipment, licensing, permit, or construction activity where licensed and relevant.
- Website/job/news language indicating growth, backlog, seasonal demand, or working-capital need.
- Direct first-party engagement: application, referral, site behavior, email reply, or call outcome.

No sensitive-class proxy, protected-class inference, or unreviewed personal-data signal may
enter the score.

---

## 3. Comparison matrix

| Feature | Cobalt likely/verified handling | Porter should build | Decision | Risk | Priority |
|---|---|---|---|---|---|
| Source registry | Internal state/capability routing is inferred | Explicit registry with owner, license, coverage, cost, health, freshness, and legal status | Improve | Medium | P0 |
| SOS verification | Live 50-state API plus cached fallback | Vendor connector plus selective official/open-data connectors | Copy pattern | Medium | P0 |
| Raw evidence | Screenshot/document links; raw retention unknown | Immutable raw payload/HTML/file, hash, capture time, parser version, and owned object-store URI | Improve | High | P0 |
| Async lookup | `retryId`, `searchGuid`, polling, callbacks | Durable job/run model, idempotency key, retry policy, dead-letter handling, webhook signing | Improve | Medium | P0 |
| Batch | CSV upload/download | Validated import, row-level errors, resumable jobs, dedupe, and review before CRM push | Improve | Medium | P1 |
| Entity resolution | Alternatives and confidence fields | Explainable weighted resolver, hard identifiers, thresholds, candidate review, merge history | Improve | High | P0 |
| UCC | Optional and state-dependent | Coverage-aware UCC facts with source, jurisdiction, debtor match, lapse, and explicit unknown state | Improve | High | P1 |
| Sanctions | Multi-list fuzzy screening | Licensed screening, versioned thresholds, case workflow, reviewer evidence | Improve | High | P0 |
| TIN | IRS match/status fields | Restricted underwriting-only connector; never expose TIN to sales | Improve | High | P2 |
| Related businesses | Cross-state agent/officer matching | Relationship graph with confidence, source, and PII access controls | Improve | High | P2 |
| AI observations | Example narrative flags | Deterministic facts first; LLM summary only with citations and no autonomous decision | Improve | High | P2 |
| Lead intent | Not publicly demonstrated | Event/time-series signal store and funding-intent classifier | Build new | High | P0 |
| Hot/Warm/Cold | Not publicly demonstrated | Versioned rules calibrated to outcomes, with eligibility and confidence gates | Build new | High | P0 |
| Contact enrichment | Some contact fields returned | Licensed enrichment, verification date, source permissions, suppression, role relevance | Improve | High | P1 |
| Human review | Dashboard details unknown | Queues for match, compliance, source error, duplicate, and lead-quality review | Build new | Medium | P0 |
| Salesforce | API integration generally advertised; native workflow unknown | Idempotent upsert, field mapping, evidence link, campaign/source attribution, feedback sync | Build new | High | P1 |
| Alerts | Unknown | Near-real-time alerts only for high-confidence newly Hot leads, with rate limits and dedupe | Build new | Medium | P2 |
| Cost tracking | Usage endpoint exists | Per-request estimated/actual cost, cache savings, source ROI, and budget guardrails | Improve | Medium | P0 |
| Source quality | Partial-success fields | Accuracy, coverage, freshness, latency, failure, drift, cost, and conversion metrics | Improve | Medium | P0 |
| Audit/security | Public evidence insufficient | SSO/MFA, RBAC/ABAC, immutable audit, secret manager, retention, encryption, access reviews | Build new | High | P0 |
| Voice outreach | Not relevant | Defer until lead precision, consent, scripts, monitoring, and human escalation are approved | Reject now | High | P3 |

---

## 4. Technical architecture

```text
Official/open data   Licensed vendors   Approved public web   First-party/Salesforce
        |                   |                   |                       |
        +-------------------+-------------------+-----------------------+
                                    |
                         Ingestion and source gateway
                 rate limit | license policy | cost | retries | health
                                    |
                  Raw event + immutable evidence object store
                                    |
               Parse/normalize -> quality checks -> entity resolution
                                    |
                 Canonical company + identity/relationship graph
                                    |
                  Time-series funding-intent signal extraction
                                    |
            Eligibility/compliance gates -> explainable lead scoring
                                    |
              Human review -> lead profile -> alerts -> Salesforce
                                    |
             Sales outcomes -> labels -> calibration/source ROI loop
```

### 4.1 Components and stack

| Layer | Recommendation |
|---|---|
| Frontend | React + Vite for production workflow; retain current dashboard and add daily queue, signal timeline, review, source health, and admin views. Streamlit is suitable only for internal analysis prototypes. |
| API | FastAPI on Python 3.13 when dependencies are qualified; keep 3.12 until CI/runtime compatibility is proven. Pydantic v2 contracts and OpenAPI. |
| Database | PostgreSQL 16+, SQLAlchemy 2.x, Alembic. `pg_trgm` for candidate search; optional `pgvector` only after an evaluated semantic-matching use case. |
| Object storage | Versioned S3-compatible storage with object lock/retention for raw evidence; DB stores hashes and metadata. |
| Pipelines | Prefect initially for scheduled/batch flows; durable queue workers for interactive jobs. Consider Temporal only if workflow scale/complexity justifies migration. |
| Scraping/API | One connector contract. Prefer official API/bulk/open data, then licensed vendor, then written-approved automation. Per-source rate limits and kill switches. |
| Enrichment | Provider adapters with field-level provenance, license/purpose metadata, cost, confidence, and expiry. |
| Scoring | Deterministic, versioned rules first. Separate identity confidence, evidence quality, intent, ICP fit, risk, and contactability. |
| Agents | Agents propose research, summaries, and mappings; deterministic code performs writes, scoring, compliance gates, and CRM sync. All agent output cites evidence and is reviewable. |
| Salesforce | REST/Bulk API adapter, OAuth connected app, sandbox contract tests, idempotent external IDs, outbox/retry pattern, and inbound outcome sync. |
| Monitoring | Structured logs, OpenTelemetry, Sentry, metrics, source canaries, queue age, webhook failures, cost and data-drift alerts. |
| Deployment | Docker Compose local; ephemeral CI DB/testcontainers; managed containers, Postgres, Redis/queue, object store, and secret manager in staging/prod. IaC and gated migrations. |

### 4.2 Core data model additions

The repository already has company, registration, run, evidence, source, score, audit,
review, and Salesforce foundations. Add:

- `source_policies`: license, legal approval, allowed purpose, robots/ToS review, retention.
- `ingestion_jobs` and `ingestion_attempts`: schedule, cursor, retry, latency, cost.
- `source_observations`: append-only normalized facts referencing raw events.
- `company_relationships`: officer/agent/address/domain/parent links with confidence.
- `signals`: type, event time, observed time, magnitude, direction, expiry, evidence IDs.
- `signal_features`: versioned values used by a scoring run.
- `lead_scores`: temperature, component values, model/rule version, explanation, expiry.
- `lead_candidates`: territory, owner, queue state, next action, suppression reason.
- `contacts`: business role, provider, verified time, permission and suppression metadata.
- `duplicate_candidates` and `entity_merge_events`: reviewable, reversible identity history.
- `salesforce_outbox`: idempotent pending operations and retry/dead-letter state.
- `lead_outcomes`: contacted, connected, qualified, application, approved, funded, lost reason.
- `source_quality_daily`: coverage, accuracy sample, freshness, latency, cost, and drift.
- `alerts`: dedupe key, recipient, channel, delivered/acknowledged timestamps.
- `compliance_cases`: sanctions/privacy/suppression reason, reviewer, disposition, evidence.

### 4.3 Scoring contract

```text
eligibility gate = verified entity AND allowed geography/industry AND not blocked

identity_confidence   0..1
evidence_quality      0..1
intent_strength       0..1
intent_recency        0..1
icp_fit               0..1
contactability        0..1
risk_penalty          0..1

lead_score = versioned weighted function of the above
temperature = threshold(lead_score) subject to eligibility and confidence gates
```

Rules must support reason codes, evidence links, replay, shadow evaluation, threshold
history, and expiry. A high score with weak identity is `Hold`, never `Hot`.

### 4.4 Security and compliance baseline

- Enterprise SSO/MFA; roles for sales, reviewer, underwriting, compliance, admin, audit.
- Field-level controls for TIN, personal addresses, officer/contact data, and sanctions cases.
- TLS, managed encryption keys, secret manager, key rotation, no secrets in DB/logs.
- Purpose limitation and source-policy enforcement before ingestion or display.
- Data minimization, retention/deletion schedules, legal hold, and DSAR support as applicable.
- Do-not-contact and suppression checks before alerts/CRM actions.
- Immutable audit for sensitive reads, score decisions, review, exports, and policy changes.
- Signed callbacks/webhooks; SSRF-safe allowlisting; replay protection and idempotency.
- Vendor security review, DPA/license inventory, subprocessor tracking, and breach process.
- No automated adverse credit decision or external outreach from unreviewed agent output.

---

## 5. Ten-phase implementation plan

### Phase 1 - Analyze and document Cobalt

- **Goal:** establish a legally clean, evidence-based reference baseline.
- **Features:** public flow map, API capability catalog, coverage matrix, unknowns register,
  authenticated-demo questionnaire, and vendor bake-off rubric.
- **Modules/files:** this document; `docs/source_registry.md`;
  `docs/state_source_feasibility.md`; `data/vendor_evaluation/` (non-production samples).
- **Models:** no production model; evaluation cases and field-level coverage matrix.
- **Tests:** documentation link checks; sample schema validation; no secrets in fixtures.
- **Security/compliance:** legal/vendor review; prohibit credential sharing and private API capture.
- **Acceptance:** stakeholders approve facts/assumptions; unknowns have owners and validation steps.
- **Risks/blockers:** authenticated Quick Start remains unverified; vendor pricing/SLA unknown.

### Phase 2 - Define Porter's product requirements

- **Goal:** translate sales and underwriting decisions into measurable product behavior.
- **Features:** personas, lead-temperature contract, ICP, territories, suppression rules,
  reviewer SLAs, Salesforce field map, and success metrics.
- **Modules/files:** `docs/product_plan.md`; `docs/lead_scoring.md`;
  `docs/salesforce_mapping.md`; acceptance-test scenarios.
- **Models:** `lead_candidates`, `lead_outcomes`, `compliance_cases` specifications.
- **Tests:** example leads classified by sales/underwriting; disagreement and edge-case review.
- **Security/compliance:** permitted-purpose review; protected/sensitive feature exclusion.
- **Acceptance:** labeled 200+ lead/deal golden set; definitions approved by Sales, UW, Legal.
- **Risks/blockers:** vague definition of Hot; insufficient historical outcome labels.

### Phase 3 - Design schema and source registry

- **Goal:** create the canonical, provenance-first data foundation.
- **Features:** source policy, capability/coverage, cost, freshness, credentials by reference,
  canonical company spine, signal/event model, dedupe and merge history.
- **Modules/files:** `db/models/source.py`, new `source_policy.py`, `signal.py`, `lead.py`,
  `relationship.py`; Alembic migrations; `services/source_registry.py`.
- **Models:** source policies, ingestion jobs, observations, relationships, signals, leads,
  scores, outcomes, quality metrics, outbox, alerts.
- **Tests:** constraints, migration up/down, append-only rules, source selection, uniqueness,
  tenant/role access, and merge reversibility.
- **Security/compliance:** source cannot run without approved policy; credential values never stored.
- **Acceptance:** schema supports replay from raw evidence and traces every score to sources.
- **Risks/blockers:** over-modeling; destructive merge semantics; migration conflicts.

### Phase 4 - Build ingestion and evidence pipeline

- **Goal:** reliably acquire permitted data and preserve it before interpretation.
- **Features:** connector SDK, scheduled/incremental/API/batch modes, idempotency, retries,
  raw store, hashes, parser versioning, quarantine, cache, and source canaries.
- **Modules/files:** `connectors/base.py`, per-source packages, `workers/ingest_flow.py`,
  `services/evidence.py`, `services/observations.py`, object-store adapter.
- **Models:** ingestion jobs/attempts, raw events, evidence items, observations, source quality.
- **Tests:** connector contracts, recorded fixtures, timeout/rate-limit/callback failures,
  raw-before-normalized invariant, hash verification, and parser replay.
- **Security/compliance:** allowlist destinations, egress limits, malware-safe file handling,
  legal kill switch, PII redaction in logs, and cost ceilings.
- **Acceptance:** two diverse sources run end-to-end; no normalized fact exists without evidence.
- **Risks/blockers:** source instability, license restrictions, bot controls, variable coverage.

### Phase 5 - Build scoring and Hot/Warm/Cold classification

- **Goal:** rank evidence-backed funding opportunities reproducibly.
- **Features:** signal extraction, expiry/decay, identity/evidence gates, ICP fit, risk penalty,
  score explanations, versioning, replay, and threshold calibration.
- **Modules/files:** `services/signals.py`, `services/lead_scoring.py`,
  `services/eligibility.py`, `workers/rescore_flow.py`, `docs/lead_scoring.md`.
- **Models:** signals, signal features, lead scores, candidate state transitions.
- **Tests:** deterministic boundaries, temporal decay, contradictory evidence, blocked/hold
  precedence, replay parity, golden-set precision/recall, and leakage tests.
- **Security/compliance:** feature allowlist; fairness/proxy review; no opaque adverse decisioning.
- **Acceptance:** versioned baseline beats simple ICP ranking; Hot precision target agreed and met
  in shadow mode; every classification has reason codes and evidence.
- **Risks/blockers:** weak labels, selection bias, sparse funded outcomes, false urgency.

### Phase 6 - Build dashboard and human review

- **Goal:** make the daily sales and review workflow usable and accountable.
- **Features:** daily lead queue, filters, signal/evidence timeline, score breakdown, duplicate
  comparison, review queues, corrections, bulk actions with preview, and source-health view.
- **Modules/files:** React pages/components; API routers for leads, signals, duplicates, reviews,
  dashboards; query/read-model services.
- **Models:** lead candidates, review decisions, merge events, saved views, audit events.
- **Tests:** API permissions, UI component/E2E flows, pagination, stale-write conflicts,
  accessibility, and sensitive-field masking.
- **Security/compliance:** field-level RBAC; audit sensitive reads and exports; no raw TIN in UI.
- **Acceptance:** pilot rep completes identify -> understand -> claim -> disposition; reviewer can
  correct a match without database access; p95 dashboard reads meet target.
- **Risks/blockers:** alert/queue overload, unclear explanations, reviewer bottleneck.

### Phase 7 - Add contact enrichment and Salesforce push

- **Goal:** convert approved candidates into actionable CRM records without duplication.
- **Features:** licensed contact adapters, role relevance, email/phone verification metadata,
  suppression, Salesforce match/upsert, evidence link, attribution, outbox, retry, and feedback pull.
- **Modules/files:** `connectors/contact_*`, `services/contacts.py`, `services/salesforce.py`,
  `workers/salesforce_sync.py`, mapping config and admin UI.
- **Models:** contacts, contact verification, suppression entries, Salesforce outbox/sync status.
- **Tests:** vendor contracts, suppression precedence, Salesforce sandbox, idempotent retries,
  duplicate collision, permission failures, and field mapping.
- **Security/compliance:** DNC/CAN-SPAM/TCPA and contract review; minimize personal data;
  OAuth least privilege; never log tokens or contact payloads.
- **Acceptance:** reviewed lead creates/updates exactly one Salesforce record; failures recover;
  source/score/evidence and disposition round-trip correctly.
- **Risks/blockers:** Salesforce schema/automation conflicts, bad CRM data, vendor use restrictions.

### Phase 8 - Add monitoring, alerts, audit, and source quality

- **Goal:** operate the system predictably and economically.
- **Features:** near-real-time Hot alerts, dedupe/cooldown, dashboards for source health, queue age,
  cost, coverage, drift, conversion, audit search, and incident runbooks.
- **Modules/files:** `services/alerts.py`, `workers/alert_flow.py`, telemetry setup, Sentry,
  source canaries, admin metrics, and runbooks.
- **Models:** alerts, source quality daily, cost ledger, incidents, audit partitions.
- **Tests:** alert dedupe, delivery retry, budget cutoff, canary failure, audit immutability,
  restore drill, and synthetic end-to-end checks.
- **Security/compliance:** alerts contain minimal data; signed links; retention and access reviews.
- **Acceptance:** SLOs and budgets visible; broken source detected before material sales impact;
  Hot alert reaches the right owner once; audit answers who/what/when/why.
- **Risks/blockers:** noisy alerts, misleading quality metrics, unbounded observability costs.

### Phase 9 - Add advanced agents and near-real-time monitoring

- **Goal:** accelerate research while keeping deterministic control over decisions and writes.
- **Features:** evidence-cited research agent, source-change triage, parser-drift assistant,
  lead-summary drafting, reviewer recommendations, continuous signal subscriptions, and evals.
- **Modules/files:** `agents/` prompts/contracts, tool allowlists, agent eval datasets,
  `workers/monitor_flow.py`, approval policies, and trace storage.
- **Models:** agent runs, tool calls, citations, proposals, approvals, evaluation results.
- **Tests:** groundedness, citation validity, prompt injection, tool permissions, regression evals,
  cost/latency limits, and fail-closed behavior.
- **Security/compliance:** untrusted-content isolation; no autonomous CRM/contact writes; redact
  secrets/PII; model/vendor data-processing review.
- **Acceptance:** agent summaries meet citation/accuracy threshold and reduce review time in shadow
  mode; deterministic services remain system of record.
- **Risks/blockers:** hallucination, prompt injection, variable cost, policy leakage.

### Phase 10 - Prepare future voice-agent outreach

- **Goal:** establish readiness criteria without prematurely automating calls.
- **Features:** consent/suppression service, approved scripts, disclosure, recording policy,
  quiet hours/time zones, call disposition ingestion, human transfer, QA sampling, kill switch.
- **Modules/files:** future `connectors/voice_provider.py`, `services/outreach_policy.py`,
  `workers/call_campaign.py`; do not enable until governance gate passes.
- **Models:** outreach consent, call attempts, recordings metadata, transcripts, dispositions,
  complaints, and campaign approvals.
- **Tests:** consent and DNC precedence, timezone/quiet hours, disclosure, transfer, provider outage,
  duplicate-call prevention, opt-out propagation, and emergency stop.
- **Security/compliance:** Legal approval for TCPA/state recording/telemarketing rules; encryption,
  restricted recordings/transcripts, retention, and human monitoring.
- **Acceptance:** lead-quality precision and sales adoption stable for at least two quarters;
  consent/legal gates pass; limited supervised pilot approved with complaint/stop thresholds.
- **Risks/blockers:** regulatory exposure, brand harm, inaccurate leads, consent ambiguity.

---

## 6. Delivery gates and KPIs

### Product KPIs

- Hot precision and qualified-opportunity rate.
- Time from signal observation to rep action.
- Contact/connect/application/funded conversion by source and score version.
- Duplicate and suppression escape rate.
- Reviewer overturn rate and reason.
- Sales acceptance and stale-lead rate.

### Data/operational KPIs

- Source coverage, freshness, accuracy sample, latency, failure, and schema drift.
- Identity auto-match rate and false-match rate (<1% target before broad automation).
- Evidence completeness (100% for score-bearing facts).
- Cost per ingested observation, qualified lead, application, and funded deal.
- Salesforce sync success, retry age, and duplicate creation rate.
- Alert precision, dedupe rate, and acknowledgement time.

### Go/no-go sequence

1. Approve source policy and golden set.
2. Prove raw evidence and entity resolution.
3. Run lead scoring in shadow mode.
4. Pilot daily dashboard with one sales pod.
5. Add reviewed Salesforce push.
6. Enable Hot alerts only after precision target.
7. Add agents only after deterministic baseline and eval harness.
8. Consider voice only after two quarters of stable lead quality and legal approval.

## 7. Immediate next sprint

1. Obtain an authenticated, screen-shared Cobalt walkthrough; do not share credentials.
2. Request current pricing, coverage-by-field/state, SLA, retention, security, and license terms.
3. Label 200-500 historical Porter leads/deals with outcome, known identity, and signal dates.
4. Finalize Hot/Warm/Cold and Hold/Blocked definitions with Sales, UW, and Compliance.
5. Extend the source registry with policy, cost, freshness, owner, and quality fields.
6. Add signal, lead score, outcome, source-quality, and Salesforce-outbox migrations.
7. Implement one high-value signal source end to end behind immutable evidence.
8. Build the daily lead read model and shadow score report before changing the UI.

## Public sources reviewed

- [Cobalt Quick Start](https://app.cobaltintelligence.com/dashboard/quickStart) - redirects to sign-in without an authenticated session.
- [Cobalt public API documentation](https://documentation.cobaltintelligence.com/)
- [Cobalt SOS product page](https://cobaltintelligence.com/secretary-of-state)
- [Cobalt application sign-in](https://app.cobaltintelligence.com/login)
