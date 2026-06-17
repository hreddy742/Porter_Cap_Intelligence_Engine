# Security

Designed to pass review by Porter leadership and a real security reviewer.

## Secrets

- **No secrets in Git.** `.env` is git-ignored; only `.env.example` (placeholders)
  is committed.
- Production secrets come from a **secrets manager** (Vault / cloud Secrets Manager).
  The database stores only secret *references* (`source_credentials.secret_ref`),
  never plaintext keys.
- Secret-bearing settings fields are marked `repr=False` so they never appear in
  logs or tracebacks.

## Authentication & authorization

- **Auth boundary** at the API layer (SSO/OIDC + MFA in production).
- **RBAC** with least privilege. Planned roles: `sales`, `underwriter`, `ops`,
  `admin`, `compliance` (read-only). Officer/UCC data is access-restricted.
- Admin actions and sensitive reads (evidence, officers) are **audited**.

## Data protection

- **Input validation** via Pydantic on every external input.
- **SQL-injection safe** — SQLAlchemy ORM / parameterized queries only; no string
  SQL interpolation.
- **PII minimization** — no raw EIN stored (hash if needed); officer addresses are
  access-controlled and retention-limited.
- **Append-only** evidence/audit/runs prevent tampering; SHA-256 on artifacts.
- **Safe logging** — never log secrets, credentials, or full PII; log identifiers.

## API hardening

- Structured, non-leaky error responses (no stack traces or internal detail to
  clients).
- Rate-limit ready (Redis-backed in later phases).
- TLS in staging/production; encryption at rest via managed DB + object store.

## Dependencies & supply chain

- Pinned base Docker image; dependency + secret scanning gated in CI (Slice 8).
- No scraping of sources where legally/technically risky without explicit approval;
  APIs / licensed vendor data first.

## Backups & retention

- Daily encrypted DB snapshots + PITR; evidence cross-region (see
  [`deployment.md`](deployment.md)).
- Funded-deal evidence retained per policy (e.g. 7 yrs — confirm with compliance);
  transient lead data purged on schedule.

## Salesforce (future)

- Credentials server-side only via a scoped connected app; least privilege; sync
  audited. No data pushed to Salesforce until credentials, field mappings, and an
  approval flow are confirmed.
