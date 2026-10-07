# Porter Staffing Discovery & Intent — Final Build Plan

**Status:** plan of record  
**Date:** 2026-08-26  
**Product objective:** continuously identify newly registered staffing, recruiting and PEO companies across approved U.S. state sources, establish the correct company identity, find timely evidence of financing need or growth, and deliver evidence-backed leads for human review.

## 1. Product boundary

This is a new **Discovery** bounded context inside the existing Porter Verify repository.

- Same FastAPI application, PostgreSQL database, authentication, RBAC and audit conventions.
- A separate worker process for scheduled discovery and enrichment jobs.
- Existing Verification behavior remains unchanged.
- No separate microservice, repository, event bus, workflow platform or new frontend framework for the pilot.
- No automatic outreach or Salesforce export during shadow mode.

Verification answers: **“Is this known company legitimate and correctly identified?”**

Discovery answers: **“Which newly registered staffing companies appear to need financing now, and what evidence supports that conclusion?”**

## 1.1 Physical project structure

Discovery must be visibly self-contained inside the existing repository. Do not scatter new discovery logic across the verification connectors and services.

```text
Search Intelligence/
├── src/porter_verify/
│   ├── api/                         # existing shared API application
│   ├── connectors/                  # existing verification/UCC connectors
│   ├── db/                          # shared database and Alembic migrations
│   ├── services/                    # existing verification/shared services
│   ├── discovery/                   # NEW staffing discovery and intent product
│   │   ├── __init__.py
│   │   ├── contracts.py             # DiscoveryConnector; enrichment contract later
│   │   ├── models.py                # discovery-owned SQLAlchemy models
│   │   ├── artifacts.py             # immutable raw artifact storage
│   │   ├── ingestion.py             # runs, windows, replay and checkpoints
│   │   ├── worker.py                # dedicated discovery worker entry point
│   │   └── connectors/              # state discovery adapters added one at a time
│   └── ...
├── tests/
│   └── discovery/                   # NEW discovery tests and fixtures
├── frontend/src/features/
│   └── discovery/                   # added only when the review UI phase begins
└── docs/
    └── staffing_discovery_intent_final_build_plan.md
```

Add `classification.py`, `identity.py`, `enrichment.py`, `scoring.py`, `review.py` and their tests only when those phases begin. Do not create empty folders or placeholder modules in Task 1.

Shared authentication, RBAC, audit, normalization, evidence hashing, database configuration and API startup remain shared. Discovery imports those capabilities; it does not copy them. Alembic migrations remain in the existing central migration directory because both contexts use the same PostgreSQL database.

This gives the repository one product deployment with two understandable areas:

```text
porter_verify existing modules → company verification
porter_verify/discovery        → staffing discovery and intent
```

## 2. Simple end-to-end flow

```text
Approved state source
        ↓
New registration records + immutable raw evidence
        ↓
Likely staffing/recruiting/PEO classification
        ↓
Canonical company identity decision
        ↓
Structured-source and web intent research
        ↓
Versioned signals with citations and expiry
        ↓
Identity + ICP + intent + freshness + contactability + risk score
        ↓
Human review queue
        ↓
Approved lead → Salesforce outbox
        ↓
Sales outcome → score/source calibration
```

New registration is a discovery event, not proof of staffing fit and not proof of funding intent.

## 3. Connector boundaries

Keep the existing `SourceConnector` unchanged. It handles interactive lookup of one known company.

Add two narrow contracts only when their phase begins:

1. `DiscoveryConnector`
   - Reads a state bulk file/API/window.
   - Returns raw records, a cursor/window boundary and completion state.
   - Supports replay, overlap and schema-version checks.

2. `EnrichmentConnector`
   - Pulls company-specific evidence from an approved source.
   - Returns `success`, `not_found`, `not_covered` or `source_failed` explicitly.
   - Never converts an uncertain name match directly into a score-bearing signal.

Do not force bulk ingestion, web research and interactive verification through one interface.

## 4. Data lineage

