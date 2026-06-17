# Data Model

Principles: a **canonical company spine**; **append-only** verification / evidence /
audit; **explicit source provenance** on every fact; **raw before normalized**;
conservative dedupe; **no destructive overwrites**.

> Full DDL reference: see §10 of [`product_plan.md`](product_plan.md). SQLAlchemy
> models land in Slice 1 under `src/porter_verify/db/models/`.

## Table catalog (MVP)

| Table | Purpose | Notes |
|-------|---------|-------|
| `companies` | Canonical resolved entity (the spine) | `dedupe_key` unique; normalized_name indexed |
| `company_identifiers` | All IDs (1:N) | `UNIQUE(id_type, id_value)` |
| `business_registrations` | Per-state registration | `UNIQUE(state, state_entity_id)`; raw + normalized status |
| `registered_agents` | Agent per registration | PII-adjacent (access-controlled) |
| `company_officers` | Officers/principals (1:N) | PII (restricted); OFAC-screened |
| `verification_runs` | One verification execution | **append-only**; carries score_version |
| `raw_source_events` | Verbatim source responses | **append-only**; raw_hash, cost_credits |
| `evidence_items` | Immutable proof | **WORM**; sha256, no update/delete |
| `confidence_scores` | Score component breakdown | value + weight + explanation per component |
| `review_decisions` | Human decisions | **immutable**; reason + before/after |
| `source_registry` | Connectors / capabilities / coverage | drives connector selection |
| `source_credentials` | Secret **references only** | no plaintext |
| `salesforce_sync_status` | SF sync state | `UNIQUE(sf_object, sf_record_id)` |
| `users` | Internal users | linked to a role |
| `roles` | RBAC roles | permissions list |
| `audit_logs` | Append-only audit | actor, action, before/after, request_id |
| `error_logs` | Operational errors | source_id, run_id, error_type |
| `generated_reports` | KYB packet PDFs | storage_uri + sha256 |

`ucc_filings` (UCC/liens) is **Phase 2**, not MVP.

## Append-only / WORM tables

`verification_runs`, `raw_source_events`, `evidence_items`, `review_decisions`,
`audit_logs`. In production the application DB role lacks UPDATE/DELETE on these.
In the MVP the same guarantee is enforced at the service layer (no update/delete
methods) and asserted by tests.

## Status enum

`business_registrations.status_normalized` and `companies.status_normalized` use a
controlled vocabulary: `active | inactive | dissolved | delinquent | unknown`. The
raw state status is always kept alongside the normalized value.

## Portability note

Models use dialect-portable types so the suite runs on SQLite. Postgres-only
features (`pg_trgm` trigram index, `gen_random_uuid`) are applied conditionally in
migrations when the dialect is PostgreSQL.
