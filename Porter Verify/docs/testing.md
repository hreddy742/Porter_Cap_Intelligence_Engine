# Testing

> Quality bar: a feature is not done unless it is tested.

## How to run

```bash
pytest                  # full suite
pytest tests/test_x.py  # one file
pytest -k name          # by keyword
ruff check src tests    # lint
mypy                    # type check
```

The suite defaults to an **isolated SQLite database**, so it runs instantly with
no Docker/Postgres dependency. To run against Postgres (closer to production), set
`PORTER_DATABASE_URL` to a Postgres URL before invoking pytest.

## Test categories (built incrementally per slice)

| Category | What it covers | Slice |
|----------|----------------|-------|
| Unit | config, logging, normalization, scoring math | 0+ |
| Database | model constraints, append-only/WORM enforcement | 1 |
| Migration | Alembic upgrade applies cleanly | 1 |
| Service | source registry, ingestion, evidence, audit | 2 |
| Entity resolution | golden-set precision/recall, false-match <1% | 3 |
| Scoring | deterministic, boundary thresholds, explainability | 3 |
| Connector contract | every connector satisfies the `SourceConnector` contract | 4 |
| Error handling | source-failure path (no charge, review fallback) | 4-5 |
| API | endpoint happy-path + validation errors | 6 |
| Permission/security | role-based access enforced | 6, 8 |
| End-to-end | search → verify → evidence → review workflow | 5-7 |

## Conventions

- Tests are deterministic — no live network calls; connectors are mocked.
- Each test states one behavior; names read as sentences.
- Golden data (entity-resolution labels) lives under `tests/golden/`.

## Pre-merge checklist

- [ ] Relevant unit + integration tests pass
- [ ] Full suite passes
- [ ] Migrations apply cleanly (`alembic upgrade head`)
- [ ] App imports / starts
- [ ] `ruff check` and `mypy` clean
- [ ] No secrets added to the diff