Every accepted lead must be traceable through:

```text
discovery_run
  → source_artifact
  → source_observation
  → discovered_entity
  → company_link_decision
  → enrichment_attempt
  → signal
  → lead_score_snapshot + components
  → lead_candidate
  → lead_review_decision
  → salesforce_outbox
  → lead_outcome_event
```

Build these tables only in the phase that uses them.

### Foundation tables

- `source_capabilities`
- `discovery_runs`
- `source_checkpoints`
- `source_artifacts`
- `source_observations`
- `discovered_entities`

### Identity tables/fixes

- Correct `CompanyIdentifier` uniqueness so a state registration is scoped by identifier type, issuer/state namespace, jurisdiction and value.
- Audit existing company dedupe collisions before changing constraints.
- Add `company_link_decisions` with match method, confidence components, disposition, version and reviewer.

### Enrichment and lead tables

- `enrichment_attempts`
- `signals`
- `lead_score_snapshots`
- `lead_score_components`
- `lead_candidates`
- `lead_review_decisions`
- `salesforce_outbox`
- `lead_outcome_events`

Do not reuse verification evidence tables for discovery because they require a verification run. Reuse their hashing and audit discipline through a new discovery artifact store.

## 5. Staffing/PEO identification

Classification happens before intent research so expensive searches run only for plausible targets.

### Evidence order

1. Exact official industry evidence:
   - NAICS `561311` — Employment Placement Agencies
   - NAICS `561320` — Temporary Help Services
   - NAICS `561330` — Professional Employer Organizations
   - State PEO or staffing license/registration where applicable
2. Strong source text:
   - legal name and assumed names;
   - state business-purpose/industry description;
   - entity type and filing context.
3. Approved web research:
   - official company website;
   - service pages;
   - credible business profiles;
   - job pages and public announcements.

### Classification result

- `confirmed_staffing`
- `probable_staffing`
- `needs_review`
- `not_staffing`

Store evidence, reason codes, classifier version and observation time. A language model may propose a structured classification and summarize evidence, but it may not create a score-bearing fact without cited source material. Deterministic code owns writes and state transitions.

## 6. Company identity

Identity resolution precedes enrichment signals.

Match in this order:

1. Exact official registration identifier within its state/issuer namespace.
2. Exact verified domain or another hard identifier.
3. Explainable weighted comparison of normalized legal name, address, agent and jurisdiction.
4. Human review for ambiguity.

Never auto-merge companies by normalized name alone. Weak identity forces `Hold` even if intent evidence is strong.

Every UCC, tax-warrant, licensing, contract, job or web observation must reference an accepted `company_link_decision` before affecting a lead score.

## 7. Intent research

The system performs its own approved searches after a company is classified and linked. Manual research remains the fallback and shadow-mode comparison.

### Structured sources

- UCC filing lifecycle and lender classification
- Tax warrants, satisfactions and vacates
- PEO/staffing licensing status
- Government contracts and awards linked by verified UEI
- State grants and economic-development projects
- Business amendments, reinstatements, mergers and address/officer changes

### Web sources

- rapid hiring or many open roles;
- new offices, branches or geographic expansion;
- customer contracts, awards or large projects;
- leadership changes;
- service launches or material website changes;
- explicit working-capital, payroll-funding or growth language;
- credible distress or operating-pressure evidence.

The web enrichment connector must store the query, page URL, capture time, content hash, extracted statement, event date if known and parser/model version. Search failure is `source_failed`; no matching evidence is `not_found`; unsearched coverage is `not_covered`.

## 8. Signal and scoring contract

Keep verification scoring untouched. Discovery uses `services/lead_scoring.py`.

Score separate dimensions:

- `identity_confidence`
- `icp_fit`
- `intent_strength`
- `intent_recency`
- `evidence_freshness`
- `contactability`
- `risk_penalty`

Each component has a value, reason codes, evidence references, calculation version and expiry.

Temperature rules:

