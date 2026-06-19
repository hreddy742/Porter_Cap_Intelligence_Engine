# Four-State Review Package

This build covers Colorado, Connecticut, Oregon, and Ohio through the same
search, evidence, normalization, screening, scoring, audit, API, and dashboard
workflow. "Full data" means every field present in the approved source file is
preserved in raw evidence; it does not mean the platform invents fields a state
does not publish.

## Coverage

| State | Official acquisition path | Normalized fields | Explicit limitation |
|---|---|---|---|
| Colorado | Colorado Information Marketplace bulk CSV | ID, name, status, type, dates, principal/mailing address, jurisdiction, registered agent | Dataset does not publish officers or UCC records |
| Connecticut | data.ct.gov SODA dataset `n7gp-d28j` | ID, name, status/sub-status in raw, type, dates, business/mailing address, formation jurisdiction | This dataset does not publish registered agents or officers |
| Oregon | data.oregon.gov SODA dataset `tckn-sxa6` | ID, name, active status, type, dates, principal/mailing address, agent, authorized representatives, record link | Dataset contains active entities only |
| Ohio | User-supplied official Secretary of State CSV/ZIP export | Available ID, name, status, type, dates, addresses, jurisdiction, agent, record link | No unverified download endpoint is embedded; the current official site must supply the file or URL |

Every staged row retains the original source payload. Every completed
verification stores hashed immutable evidence and source provenance. A missing
field is returned as unavailable, not as clear, absent, or verified.

## Refresh Commands

Apply migrations first:

```powershell
.venv\Scripts\python.exe -m alembic upgrade head
```

Then refresh the official datasets:

```powershell
.venv\Scripts\python.exe scripts\refresh_colorado.py
.venv\Scripts\python.exe scripts\refresh_connecticut.py
.venv\Scripts\python.exe scripts\refresh_oregon.py
.venv\Scripts\python.exe scripts\refresh_ohio.py --file C:\secure\official-ohio-export.zip
```

The `--limit` and `--row-limit` flags are development-only caps. Omit them for a
complete refresh. Ohio also accepts `--url` when an official export URL has been
confirmed by the source owner.

## John Review Checklist

1. Search an exact legal name in each state and open the resulting profile.
2. Confirm raw and normalized status, principal/mailing address, jurisdiction,
   agent, representatives, and source link match the official record where those
   fields are published.
3. Confirm evidence has a timestamp, SHA-256, and source URL.
4. Verify unknown names produce insufficient evidence and no fabricated company.
5. Verify inactive Colorado records are marked ineligible.
6. Confirm Oregon clearly states active-only coverage and CT does not claim agent
   coverage.
7. Record an underwriting decision and confirm the audit trail captures it.

## Release Gate

The connector code, migrations, parsers, and end-to-end tests are review-ready.
The 2026-06-18 full refresh loaded 3,069,566 Colorado entities, 1,281,606
Connecticut entities, and 556,188 Oregon active entities. Exact source and row
metadata is stored in `data/state_refresh_manifest.json`.

Ohio remains `source_unavailable`: the official business search, sitemap,
business reports, and static publication routes all returned the Secretary of
State maintenance/security page during the refresh. No paid vendor credential is
configured. The Ohio connector and CSV/ZIP loader are tested and ready, but a
production sign-off cannot truthfully label Ohio complete until the official
source is reachable or an approved export/provider credential is supplied.
