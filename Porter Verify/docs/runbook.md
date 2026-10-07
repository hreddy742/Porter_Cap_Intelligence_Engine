# Runbook

Practical operations for Porter Verify. Keep it short; expand as real incidents
teach us.

## Daily / on-call checks

- API healthy: `GET /health` (liveness) and `GET /ready` (DB reachable).
- Source health: `GET /sources/health` (ops/admin) — confirm connectors are not
  `degraded`/`unavailable`.
- Error volume: review `error_logs` for spikes in `source_unavailable` / parse errors.

## Common scenarios

**A verification returns `source_unavailable`.**
The data source was unreachable. The run is recorded with no charge and no
fabricated result. Check `/sources/health` and `error_logs`; retry once the source
recovers. No data fix needed.

**A verification returns `insufficient_evidence`.**
Expected when no record was found or key fields are missing for that state — not a
failure. Confirm the name/state input; the company is not persisted.

**A result looks wrong (false match).**
Entity resolution is conservative and routes ambiguity to review. Open the run,
inspect the confidence components and evidence, and record a review decision. If a
systematic issue, file against the resolution weights (versioned).

**Evidence hash mismatch.**
`EvidenceStore.verify()` failing means an artifact changed on disk. Treat as a
potential integrity incident: do not overwrite; capture the run id + hash and
escalate to security.

## Data integrity guarantees (do not bypass)

- `verification_runs`, `raw_source_events`, `evidence_items`, `review_decisions`,
  `audit_logs` are append-only. Never `UPDATE`/`DELETE` them directly.
- Company merges are reviewed and history-preserving — never hard-delete a company.
- Secrets live in the secrets manager only; never paste them into logs or tickets.

## Seeding sample data (non-prod)

```bash
alembic upgrade head
python scripts/seed.py
```

## Restore drill

See [`deployment.md`](deployment.md#backup--restore).