- **Hot:** strong, recent intent; accepted identity; eligible; no hard block.
- **Warm:** plausible but weaker or less recent evidence.
- **Cold:** valid staffing ICP with no timely intent.
- **Hold:** identity, evidence or freshness is ambiguous.
- **Blocked:** compliance, suppression, duplicate or source-policy rule prevents action.

New registration, PEO licensing and ESD grants affect discovery/ICP/operating context; they do not automatically increase funding intent.

## 9. Worker and durability design

Run discovery in one dedicated worker process, not inside every API replica.

Use:

- PostgreSQL-backed run/checkpoint state;
- one advisory lock per source/state;
- bounded overlap windows;
- idempotent observation keys;
- immutable source-artifact hashes;
- atomic checkpoint advancement only after full-window success;
- replay from stored artifacts;
- explicit retry and terminal error records;
- local artifact storage in development and an S3-compatible object-lock store in production.

Do not introduce Celery, Kafka, Prefect or Temporal for the pilot. Add a queue/workflow platform only after measured concurrency or recovery requirements exceed the database-backed worker.

## 10. Human review and Salesforce

Workflow:

```text
Discovered
→ Classifying
→ Identity Review / Enriching
→ Scored
→ Needs Review
→ Approved / Rejected / Needs More Research
→ Export Pending
→ Exported
```

- Review decisions are immutable and auditable.
- Raw personal data is masked by role.
- Only approved leads enter `salesforce_outbox`.
- Salesforce operations use an idempotent external key, retry state and dead-letter state.
- Raw observations and unrestricted PII never go to Salesforce.
- Salesforce outcomes return as append-only events for source ROI and scoring calibration.

## 11. Build sequence

### Task 0 — Establish a trustworthy baseline

**Work**

- Run current tests and linting.
- Document real failures without changing unrelated code.
- Confirm PostgreSQL/Alembic test execution.
- Record current schema and dirty-worktree state.

**Gate:** the team can distinguish new regressions from pre-existing failures.

### Task 1 — Discovery ingestion spine with fake data

**Build**

- `DiscoveryConnector` contract.
- Foundation tables only.
- Local development artifact store using existing hashing logic.
- One dedicated worker entry point.
- Fake paginated/windowed connector fixture.

**Tests**

- idempotent rerun;
- bounded-overlap replay;
- zero records versus source failure;
- parser/schema failure;
- immutable hash/provenance;
- checkpoint advances only after complete success;
- advisory lock prevents duplicate execution.

**Explicitly excluded:** live state source, staffing classification, identity matching, enrichment, scoring, UI and Salesforce.

### Task 2 — New York formation discovery connector

Implement the proven New York filing source through the Task 1 contract. Preserve the official identifiers needed to join the filings and entity-name datasets. Run bounded windows and reconcile counts against the source.

**Gate:** a replayed NY window produces identical observations and no duplicate discovered entities.

### Task 3 — Identity correction and link decisions

- Audit same-state identifier and company-dedupe collisions.
- Back up the database before identity migration.
- Correct state/issuer-scoped identifier uniqueness.
- Add explainable `company_link_decisions`.
- Build exact-ID first, weighted-match second, manual-review fallback.

**Gate:** no enrichment signal can exist without an accepted company link.

### Task 4 — Staffing classifier

- Deterministic NAICS/license/name/purpose rules.
- Web classification attempt only for unresolved candidates.
- Evidence-backed structured classification result.
- Manual review queue for ambiguity.

**Gate:** review at least 200 stratified candidates and report precision by match method/evidence tier, not only aggregate precision.

### Task 5 — New York intent vertical slice

Add, in order:

1. NY tax-warrant lifecycle reducer keyed by warrant ID.
2. Existing UCC connector reuse behind identity decisions.
3. Approved web enrichment for jobs, expansion, contracts and operating signals.
4. PEO and ESD sources as ICP/operating context, not distress intent.

**Gate:** every signal has event time, observation time, expiry, evidence and an accepted company link.

### Task 6 — Lead scoring and review API

