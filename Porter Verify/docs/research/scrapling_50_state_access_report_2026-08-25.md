# U.S. SOS Business-Registration Access Audit

**Audit date:** 2026-08-25  
**Purpose:** determine where official state business-registration data can be acquired for new-company discovery before staffing classification and buyer-intent enrichment.  
**Evidence base:** the complete 50-state Scrapling/browser spike recorded on 2026-08-21, reconciled with fresh Scrapling checks on 2026-08-25. No CAPTCHA was solved, no policy restriction was bypassed, and no production connector or database was changed.

## Executive verdict

The deeper acquisition review changed the result. A CAPTCHA or blocked interactive search does not necessarily block the state's data: several states publish a separate bulk file, list-builder, subscription, or public-record extract.

- **31 states:** official formation-dated records are now technically proven through direct HTTP, an official file/feed, or a rendered browser. Alaska, California, Illinois and Mississippi moved into this group during the deeper review.
- **13 states:** a lawful official paid bulk, monthly-new-business, custom-query, or special-request route is documented: AZ, IN, KS, LA, ME, MD, NE, OK, SD, TX, UT, WV and WY.
- **1 state (VT):** an official account-gated bulk/download route exists, but enrollment and a sample/schema check remain before production approval. Vermont describes its weekly full dataset as free.
- **5 states (AL, DE, MI, TN and VA):** no unattended statewide feed is yet approved. The remaining route is a formal records request, manual use, or a licensed provider; Tennessee's replacement portal is reachable but its search submission remains reCAPTCHA-protected.

This means all 50 states now have a named acquisition route, but only **31 are technically proven for automation today**. “Named route” is not the same as “fully acquired”: account acceptance, payment, field-layout validation, permitted-use review and one real sample are still required for the other 19 states.

## Fifty-state matrix

