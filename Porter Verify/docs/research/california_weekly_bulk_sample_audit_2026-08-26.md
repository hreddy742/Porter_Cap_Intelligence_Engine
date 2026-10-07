# California Weekly Business-Entity Bulk Sample Audit

**Audit date:** 2026-08-26  
**Source archive:** `DataRequest0xCECB6A1FEE5BBAA09B1F045E32F0B01EFE557F0B.zip`  
**SHA-256:** `B6D3FD0B9B21CB536BBDD2414A041AA7D0C71ECA5E573FBC5EC2B3A48E5F714F`

## Verdict

This is a valid **California weekly business-entity data package**, not a Vermont download. It is suitable for California new-registration discovery after three ingestion rules are enforced:

1. exclude name-reservation and other non-entity records;
2. parse the nonstandard `*|*` delimiter and treat `ENTITY_NUM` as text;
3. use `INITIAL_FILING_DATE` for discovery and never interpret `Jan 1 1900` in `LAST_SI_FILE_DATE` as a real filing date.

The sample is internally coherent and strong enough to approve a California connector spike. It is not the latest August 23 package shown in the portal: its records cover **2026-06-29 through 2026-07-06**, and its embedded file timestamps are July 6.

## Dataset and grain

| Table | Rows | Columns | Intended grain | Exact duplicates |
|---|---:|---:|---|---:|
| `Filings.csv` | 6,904 | 36 | One row per entity/registration record | 0 |
| `Agents.csv` | 6,539 | 14 | At most one agent per entity in this sample | 0 |
| `Principals.csv` | 9,099 | 14 | Zero-to-many principals per entity | 31 |

`Filings.ENTITY_NUM` is complete and unique: 6,904 nonblank values and 6,904 distinct values. Both child files have zero orphan entity IDs, so the joins are structurally sound.

## Date and volume checks

| Initial filing date | Records |
|---|---:|
| 2026-06-29 | 1,939 |
| 2026-06-30 | 1,599 |
| 2026-07-01 | 2,096 |
| 2026-07-02 | 1,175 |
| 2026-07-03 | 84 |
| 2026-07-04 | 7 |
| 2026-07-06 | 4 |

All 6,904 initial filing dates parse successfully. The July 3–6 collapse is consistent with the Independence Day weekend but should not be encoded as a permanent volume rule.

## Coverage and quality

| Check | Result | Interpretation |
|---|---:|---|
| Named agent coverage | 6,537 / 6,904 (94.7%) | Strong. Missing agents are almost entirely name reservations and other non-entity records. |
| Principal/mailing address coverage | 6,541 / 6,904 (94.7%) | Strong after non-entity rows are excluded. |
| Named principal coverage | 1,838 / 6,904 (26.6%) | Expectedly sparse for new filings; do not require a principal for ingestion or classification. |
| Nonblank type-of-business coverage | 1,676 / 6,904 (24.3%) | Too sparse and inconsistent to be the only staffing classifier. |
| Child-table orphan IDs | 0 | Agent and principal rows join cleanly to filings. |

The 365 filings without an agent comprise 355 name reservations, four foreign-name registrations, four unincorporated common-interest developments, one agricultural cooperative and one foreign LLC. This confirms that missing-agent coverage is primarily a record-type issue rather than general source failure.

## Entity mix and required exclusions

- 4,336 California LLCs
- 1,171 general California stock corporations
- 399 out-of-state LLC registrations
- 355 name reservations
- 177 out-of-state stock corporations
- 466 other entity/registration types

`Name Reservation` and `Foreign Name Registration` rows must never create companies or leads. Other unusual record types should be controlled by an explicit accepted-type mapping rather than accepted automatically.

## Staffing discovery test

A conservative keyword screen over entity name plus `TYPE_OF_BUSINESS` found **14 review candidates** in this one-week package:

| Candidate | Filing date | Evidence |
|---|---|---|
| AITechLogix LLC | 2026-07-01 | “IT solutions, consulting, and staffing services” |
| ALL START STAFFING AGENCY INC | 2026-07-01 | “STAFFING SERVICE” |
| Code 3 Staffing LLC | 2026-07-01 | Staffing in legal name |
| Harvest Support Staffing LLC | 2026-06-30 | Staffing in legal name |
| National Recovery Staffing LLC | 2026-07-01 | Staffing in legal name |
| Naval Technical Staffing LLC | 2026-07-01 | Staffing in legal name |
| Rebion Partners Inc. | 2026-06-29 | “Recruitment agency” |
| Render Staffing LLC | 2026-07-01 | Staffing in legal name |
| Stagehands national staffing Inc. | 2026-07-01 | Staffing in legal name |
| Viable Talent Solutions LLC | 2026-06-30 | “Talent Acquisition, Recruitment, and staffing” |
| Arline Care Industry Staffing Plus LLC | 2026-07-01 | Staffing in legal name |
| Creative Recruiting Services LLC | 2026-07-02 | Executive recruiting description |
| Infinity Workforce LLC | 2026-07-01 | Workforce in legal name; needs web verification |
| Workforce Pay Services | 2026-06-29 | Payroll description; likely not staffing |

The first 12 are strong staffing/recruiting candidates but still require identity resolution and web evidence before becoming sales leads. `Infinity Workforce` needs manual/web classification, and `Workforce Pay Services` should probably be rejected as payroll rather than staffing.

## Connector rules

1. Preserve the original ZIP, checksum, internal filenames and acquisition timestamp.
2. Parse `*|*` as the delimiter and retain all identifier columns as strings.
3. Use `ENTITY_NUM` as the source identifier within the California namespace.
4. Use `INITIAL_FILING_DATE` as the official registration event date.
5. Reject name reservations and maintain an explicit allowlist of entity types.
6. Join agents and principals by `ENTITY_NUM`; never flatten principals before controlling the one-to-many relationship.
7. Convert blank strings to null only after raw evidence is stored.
8. Treat `Jan 1 1900` as a sentinel/null in date fields.
9. Reprocess a bounded overlap window because corrected or late records may reappear.
10. Deduplicate downstream companies by official identifier first, never by name alone.

## Remaining production gates

- Download the actual latest package shown in the portal and confirm its filing-date window.
- Obtain the $100 master unload only if historical California coverage is required; weekly files are sufficient for forward discovery.
- Compare the next two weekly packages to determine whether files are pure new formations or include corrections/updates.
- Confirm the portal's retention and commercial-use terms and store a copy with the source configuration.
- Reconcile one weekly file against a portal control total or a sample of official entity pages.

**Approval:** approve for a California connector spike; do not label production-ready until the next two weekly files establish update semantics and replay behavior.