- Versioned component scoring.
- Hard identity/compliance gates.
- Deterministic Hot/Warm/Cold/Hold/Blocked transitions.
- Lead queue/read APIs and immutable review decisions.

**Gate:** replaying the same evidence under the same score version gives the same result and explanation.

### Task 7 — Shadow-mode UI

Reuse the existing manual-queue interaction pattern. Add the daily staffing-lead queue, evidence timeline, identity decision, score breakdown, reviewer action and source-health status.

**Gate:** staff can understand why a company is present, verify evidence, reject a bad match and request more research without database access.

### Task 8 — Shadow evaluation

Use three separate datasets:

- at least 200 stratified discovery candidates for workflow and classification evaluation;
- at least 350 independently reviewed automated identity links with zero false links, stratified by match method;
- historical Porter outcomes only for signal correlation and calibration, never for discovery-coverage estimates.

No automated Salesforce export or outreach during this phase.

### Task 9 — Production controls and Salesforce

- SSO/MFA integration and production RBAC review.
- S3-compatible object storage with retention/object lock.
- source policy approvals and kill switches;
- monitoring, schema-drift and freshness alerts;
- Salesforce OAuth, field map and outbox worker;
- suppression and duplicate checks;
- inbound disposition/funded-outcome sync.

**Gate:** only reviewed leads export, retries cannot create duplicates, and every exported value is traceable.

### Task 10 — State expansion

Add states through the proven `DiscoveryConnector`, prioritized by Porter sales value, source legality, data quality and cost per accepted lead.

Recommended order after the NY vertical slice:

1. **California** — real weekly three-table sample already validated; useful business-purpose text.
2. **Mississippi and Rhode Island** — strong NAICS support for staffing classification.
3. **Utah** — paid but inexpensive source-filtered staffing NAICS/new-registration list.
4. **Existing staging states** — CO, CT, OR, OH and FL through discovery adapters, without rebuilding their acquisition logic.
5. **Low-friction bulk/API states** — AK, IL, ID, MT, WI and ME.
6. Remaining paid/request/manual states only after source-policy approval and ROI review.

The product supports all states through capabilities/coverage metadata even when a state is `not_covered`, pending approval or manual-only. It must never represent missing access as “no companies found.”

## 12. Company-grade approval gates

A source is production-ready only when:

1. intended commercial use is approved;
2. required entity types and formation fields are present;
3. source cadence and safe replay are documented;
4. a real sample passes schema, uniqueness, completeness and reconciliation checks;
5. source failure, zero records and not-covered states remain distinguishable;
6. raw evidence is immutable and score-bearing facts are fully traceable;
7. schema drift and stale data alert before sales impact.

System-wide gates:

- false automated company-link rate below 1% before broad automation;
- 100% of score-bearing facts have evidence and identity decisions;
- no automatic Salesforce writes before shadow approval;
- no autonomous outreach;
- no LLM-only identity, scoring, compliance or write decisions;
- source cost and accepted/funded outcomes measured by state and connector.

## 13. How implementation starts

The first Claude Code prompt should implement **Task 1 only**: the fake-fixture discovery ingestion spine and its tests. It must not contain California-specific or New York-specific parsing.

After Task 1 passes review:

1. issue the NY connector prompt;
2. review and test it;
3. issue the identity correction prompt;
4. review its migration and sampling results;
5. issue the staffing-classifier prompt;
6. then begin intent enrichment.

Every implementation prompt must require:

- `ponytail` full mode;
- relevant engineering/testing skills;
- reading the actual code path before editing;
- professional, human-readable code;
- minimal dependencies and smallest correct diff;
- trust-boundary validation, security, provenance and tests;
- exact acceptance criteria and commands run;
- no unrelated cleanup, no unverified claims and no production/external writes unless explicitly authorized.

## Final decision

Approve this plan and begin with Task 1. Do not begin with a California connector, 50 state-specific staging tables, web scraping, lead scoring, UI or Salesforce. The reusable discovery spine is the smallest foundation that prevents every state and enrichment source from becoming a separate one-off pipeline.
