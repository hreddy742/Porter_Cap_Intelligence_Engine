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
