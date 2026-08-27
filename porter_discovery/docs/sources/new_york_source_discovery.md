# New York Source Discovery

Research only. No connector, ingestion, or database code was written for this task.

## Official source links

- Dataset (primary): [Corporations and Other Entities: All Filings](https://data.ny.gov/Economic-Development/Corporations-and-Other-Entities-All-Filings/63wc-4exh) — data.ny.gov, ID `63wc-4exh`
- Dataset (address detail): [Corporations and Other Entities: All Filings - Address](https://data.ny.gov/Economic-Development/Corporations-and-Other-Entities-All-Filings-Addres/2tms-hftb) — data.ny.gov, ID `2tms-hftb`
- Dataset (snapshot, enrichment): [Active Corporations: Beginning 1800](https://data.ny.gov/Economic-Development/Active-Corporations-Beginning-1800/n9v6-gdp6) — data.ny.gov, ID `n9v6-gdp6`
- Data dictionary PDF (attached to the primary dataset page): `DOS_CorpsEntitiesAllFilings_DataDictionary.pdf`
- Search portal (verification only, not bulk discovery): [Corporation and Business Entity Search Database](https://dos.ny.gov/corporation-and-business-entity-search-database) → https://apps.dos.ny.gov/publicInquiry/
- Open data license: [Open NY Terms of Use](https://data.ny.gov/dataset/OPEN-NY-Terms-Of-Use/77gx-ii52)

Publisher for all datasets: New York State Department of State, Division of Corporations.

## Access method

Two distinct kinds of NY DOS access exist:

1. **`data.ny.gov` open datasets (recommended)** — official Socrata-hosted bulk data.
   - Available as CSV/JSON download and via the Socrata Open Data API (SODA), which supports filtering/sorting by column (including by `date_filed`).
   - No login, no payment, no CAPTCHA.
   - Primary "All Filings" dataset is updated **weekly** and has 20.9M+ rows going back to when the DOS electronic database began.
   - Governed by the state's own Open NY Terms of Use — permissive, allows commercial use, no attribution/share-alike requirement, but includes several pages of legal restrictions ("keep your re-uses lawful") that should be read in full before production use.

2. **DOS public entity search portal (`apps.dos.ny.gov/publicInquiry`)** — free, no login web search UI.
   - Search by entity name (Base Word / Contains / Begins With), DOS ID, or assumed name.
   - **No date-range browsing** — it is a lookup tool for a known/candidate name, not a discovery feed of new filings.
   - Site explicitly warns results should not be used to determine name acceptability; not designed for bulk/programmatic use.

**Newly registered by date/week**: yes, via the "All Filings" dataset's `date_filed` column, filtered further by `documenttype` to isolate initial filings from amendments. This is the only NY source found with real per-filing date granularity.

**Pagination/search required**: not for the open dataset (bulk query/download). The search portal is pagination/search-only and has no bulk or date-filter mode.

**Login/payment**: none for any source checked.

**Usage limits/terms**: subject to Socrata's standard API rate limits (not specially documented per-dataset) and NY's Open NY Terms of Use.

## Available fields (verified from source metadata only)

### "Corporations and Other Entities: All Filings" (`63wc-4exh`)

| Field | Column |
|---|---|
| DOS ID Number | `corpid_num` |
| Filing Number | `film_num` |
| Date Filed | `date_filed` |
| Approved Date | `approved_date` |
| Effective Date | `eff_date` |
| Entity Name | `corp_name` |
| Entity Type | `entitytype` |
| Document Type (e.g. initial filing vs. amendment) | `documenttype` |
| Jurisdiction | `juris` |
| County — Principal Office | `cnty_prin_ofc` |
| Law (statute under which filed) | `law` |
| Duration Date | `dura_date` |
| Dissolution Effective Date | `dis_eff_date` |
| Foreign Formation Date | `for_inc_date` |
| NFP Category | `nfp_type` |
| Fictitious Name | `fict_name` |
| ~15 amendment-tracking flag columns | various |

### "All Filings - Address" (`2tms-hftb`)

| Field | Column |
|---|---|
| DOS ID Number | `corpid_num` |
| Filing Number | `film_num` |
| Date Filed | `date_filed` |
| Address Type (1=Service of Process, 2=Registered Agent, 3=CEO, 4=Principal Executive Office) | `addr_type` |
| Name (of the addressee for that address type) | `name` |
| Address lines | `addr1`, `addr2` |
| City | `city` |
| State | `state` |
| ZIP | `zip5`, `zip4` |
| Country | `country` |

### "Active Corporations: Beginning 1800" (`n9v6-gdp6`, monthly snapshot)

DOS ID, Current Entity Name, Initial DOS Filing Date, County, Jurisdiction, Entity Type, plus denormalized Service-of-Process / Chairman / Registered Agent / Location address blocks.

**Not found in any official source**: officer or principal names/roles beyond a single CEO/chairman name field tied to an address record. NY's public corporate filings do not disclose a board or officer roster the way some states do.

## Discovery usefulness

- **Finding newly registered companies**: yes — `date_filed` + `documenttype` on the "All Filings" dataset, refreshed weekly.
- **Identifying staffing/PEO candidates**: entity name and `entitytype` alone are insufficient for classification (no NAICS/SIC code in these datasets); would require name-pattern heuristics or an external enrichment step, which is out of scope for this task.
- **Tracking registration changes over time**: yes — `documenttype` and the ~15 amendment flags on "All Filings" track subsequent changes to an already-known DOS ID.
- **Preserving source evidence**: yes — each row is tied to a `film_num` (Filing Number) that is independently verifiable against the DOS search portal.
- **Linking to company identity later**: DOS ID (`corpid_num`) is a stable key usable for future identity resolution and joins across all three datasets.

## Limitations

- No NAICS/SIC/industry code — staffing/PEO classification must happen downstream, not from this source alone.
- No officer/principal roster beyond one CEO/chairman address record.
- "All Filings" is weekly, not real-time; there will be up to ~7 days of lag between actual filing and dataset availability.
- Socrata API rate limits and the Open NY Terms of Use legal text were not fully read in this pass — flagged as unresolved below.
- Search portal has no bulk/date-filter mode, so it cannot be the discovery source; useful only for spot-verifying a specific entity found via the dataset.

## What we still do not know

- Exact Socrata API rate limits (requests/min) for anonymous vs. app-token access.
- Full text of the Open NY Terms of Use restrictions beyond the "keep re-uses lawful" summary.
- Whether `documenttype` values reliably distinguish "initial Articles of Organization/Incorporation" from all other filing types across every entity type (corp vs. LLC vs. LP) — needs a small sample pull to confirm before building filters on it.
- Typical actual lag between a real-world filing and its appearance in the weekly dataset (documented cadence is "weekly," but no confirmed day-of-week refresh time).

## Recommended first New York implementation approach

Use the official "Corporations and Other Entities: All Filings" dataset via the Socrata API, queried on a bounded `date_filed` window (e.g. rolling 7–14 days) and filtered to initial-filing `documenttype` values. This avoids scraping the search portal entirely, requires no login/payment, and gives a stable DOS ID for later identity resolution. Defer officer/registered-agent enrichment (join with the Address dataset) to a later step once the core filing feed is working.

## Final recommendation

**Proceed** — New York has a genuine official bulk dataset with real date-filed granularity, weekly updates, no auth, and a permissive commercial-use license, making it a strong candidate for the first real state source.