| State | Verdict | Formation date | Best proven/official path | Important condition |
|---|---|---:|---|---|
| AL | Records-request route | Not yet sampled | SOS public-record request | No published bulk product was found. Alabama-citizen eligibility and commercial-use terms must be confirmed before requesting a recurring extract. |
| AK | Free, proven and freshly checked | Yes | Direct official CSV download | Scrapling received a 44 MB CSV with `AKFORMEDDATE`, entity number, legal name, status and registered-agent fields. |
| AZ | Paid official path | Yes | ACC manual database extract | $75 partial or $1,000 full extract; free search is CAPTCHA-gated. |
| AR | Free, proven | Yes | Plain HTTP live search/detail | `Date Filed` obtained from an official record. |
| CA | Free, proven weekly bulk | Yes | BizFile portal weekly unload; $100 master alternative | A real three-table package was validated: 6,904 unique filings for 2026-06-29 through 2026-07-06, with clean official IDs, dates, agents and principals. |
| CO | Free, proven and freshly checked | Yes | Socrata API | Fresh Scrapling sample returned entity name, status, type, address and `entityformdate`. |
| CT | Free, proven and freshly checked | Yes, with filtering | Socrata API | Feed contains reservation rows with `0001-01-01`; exclude reservations/invalid dates. |
| DE | Partial | Unconfirmed | WebForms search | Results and file numbers obtained; detail step triggers an anti-automation warning/cookie gate. |
| FL | Free, proven/built | Yes | Sunbiz bulk files | Existing project path; retain file-level provenance and date checks. |
| GA | Free, proven | Yes | Plain HTTP form POST/detail | `Date of Formation / Registration Date` obtained. |
| HI | Free record search, browser required | Yes | Rendered official search | Registration date obtained; bulk alternative is about $1,000/month. |
| IA | Free official bulk | Yes | Iowa Data Hub full download | Current catalog documents `effective_date`; old lightweight endpoint changed, so use the full-file route or re-discover the new query API. |
| ID | Free, proven and freshly checked | Yes | Public JSON POST endpoint | Fresh Scrapling response returned nine records with `FILING_DATE`, ID, type, agent and status. |
| IL | Free, proven and freshly checked | Yes | Daily official corporation and LLC ZIP files | Scrapling received valid ZIP ranges. LLC documentation includes organized date, status, agent, annual-report data and an IRS-purpose code. Do not automate the interactive query screen. |
| IN | Official account/paid path | New-registration period; sample needed | INBiz monthly new-business CSV | Prefer the monthly new-business list over the $9,500 full file. Account, exact price and sample columns still need confirmation. |
| KS | Paid official path with use restriction | Yes | SOS database access request | Active for-profit entities cost $200 and include formation date. Kansas restricts some commercial solicitation uses; counsel must approve the intended use. |
| KY | Free/proven, normal browser required | Yes | Live detail; official bulk also exists | Scrapling's default impersonation path was black-holed; normal browser succeeded. Commercial bulk is $2,000/month. |
| LA | Paid official custom-query path | Yes | SOS Commercial Database custom query | Formation/registration date is available. Minimum $25 for 40 records, then $0.01 per additional record. Do not automate the disallowed interactive search. |
| ME | Low-cost official monthly list | Yes | SOS monthly lists of new entities | $10 per entity category per month; lists include legal name, agent/address, filing date, charter number and jurisdiction. This is preferable to the $600+ bulk products for discovery. |
| MD | Paid official master/custom path | Needs layout validation | Corporate Master File via SpecPrint | Monthly master/weekly subscription; $0.04 per selected account with $40 minimum. Obtain the corporate file layout and verify original formation date before buying. |
| MA | Free, proven | Yes | Stateful WebForms search/detail | `Date of Declaration in Massachusetts` obtained. |
| MI | Formal-request route | Not yet sampled | LARA FOIA request | No published corporation bulk product was found. Request a current registry extract plus incremental-update options; do not scrape the restricted portal. |
| MN | Free, proven | Yes | Official bulk or rendered search | Formation/filing date confirmed; commercial bulk is $30/week. |
| MS | Free, proven and freshly checked | Yes | Business Reports JSON/report service | Scrapling received real JSON from the public report endpoint. It exposes formation date and three NAICS fields and supports Excel export up to 300,000 rows. |
| MO | Free, proven | Yes | Stateful WebForms POST | `Created` date is present in the results grid. |
| MT | Free, proven | Yes | Public JSON POST endpoint | Clean self-describing response with `FILING_DATE` / registration date. |
| NE | Paid official path | Yes | Special-request CSV | $15 per 1,000 records; free search is reCAPTCHA-gated. |
| NV | Free, proven | Yes | Scrapling rendered-browser search | Incapsula requires the rendered path; filing date obtained. |
| NH | Free, proven | Yes | Scrapling rendered-browser search/detail | Formation date and an actual NAICS field were obtained. |
| NJ | Free, proven | Yes | Plain HTTP POST | `Incorporated Date` is in the results grid. |
| NM | Free, proven | Yes | Public JSON API discovered from SPA | Raw JSON includes `RegistrationDate`, even though the UI grid omits it. |
| NY | Free, proven and freshly checked | Yes | SODA filings API | Fresh response returned filing/effective dates. Entity name lives in a companion dataset and must be joined by official identifiers. |
| NC | Free, proven | Yes | Scrapling rendered-browser search/detail | `Date formed` obtained; an official paid subscription is also available. |
| ND | Free, proven | Yes | Scrapling rendered-browser search | `Filing Date` is in the results grid. |
| OH | Free, proven | Yes | Rendered search with CSV export | Plain HTTP can receive a maintenance decoy; real browser path returned records and filing dates. |
| OK | Paid official path | Unconfirmed | Official bulk order | Live search is Turnstile-blocked; bulk is $500/month full or $150/week deltas. |
| OR | Free, proven and freshly checked | Yes | Socrata API | Fresh sample returned name, entity type, address and `registry_date`. |
| PA | Free, proven | Yes | Rendered search/API response capture | `Initial Filing Date` obtained; direct API replay remains Cloudflare-protected. |
| RI | Free, proven | Yes | Rendered WebForms search + direct detail | Strongest staffing pilot: NAICS appears in results and can be searched directly. |
| SC | Free, proven | Yes | Plain HTTP POST | Clean result table includes `Date of Incorporation`. |
| SD | Paid official subscription | New-entity listing available; layout needed | SOS Business Filings database | $1,500 initial setup includes the full database; monthly/weekly downloads and a monthly new-entity listing are offered. Confirm the chosen update price and fields on the order form. |
| TN | Reachable but gated | Registration date in portal schema | New TNCAB business search | Scrapling now reaches the replacement portal and its result schema includes `RegistrationDate`, but the search action is reCAPTCHA-protected. Use a records request or approved manual process unless SOS provides a feed. |
| TX | Paid SOS path | Yes per entity; bulk schema needs quote | SOSDirect plus SOS bulk-order contact | SOSDirect costs $1 per search. Ask Business & Public Filings for a formation-date-filtered recurring bulk order; do not substitute the wrong-purpose Comptroller API. |
| UT | Paid official list-builder | New-registration filter | Utah business data request | $5 includes 200 records, then $0.05 each. It can filter new registrations for 31/90/365 days and staffing NAICS codes; data updates weekly. |
| VT | Free account-gated weekly bulk | Search supports initial filing date | Business portal bulk database download | Vermont's 2025 legislative testimony says the full dataset is free and updated weekly. Account login and a live file/schema check remain. |
| VA | Official-request route | Likely; not yet sampled | SCC Clerk bulk/public-record request | Public business records exist, but the search site disallows crawling. Request the reportedly available weekly fixed-width extract and its current license/layout directly from SCC before using any third-party mirror. |
| WA | Free, proven | Yes | Scrapling rendered-browser search/detail | Formation date and `Nature of Business` obtained; old full bulk extract is discontinued. |
| WV | Paid official list/bulk path | Yes | Business Entity List Service | $25 minimum plus $0.05 per record; filters include original registration date, status, purpose and geography. File layouts also cover amendments, annual reports, mergers and other activity. |
| WI | Free, proven | Yes | WebForms search; inexpensive bulk alternative | `Registered Effective Date` obtained; monthly new-entity bulk file is $5/month. |
| WY | Paid official path | Unclear | SOS business-database subscription | Free POST is WAF-blocked; bulk costs $850/month or $10,200/year; inspect a sample before purchase. |

