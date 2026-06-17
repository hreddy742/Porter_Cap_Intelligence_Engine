# Architecture

Porter Verify is built as clean, testable layers. **No business logic lives in
routes or UI.** Each layer depends only on the ones below it.

```
PRESENTATION      React + Vite dashboard
        |  HTTPS / (SSO later)
API LAYER         FastAPI: authn/z, RBAC, validation, rate-limit
        |  calls services
ORCHESTRATION     verify_flow: resolve -> fetch -> normalize -> screen -> score
                  -> persist -> evidence -> audit   (Prefect-ready; sync in MVP)
        |
SERVICE LAYER     normalization | entity-resolution | scoring | screening(OFAC)
                  evidence | review | audit | source-registry | salesforce | report
        |  via repositories
DATA LAYER        PostgreSQL (core)   object store (evidence WORM)   Redis (later)
CROSS-CUTTING     config | structured logging | error monitoring | security
```

## Layer responsibilities

| Layer | Responsibility | Key rule |
|-------|----------------|----------|
| **API** | HTTP surface, request/response schemas, auth, RBAC | Thin — delegates to services |
| **Orchestration** | Sequence the verification steps; retries; idempotency | One run = one `verification_run` row |
| **Services** | All business logic; pure-ish, unit-testable | No HTTP/DB framework leakage in signatures |
| **Repositories** | Data access via SQLAlchemy | Parameterized queries only (no string SQL) |
| **Connectors** | Talk to external sources behind one `SourceConnector` contract | Swappable; raw response preserved before parsing |
| **Data** | Postgres + evidence object store | Append-only for runs/evidence/audit |

## Data-flow invariants

1. **Raw before normalized.** Every source response is written verbatim to
   `raw_source_events` *before* any parsing. Re-parsing old raw enables
   reprocessing without re-paying the vendor.
2. **Evidence is immutable (WORM).** `evidence_items` carry a SHA-256; new runs add
   new evidence, never overwrite.
3. **Provenance on every fact.** Each stored fact references its `source_id` and
   carries a `captured_at` timestamp.
4. **Conservative resolution.** Below the auto-accept threshold, the system routes
   to human review — it never forces a match.
5. **Explainable scoring.** Scores are deterministic, versioned, and trace back to
   the evidence behind each component.

## Module map (`src/porter_verify/`)

- `config.py` / `logging_config.py` — cross-cutting configuration & logging.
- `db/` — SQLAlchemy 2.x models, session management, Alembic migrations.
- `services/` — one module per service responsibility above.
- `connectors/` — `SourceConnector` protocol, registry, OFAC + vendor implementations.
- `workers/` — verification flow orchestration.
- `api/` — FastAPI app factory, routers, Pydantic request/response schemas.

## Environments

Separate **local / staging / production**: separate DBs, secrets, and vendor
test/live keys. No prod data in staging. See [`deployment.md`](deployment.md).
