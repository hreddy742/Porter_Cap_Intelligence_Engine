# Development Plan

Build order for the MVP. Each slice follows **Plan → Code → Test → Review → Commit**
and is shippable on its own. Slices map to the plan's Phase 1 (§5, §24).

| Slice | Scope | Status |
|-------|-------|--------|
| 0 | Foundation: repo, config, logging, tests, docker-compose, docs | ✅ done |
| 1 | Core data model (18 tables) + Alembic migration + DB tests | ✅ done |
| 2 | Core services: normalization, evidence, audit | ✅ done |
| 3 | Entity resolution v1 + scoring v1 (boundary tests) | ✅ done |
| 4 | Connector framework + OFAC + mock vendor (contract tests) | ✅ done |
| 5 | Verification run orchestration (end-to-end flow) | ✅ done |
| 6 | FastAPI endpoints + RBAC + permission tests | ✅ done |
| 7 | React + Vite dashboard (search → profile → evidence → review) | ✅ done |
| 8 | Salesforce foundation, seed data, CI, deployment/runbook docs | ✅ done |

### Not yet built (next phases)

- Reports / KYB packet PDF export (plan §7.18, Phase 4)
- UCC / lien intelligence (plan §7.7, Phase 2)
- Real SOS/KYB vendor connector (swap in behind the existing contract)
- Real SSO/JWT auth replacing the header-based MVP boundary
- Duplicate-company review/merge tooling (plan §7.11)
- Monitoring/alerts + Sentry wiring (plan Phase 5)

## Cobalt parity and Porter differentiation roadmap

This is the execution order from the June 18 public-product comparison. "Parity"
means equivalent business capability, not copied code, UI, branding, or private
implementation. A phase advances only after its exit gate passes.

| Phase | Feature slice | Porter status | Exit gate |
|---|---|---|---|
| 1 | Source governance: acquisition method, legal approval, allowed purpose, retention, freshness, cost, quality | **Built in this branch** | Every production source has an owner and approved policy; daily quality schema exists; admin changes are audited. |
| 2 | Source quality aggregation and kill switches | Next | Success, latency, freshness, schema drift, and cost calculated daily; unhealthy sources can be disabled without deploy. |
| 3 | Vendor connector and coverage matrix | Planned | Cobalt or selected vendor passes the connector contract and a Porter golden-set bake-off; gaps are explicit by state/field. |
| 4 | Durable async jobs, callback delivery, and cached fallback | Partial | Polling survives process restart; callbacks are signed/idempotent; cache age is visible; no duplicate charge on retry. |
| 5 | Owned evidence: screenshots, documents, raw replay | Partial | 100% of score-bearing facts trace to immutable evidence; screenshots/documents are copied to Porter-controlled storage where licensed. |
| 6 | Batch CSV and nationwide verification | Planned | Row-level validation/retry/dedupe works; 50-state jobs expose partial progress; coverage is never overclaimed. |
| 7 | UCC, TIN, courts, licenses, related businesses | Planned | Each capability has jurisdiction coverage, access controls, match tests, cost, and explicit `unknown`/`not_covered` results. |
| 8 | Production identity and review | Partial | False entity match <1% on labeled Porter data; duplicate merge is reviewable/reversible; SSO replaces trusted headers. |
| 9 | Salesforce production workflow | Partial | Reviewed company upserts exactly once; evidence and attribution round-trip; failures recover through an outbox. |
| 10 | Funding-intent signals and Hot/Warm/Cold | Designed | Shadow-mode Hot precision meets the Sales-approved threshold; weak identity always routes to Hold; every score has reasons/evidence. |
| 11 | Daily lead queue and near-real-time Hot alerts | Planned | Reps act from one deduplicated queue; alerts have cooldown/ownership; acceptance and stale-lead rates are measured. |
| 12 | Advanced agents and future voice readiness | Deferred | Agents pass groundedness/tool-permission evals. Voice remains off until two quarters of stable lead quality and legal approval. |

### Program KPIs

Use a small set of decision metrics rather than counting shipped endpoints:

1. **Verified profile correctness** = correctly resolved and correctly normalized
   profiles / reviewed profiles. Initial gate: status correctness >98% and false
   entity match <1% on the Porter golden set.
2. **Evidence completeness** = score-bearing facts with retrievable, hashed source
   evidence / all score-bearing facts. Gate: 100% before production scoring.
3. **Qualified Hot precision** = Hot leads accepted as genuinely sales-actionable /
   reviewed Hot leads. Set the production target after shadow-mode baseline; do not
   invent a target without Porter outcomes.

Drivers: source success/freshness, auto-resolution rate, review turnaround, Salesforce
sync success, and time from signal to rep action. Guardrails: source cost per qualified
lead, suppression escapes, duplicate CRM creation, reviewer overturn rate, and alert
volume per rep.

## Definition of done (per slice)

A slice is done only when it: works; is tested; is readable; handles failure
cases; exposes no secrets; doesn't break existing features; has clean DB
constraints; preserves evidence/auditability; and can be explained to a new
engineer.

## MVP exit criteria (from the plan §5.4)

- >70% of a real Porter test-lead set auto-verify without human touch.
- False-match rate <1%; status-correctness >98% on a labeled golden set.
- Every run produces immutable evidence + audit entries; OFAC runs in-flow.
- Connector proven swappable (a second stub passes the same contract tests).

## Deferred (NOT in MVP)

In-house SOS scraping; UCC (Phase 2); native Salesforce UI / auto-trigger
(Phase 3); ML scoring; monitoring/alerts; underwriting automation; external API.