## Deep-access findings for the 23 previously unresolved states

| State | Best acquisition design | What is actually obtainable | Remaining approval/check |
|---|---|---|---|
| AK | Download the official corporations CSV and retain the source file hash. | Entity number, legal/assumed name, status, Alaska formed date, home jurisdiction, registered agent and addresses. | Confirm update cadence and implement incremental comparison locally. |
| AL | Submit a narrowly scoped recurring public-record request if Porter satisfies the requester-eligibility rule. | Ask for newly accepted domestic/foreign registrations, IDs, dates, type, status and addresses. | Alabama citizenship/identity requirement, price and commercial use. |
| AZ | Order a date-bounded database extraction instead of touching the CAPTCHA search. | CSV with incorporation/approval dates, names, addresses, agent, officers, status, domicile and type. | Commercial-purpose disclosure and approval; $75 partial extract. |
| CA | Ingest the free weekly three-table package and buy the $100 master only if historical coverage is required. | A live sample contains entity identity, status, jurisdiction, addresses, formation date, agents, principals and type-of-business text. | Confirm license/retention terms and compare the next two weeks to establish correction/replay semantics. |
| DE | Keep discovery manual or contract with a licensed Delaware data/registered-agent provider. | The official per-entity search exposes formation date and agent details. | Delaware explicitly prohibits automated data mining; no official bulk feed was found. |
| IL | Pull the published daily corporation and LLC ZIPs; never automate the query interface. | Formation/organized date, entity identity/type/status, agent, annual reports, managers/series and purpose codes. | Implement file parsing and daily checksum/version controls. |
| IN | Buy the monthly new-business CSV, not the full historical database. | Basic details for domestic and out-of-state businesses registered in the prior month. | INBiz account, price and sample column confirmation. |
| KS | Order the $200 active for-profit dataset or a custom extract. | ID, type, status, name, address, formation date/jurisdiction and resident agent. | Kansas statutory commercial-use restriction requires legal approval. |
| LA | Request a monthly custom query by registration date/entity type. | Name, status, incorporation/organization/registration date, addresses, agent and principals. | Define delivery format and cadence; minimum $25 plus $0.01 after 40 records. |
| ME | Subscribe to the $10 monthly lists for domestic/foreign corporations, LLCs, LPs and LLPs needed by the pilot. | Legal name, agent/address, filing date, charter number and jurisdiction. | Confirm electronic format/delivery; avoid the much costlier full bulk unless later justified. |
| MD | Purchase a small date-selected sample before committing to the corporate master. | Principal office, resident agent/address, amendments and trade-name filing dates are documented. | Verify that the entity record contains the original formation date, not only amendment dates. |
| MI | File a LARA FOIA request for a registry extract and incremental delivery. | Requested fields should include entity ID/name/type/status, formation/qualification date, jurisdiction and address. | Agency response, fee estimate, format, exemptions and reuse terms. |
| MS | Query the public reporting dataset by formation window and staffing NAICS; archive JSON/Excel evidence. | Formation date, business ID/name/type/status, address and up to three NAICS codes. | Prove the exact Kendo filter syntax and result completeness against an exported control total. |
| NE | Use the official special-request CSV with a registration/incorporation-date filter. | Immediate CSV download filtered by entity type, date, name keyword and location. | Buy a small sample batch first; published price is $15 per 1,000 records. |
| OK | Subscribe to the official master plus weekly deltas only after receiving the layout. | Official bulk and update products exist. | Formation-date field and update semantics are still unverified. |
| SD | Purchase the full database/appropriate update plan or monthly new-entity listing. | Password-protected ZIP/FTP delivery with monthly and weekly business-filing options. | Sample layout, exact price mapping and permitted-use review. |
| TN | Ask SOS for a recurring extract; retain manual portal use only as a fallback. | The new public portal's result model includes file number, entity name/type/status, city/state and registration date. | Search action remains reCAPTCHA-protected; no unattended feed is yet proven. |
| TX | Use SOSDirect for individual validation and request a recurring SOS bulk order for discovery. | SOS records provide formation facts; SOSDirect is $1 per search and the division accepts bulk-order inquiries. | Written quote, schema, cadence and licensed use. |
| UT | Run a weekly official custom list for NAICS 561311, 561320 and 561330 limited to new registrations in the last 31 days. | Business/address and principals/agents; source supports NAICS, status and new-registration filters. | Account/subscriber checkout and one purchased sample. |
| VT | Create a portal account and download one full business-data sample from `Bulk Database Download`. | The state says the full dataset is free and updated weekly; public search supports initial-filing-date filters. | Confirm post-login business-type choices, columns, file format and permitted reuse in the live portal. |
| VA | Ask the SCC Clerk for the current weekly business-record extract and fixed-width layout. | SCC states its business records are generally public; historical evidence indicates a weekly bulk file exists. | Only use a state-supplied file or a provider with proven current license/provenance. |
| WV | Buy date-filtered custom lists first; graduate to the account-gated bulk service only if needed. | Registration/filing dates, type/class/status/purpose, agents/officers and separate activity files. | One sample purchase and confirmation that commercial lead use is permitted. |
| WY | Obtain a one-month sample subscription before considering annual service. | Name/address, agent, officers/directors, status, standing and mailing address. | The published description does not explicitly promise formation date; reject for discovery if the sample lacks it. |

