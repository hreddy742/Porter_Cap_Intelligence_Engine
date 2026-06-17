# Deployment

| Environment | Description |
|-------------|-------------|
| **local** | docker-compose (Postgres + Redis); app via uvicorn; mock connector |
| **staging** | Cloud, prod-like, vendor *test* keys, no prod data; auto-deploy on main |
| **production** | Cloud container service + managed Postgres + object store; manual-approval deploy |

## Configuration

All config is environment variables (see `.env.example`). Non-secret config via env;
**secrets via a secrets manager** (Vault / cloud Secrets Manager) — the app only
receives references, never plaintext. `PORTER_ENV` selects safety defaults (e.g.
JSON logs and locked-down CORS in production).

## Database migrations

```bash
alembic upgrade head      # apply
alembic downgrade -1      # roll back one
```

Migrations run as a gated pipeline step **before** the app switches over, and are
written to be backward-compatible so a rollback is safe.

## Build & run

```bash
docker build -t porter-verify:local .
uvicorn porter_verify.api.app:app --host 0.0.0.0 --port 8000
```

The image is multi-stage, pins its base, and runs as a non-root user.

## CI/CD

GitHub Actions (`.github/workflows/ci.yml`) gates every push/PR: ruff lint +
format check, mypy, pytest, an Alembic upgrade smoke, and a frontend type-check +
build. The deploy pipeline target order is: lint → type → test → scan → build →
deploy(staging) → manual approve → prod.

## Backup & restore

- **Backups:** daily managed Postgres snapshot + point-in-time recovery; evidence
  object store replicated cross-region; a backup is taken before each deploy.
- **Restore drill (must pass before production):**
  1. Provision a scratch database.
  2. Restore the latest snapshot into it.
  3. Run `alembic upgrade head` (no-op if current) and the app's `/ready` check.
  4. Spot-check a known company profile + its evidence hashes.
- **Retention:** funded-deal evidence retained per policy (confirm with compliance,
  e.g. 7 years); transient lead data purged on schedule.

## Release checklist

- [ ] Migrations reviewed and backward-compatible
- [ ] Pre-deploy backup taken
- [ ] Required secrets present in the target environment
- [ ] CI green (lint, types, tests, build)
- [ ] Smoke test passes in staging (golden-set verify → evidence → review)
- [ ] On-call assigned; rollback image identified
