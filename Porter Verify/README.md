# Porter Verify

**Internal Business Verification & Lead Intelligence Platform for Porter Capital.**

Porter Verify tells Porter, in seconds, whether a business lead is **real, active,
correctly named, registered, and lien-encumbered** — backed by immutable, sourced
evidence and a full audit trail, and (later) wired into Salesforce.

It answers, for any company: *Is this business real? Active or inactive? What is the
legal name? Does it have a DBA? What state is it registered in? What evidence supports
this? Are there UCC/risk indicators? Does it match a Salesforce lead? Should sales,
underwriting, or operations review it? What source produced each claim, and how
confident are we?*

> Full product specification: [`docs/product_plan.md`](docs/product_plan.md) (Plan v1.0).
> Architecture: [`docs/architecture.md`](docs/architecture.md).

## Principles (non-negotiable)

- **Evidence-backed only** — every claim links to a source, timestamp, and hash.
- **Never fabricate** source data; preserve **raw** responses verbatim, separately
  from **normalized** fields.
- **Append-only** evidence, audit, and verification runs (WORM) — no silent overwrites.
- **Conservative entity resolution** — fuzzy matches only *surface* review candidates;
  the system never auto-merges companies on name similarity alone.
- **Deterministic, explainable scoring** — no ML in the MVP.
- **Secure by default** — RBAC boundary, secrets from a manager (never Git), audited
  sensitive actions.

## Tech stack

| Layer | Choice |
|-------|--------|
| API | FastAPI (Python 3.12+) |
| DB | PostgreSQL 16 + SQLAlchemy 2.x + Alembic |
| Validation | Pydantic v2 |
| Orchestration | Prefect (scaffolded; synchronous in MVP) |
| Dashboard | React + Vite |
| Logging | structlog (JSON in prod) |
| Tests | pytest |

## Quick start (local)

```bash
# 1. Create a virtualenv and install (dev extras include pytest/ruff/mypy)
python -m venv .venv
.venv/Scripts/activate        # Windows;  source .venv/bin/activate on macOS/Linux
pip install -e ".[dev]"

# 2. Configure environment
cp .env.example .env          # fill in values; defaults are safe for local

# 3. Start the database (PostgreSQL via Docker)
docker compose up -d db

# 4. Apply migrations  (available from Slice 1 onward)
# alembic upgrade head

# 5. Run the API
uvicorn porter_verify.api.app:app --reload      # serves on http://localhost:8000
```

### Dashboard (React + Vite)

```bash
cd frontend
npm install
cp .env.example .env          # VITE_API_BASE defaults to http://localhost:8000
npm run dev                   # serves on http://localhost:5173
npm run build                 # type-check + production build
```

Pick an acting role from the header dropdown (stands in for SSO in the MVP) to see
role-based access in action. Run a verification from **Home**, then open the
company profile to see the score panel, evidence timeline, and review panel.

### Four-state data refresh

Colorado, Connecticut, Oregon, and Ohio have direct state connectors. See
[`docs/four_state_review.md`](docs/four_state_review.md) for coverage, refresh
commands, source limitations, and the review checklist.

### UCC filing intelligence

Porter Verify also exposes deterministic UCC intelligence for Porter Leads over
REST only; there is no shared database or shared code between the systems.

Endpoints:

- `GET /ucc?company={name}&state={ST}` returns active/terminated UCC filings and
  any UCC-3 exit signal for the debtor name.
- `GET /ucc/exits` returns freshest UCC exit signals first, optionally filtered by
  state or `min_strength=HOT|WARM`.
- `GET /ucc/known-factors` lists the deterministic factor/MCA/ABL/bank watchlist.
- `POST /ucc/known-factors` lets ops/compliance add competitor factor names from
  John Cox Miller.

Classification is rule-based only. Known factors are checked first, then MCA,
bank, and equipment indicators. AI is not used for scoring, gates, suppression,
or lender classification.

Washington UCC ingestion currently supports an official CSV/JSON file or URL:

```bash
python scripts/refresh_washington_ucc.py --file path/to/washington_ucc.csv
python scripts/refresh_washington_ucc.py --url https://official-source.example/file.csv
```

Important source note: historical IACA materials say Washington offered a free
full database/API, but the current official pages found during implementation
expose UCC search/filing pages, not a verified direct public bulk URL. Do not
claim Washington is live-loaded until an official working bulk URL or file is
provided and logged in `ucc_refresh_log`.

Known paid/gated UCC feeds include Kentucky, North Dakota, Minnesota, Idaho,
Kansas, Texas, Florida's vendor registry, and Indiana. Use official subscription
or bulk channels for those states. Do not scrape North Carolina SOS UI.

## Running tests

```bash
pytest                 # full suite (defaults to an isolated SQLite DB — no Docker needed)
ruff check src tests   # lint
ruff format src tests  # format
mypy                   # type check
```

The test suite does **not** require Docker or a running Postgres; it uses an
isolated SQLite database so contributors can run it instantly. Models are kept
dialect-portable; Postgres-only features are applied conditionally.

## Repository layout

```
src/porter_verify/
  config.py            # env-based settings (Pydantic)
  logging_config.py    # structlog setup
  db/                  # SQLAlchemy models + Alembic        (Slice 1)
  services/            # normalization, resolution, scoring, evidence, audit (Slice 2-3)
  connectors/          # SourceConnector protocol + OFAC + vendor (Slice 4)
  workers/             # verify flow orchestration           (Slice 5)
  api/                 # FastAPI app, routers, schemas        (Slice 6)
frontend/              # React + Vite dashboard               (Slice 7)
tests/                 # unit, contract, golden, api, permission
docs/                  # plan + architecture + security + testing + data model
infra/                 # CI, deployment
```

## Status

MVP under active development. See
[`docs/development_plan.md`](docs/development_plan.md) for the build sequence and
[`docs/testing.md`](docs/testing.md) for the test strategy.