## Honest meaning of “fully”

A state is production-ready only after five independent gates pass:

1. **Authority:** the official terms or written state permission allow Porter's intended commercial use.
2. **Coverage:** the extract includes all relevant entity types, not only corporations or only active entities.
3. **Required fields:** official entity ID, legal name, entity type, jurisdiction, formation/registration date and source provenance are present.
4. **Freshness:** a documented daily/weekly/monthly cadence exists and late/corrected filings can be replayed.
5. **Reconciliation:** a bounded sample matches the state's search/control totals and the connector can replay without duplicate leads.

Passing a web request alone does not pass these gates. Paid and account-gated states should remain `candidate` connectors until a real file has been sampled and the five gates are documented.

## What this means for the staffing system

SOS records identify **new legal entities**, not reliably **staffing companies**. Only a few proven states expose useful industry data: RI has directly searchable NAICS; NH exposes NAICS on detail; KY has an industry classification; WA exposes a nature-of-business field. In most states, the correct workflow is:

1. Collect newly formed entities and their official identifiers/date evidence.
2. Classify likely staffing/PEO firms from names, websites and public business descriptions.
3. Resolve the entity to a canonical company without fuzzy auto-merging.
4. Search the web for job growth, expansion, contracts, leadership and hiring signals.
5. Send only evidence-backed, reviewable leads to Sales.

## Recommended rollout

1. **Pilot RI, MS and UT for staffing targeting.** RI and MS expose NAICS; Utah can sell a weekly list already filtered to staffing NAICS and recent registrations.
2. **Run NY, IL and AK as high-volume acquisition tests.** These exercise API/join, ZIP-bulk and CSV-bulk connector patterns without depending on an interactive search screen.
3. **Add CO, ID, MT, WI and ME next.** They are low-friction; Maine's monthly new-entity lists are unusually inexpensive.
4. **Enroll in California and Vermont in parallel.** Do not call them production-ready until a real bulk sample passes the five gates above.
5. **Buy small samples, not annual contracts.** Start with AZ ($75 partial), NE ($15/1,000), UT ($5/200) and WV ($25 minimum) before considering IN, SD or WY subscriptions.
6. **Send formal data requests to AL, MI, TN, TX and VA together.** Use one standard field/cadence/licensing questionnaire so responses are comparable.
7. **Keep Delaware manual.** Its official anti-data-mining restriction makes unattended collection an unacceptable design unless Delaware supplies written permission or a licensed provider supplies the data.

## Fresh live-check notes (2026-08-25)

