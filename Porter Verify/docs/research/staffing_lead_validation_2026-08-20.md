# Staffing lead-source validation — 2026-08-20

## Outcome

The Massachusetts Department of Labor Standards staffing register is a viable top-of-funnel source when it is joined to the Massachusetts corporate registry and then screened against current operating evidence, the UCC index, and SBA loan files.

This test produced **two outreach-ready, public-record-clean candidates** from a small manual sample: **VeraPro Staffing Solutions Inc** and **ABABAS Health Service LLC**. “Public-record-clean” means no Massachusetts UCC debtor filing and no exact-name SBA 7(a)/504 match were found. It does **not** prove that the company has no unsecured loan, private debt, or financing filed under another debtor name.

The raw register is not a lead list by itself. Several plausible rows failed because the company was too new, had no current operating evidence, or only had a template-style website.

The row-level results are also available in [the spot-check CSV](./staffing_lead_spot_checks_2026-08-20.csv).

## Source stack that worked

1. **Industry/operating authority:** [Massachusetts current employment and placement agency register](https://www.mass.gov/doc/list-of-currently-licensed-employment-and-placement-agencies). The downloaded workbook was updated 2026-08-10 and contained 1,225 rows; 558 Massachusetts rows were marked `Staffing Agency = Yes`.
2. **Meaning of the signal:** [Massachusetts DLS explains that staffing agencies procure or provide temporary or part-time employment](https://www.mass.gov/info-details/information-for-employment-agencies), must be licensed or registered, and renew annually. [M.G.L. c. 149 §159C](https://malegislature.gov/Laws/GeneralLaws/PartI/TitleXXI/Chapter149/Section159C) covers assignments, pay-day/rate disclosures, workers' compensation carrier disclosure, and payroll-card/wage rules.
3. **Legal identity and age:** [Massachusetts corporate database](https://corp.sec.state.ma.us/CorpWeb/CorpSearch/CorpSearch.aspx), checked by exact legal name and confirmed with address, contact/officer, entity ID, and organization date.
4. **Current operations:** a live company recruiting flow plus a dated live job posting where available. A dated posting within 45 days is the preferred proof.
5. **Secured-financing exclusion:** [Massachusetts UCC database](https://corp.sec.state.ma.us/CorpWeb/UCCSearch/UCCSearch.aspx), searched twice under the exact legal debtor name: the standard `Article 9` normalization and the informational `Exact Match` mode, with all dates/cities/states included.
6. **Government-backed financing exclusion:** [SBA 7(a) & 504 FOIA files](https://data.sba.gov/dataset/7a-504-foia), using the FY2020-present 7(a) and FY2010-present 504 CSVs, both current through 2026-06-30.

## Outreach-ready candidates

### VeraPro Staffing Solutions Inc — high confidence

- DLS credential: placement agency `R11624`, `Staffing Agency = Yes`, expires 2027-06-09; Tyngsboro; contact Natalie Sokhom; phone 978-822-4039.
- Corporate identity: Massachusetts entity `001938472`, organized 2026-01-06. The Tyngsboro location and Natalie Sokhom match the DLS row.
- Operating proof: the [company site](https://www.veraprostaffing.com/) offers temporary and temp-to-perm light-industrial staffing. A [Senior AOI Operator listing](https://www.ziprecruiter.com/c/VeraPro-Staffing-Solutions/Job/Senior-AOI-Operator/-in-Merrimack,NH?jid=2fd3020f434479c8) was live and marked “Posted 22 days ago” on 2026-08-20, with an active apply path.
- Financing screen: no record under both Massachusetts UCC search modes; no exact-name match in the current SBA 7(a) or 504 files.
- Caveat: the company site shows 5 Pondview Place while the corporate record shows 7 Pondview Place. Name, city, phone, and officer/contact match, so this appears to be an operating-versus-records address variation, but it should be confirmed during outreach.

### ABABAS Health Service LLC — medium-high confidence

- DLS credential: placement agency `R11597`, `Staffing Agency = Yes`, expires 2027-03-24; Fall River; contact Bakary Jatta; phone 978-631-7506.
- Corporate identity: Massachusetts entity `001929674`, organized 2025-11-21. The legal name, 41 Donnelly Street address, and Bakary Jatta match the DLS row.
- Operating proof: the [company site](https://ababashealthservice.com/) advertises per-diem shifts, short/long-term placements, rapid-response coverage, and active recruiting for CNAs, LPNs, and RNs. The phone and founder match the official records.
- Financing screen: no record under both Massachusetts UCC search modes; no exact-name match in the current SBA 7(a) or 504 files.
- Caveat: the recruiting page is current but does not expose a dated individual job requisition. Keep this below VeraPro until a recent assignment, job order, or payroll volume is confirmed by phone.

## Manual rejects and why they matter

| Candidate | Result | Reason |
|---|---|---|
| On Point Construction Staffing, Inc. | Reject | Organized 2026-06-29, below the six-month age floor. |
| Mason Employment LLC | Reject | Identity and age matched, but no operating footprint was found beyond the state register. |
| Transcending Staffing Solutions Inc | Reject | Identity and age matched, but the site retained template artifacts (`Lovable App`, `CareStaff Pro`, placeholder social links) and exposed no live jobs. |
| Alpha & Omega Staffing Agency LLC | Reject for now | Current staffing registration and a state temporary-nursing-agency listing, but no current job or assignment evidence was found. |
| Collective Care Staffing LLC | Reject | Organized 2024-07-31, just outside the strict 24-month age ceiling on the test date. |
| Patriot Healthcare Services LLC | Manual review | Age, current DLS credential, phone, operating address, and career application flow are plausible, but the corporate records address/contact differ and the UCC/SBA screen was not completed. Do not treat as confirmed yet. |

## Repeatable decision rule

A candidate becomes `outreach-ready` only when all of these are true:

1. DLS row is marked `Staffing Agency = Yes` and the credential expiration is after the run date.
2. Exact corporate identity resolves, and the organization date is 6–24 months old.
3. At least two identity fields agree across sources: legal name plus one of address, phone, or named officer/contact.
4. Current operations are supported by a live dated job/requisition within 45 days, or by a current recruiting/application flow plus another independent operating signal.
5. Massachusetts UCC `Article 9` and `Exact Match` searches both return no debtor records.
6. SBA 7(a) and 504 current files contain no normalized exact-name match.

Use these labels:

- `high`: dated live job + current credential + verified identity + clean UCC/SBA screen.
- `medium-high`: current recruiting/placement flow without a dated requisition + verified identity + clean UCC/SBA screen.
- `manual-review`: one required check is incomplete or identity fields conflict.
- `reject`: age, credential, operating-evidence, identity, or financing screen fails.

## Sources tested that did not work as primary automation

- **Illinois day/temp labor registration:** conceptually strong, but the live IDOL page currently exposes an old 2023 file while search indexes reference newer PDFs whose direct links now return 404. Illinois entity and UCC searches also presented challenge validation/CAPTCHAs. This is usable only as a human-assisted queue until publication stabilizes.
- **Illinois home-services placement open data:** accessible and useful for a narrow placement niche, but it does not reliably prove that the agency runs payroll; several rows were already expired relative to 2026-08-20.
- **MassHire JobQuest:** the official board supports public UI search and export but no public employer API was found. An exact VeraPro keyword search returned zero results while a live external job board showed a posting 22 days old, so JobQuest absence is not a rejection signal.
- **Massachusetts workers' compensation proof of coverage:** [Mass.gov identifies the source](https://www.mass.gov/how-to/check-for-workers-compensation-insurance), and the underlying search was updated 2026-08-20, but it requires a reCAPTCHA. It is valuable as an optional human confirmation, not an unattended connector. Mass.gov also warns that no result does not prove no coverage because policies may use another name or self-insurance.
- **Generic web absence:** not used as a negative conclusion. It only triggered manual review.

## Recommended production shape

Automate register ingestion, expiration filtering, age calculation, normalized SBA matching, and queue generation. Keep corporate identity, current-job confirmation, and UCC review as evidence-captured browser steps unless/until stable APIs are available. Store the source URL, retrieval date, exact searched name, search mode, and a screenshot or result text for every financing decision.