- HTTP 200 plus structured official records: AK, CO, CT, ID, MS, NY and OR.
- Illinois corporation and LLC master URLs returned HTTP 206, valid ZIP signatures and advertised file sizes of roughly 82 MB and 54 MB respectively.
- Alaska's direct corporation download returned a 44 MB CSV whose header contains `AKFORMEDDATE`.
- Mississippi's public JSON service returned a real entity record from a population of more than one million and its reporting UI exposes Formation Date plus three NAICS fields.
- California's downloaded weekly package contained 6,904 unique filing IDs dated 2026-06-29 through 2026-07-06, plus clean agent/principal child tables. The detailed sample audit is `docs/research/california_weekly_bulk_sample_audit_2026-08-26.md`.
- TX returned structured official data, but not formation data.
- Iowa's current public catalog is live and documents 344,321 active records, monthly updates and an `effective_date`; its earlier query URL should not be reused without modification.
- The reproducible read-only check is `tools/scrapling_state_feed_check.py`.

## Official evidence for the deeper review

- **AK:** [direct Corporations CSV](https://www.commerce.alaska.gov/cbp/main/DbDownload/CorporationsDownload)
- **AL:** [public-record request](https://www.sos.alabama.gov/public-records-request)
- **AZ:** [database extraction request and field list](https://www.azcc.gov/docs/default-source/corps-files/forms/m027-database-extraction-request4afa009930ae4583a9310593ba4c65ce.pdf?sfvrsn=73637fee_6)
- **CA:** [Business Entity records and fields](https://www.sos.ca.gov/business-programs/business-entities/information-requests) and [BizFile/UCC portal manual](https://bpd.cdn.sos.ca.gov/ucc/ucc-online-help.pdf)
- **DE:** [official entity-information limits](https://corp.delaware.gov/more-information/) and [official search](https://icis.corp.delaware.gov/ecorp/EntitySearch/NameSearch.aspx)
- **IL:** [Data Transparency Act bulk files](https://www.ilsos.gov/data/bus-serv-home.html) and [LLC layout](https://www.ilsos.gov/content/dam/data/bs/proc_llc_data.pdf)
- **IN:** [INBiz Bulk Data Services](https://inbiz.in.gov/inbiz/bulkdataservices/index)
- **KS:** [Database Records Access Request](https://www.sos.ks.gov/forms/elections/RAR.pdf)
- **LA:** [custom computer-query ordering](https://www.sos.la.gov/business-services/how-to-order)
- **ME:** [monthly new-entity lists and bulk data](https://www.maine.gov/sos/corporations-commissions/incorporating-resources/corporations-commissions/miscellaneous-service-lists-and-bulk-data)
- **MD:** [Corporate Master File service](https://dat.maryland.gov/pages/services.aspx)
- **MI:** [LARA FOIA request](https://www.michigan.gov/lara/foia-request)
- **MS:** [free Business Reports search/export](https://corp.sos.ms.gov/corpreporting/Corp/BusinessSearch3)
- **NE:** [Corporate Searches — Special Requests](https://sos.nebraska.gov/business-services/corporate-and-business)
- **OK:** [official corporation bulk order](https://www.sos.ok.gov/corp/bulkorder/bulkDefault.aspx)
- **SD:** [Business/UCC database subscription](https://sdsos.gov/docs/ucc-docs/NEWBusinessUCCDatabaseSubscriptionForm.pdf)
- **TN:** [replacement TNCAB portal](https://tncab.tnsos.gov/portal/business-entity-search)
- **TX:** [SOSDirect access and price](https://www.sos.state.tx.us/corp/sosda/index.shtml) and [Business & Public Filings contact](https://www.sos.state.tx.us/corp/contact.shtml)
- **UT:** [official business-list builder](https://secure.utah.gov/datarequest/businesses/index.html)
- **VT:** [official business portal](https://bizfilings.vermont.gov/), [public business search](https://bizfilings.vermont.gov/business/businesssearch), and [2025 Secretary of State testimony describing a free weekly full dataset](https://legislature.vt.gov/Documents/2026/Workgroups/House%20Energy%20and%20Digital/Data/W~Lauren%20Hibbert~Transparency%20and%20Accessibility%20of%20SOS%20Data~4-29-2025.pdf)
- **VA:** [SCC Clerk public-record scope](https://www.scc.virginia.gov/businesses/about-the-clerks-office/)
- **WV:** [Business Entity List Service](https://apps.wv.gov/sos/businessentity/) and [file layout](https://apps.wv.gov/sos/businessentity/BEL_FileInformation.pdf)
- **WY:** [bulk-data FAQ](https://sos.wyo.gov/FAQS.aspx?root=BUS) and [subscription form](https://sos.wyo.gov/Forms/Business/General/WYSOS-BusinessDatabaseDownload.pdf)
