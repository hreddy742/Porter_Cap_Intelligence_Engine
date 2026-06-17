
Porter Verify
Business Verification & Lead Intelligence Platform
Company-Grade, Production-Ready Product Plan
Prepared for: Porter Capital — Product, Engineering, Security & Leadership
Version 1.0  |  June 16, 2026
Honesty note: This plan separates FACT (publicly verifiable), ASSUMPTION (reasonable, stated), and UNKNOWN (must be validated). It uses only public product understanding and standard enterprise patterns. It does not copy any proprietary system, private API, or private code. Where an external API or data coverage cannot be confirmed publicly, it is marked UNKNOWN with a validation method.

Table of Contents
TOC \h \o "1-2"Table of Contents PAGEREF _Toc232581696 \h 1
1. Executive Summary PAGEREF _Toc232581697 \h 1
1.1 Main risks (top 5) PAGEREF _Toc232581698 \h 1
2. Product Vision PAGEREF _Toc232581699 \h 1
2.1 Target internal users PAGEREF _Toc232581700 \h 1
2.2 Vision: long-term vs MVP PAGEREF _Toc232581701 \h 1
2.3 Success at 30 / 60 / 90 days PAGEREF _Toc232581702 \h 1
2.4 Connection to Porter's workflows PAGEREF _Toc232581703 \h 1
3. User Personas PAGEREF _Toc232581704 \h 1
4. Core Use Cases PAGEREF _Toc232581705 \h 1
5. MVP Scope PAGEREF _Toc232581706 \h 1
5.1 MVP features (in) PAGEREF _Toc232581707 \h 1
5.2 MVP non-features (out) PAGEREF _Toc232581708 \h 1
5.3 MVP building blocks PAGEREF _Toc232581709 \h 1
5.4 MVP exit criteria PAGEREF _Toc232581710 \h 1
6. Phase Roadmap PAGEREF _Toc232581711 \h 1
Phase 0 — Discovery & validation (1–2 wk) PAGEREF _Toc232581712 \h 1
Phase 1 — Shippable MVP (4–6 wk) PAGEREF _Toc232581713 \h 1
Phase 2 — Data coverage & UCC intelligence (4–8 wk) PAGEREF _Toc232581714 \h 1
Phase 3 — Salesforce workflow integration (4–6 wk) PAGEREF _Toc232581715 \h 1
Phase 4 — Underwriting & document automation support (4–6 wk) PAGEREF _Toc232581716 \h 1
Phase 5 — Monitoring, alerts & risk intelligence (ongoing) PAGEREF _Toc232581717 \h 1
7. Feature Requirements PAGEREF _Toc232581718 \h 1
8. Data Source Strategy PAGEREF _Toc232581719 \h 1
8.1 Per-source notes & how to validate PAGEREF _Toc232581720 \h 1
9. System Architecture PAGEREF _Toc232581721 \h 1
9.1 Recommended stack & why PAGEREF _Toc232581722 \h 1
9.2 Logical architecture PAGEREF _Toc232581723 \h 1
9.3 Connector framework (the swappability contract) PAGEREF _Toc232581724 \h 1
9.4 Component responsibilities (brief) PAGEREF _Toc232581725 \h 1
9.5 Environments PAGEREF _Toc232581726 \h 1
10. Database Design PAGEREF _Toc232581727 \h 1
10.1 Table catalog PAGEREF _Toc232581728 \h 1
10.2 Representative DDL PAGEREF _Toc232581729 \h 1
10.3 Data-handling rules PAGEREF _Toc232581730 \h 1
11. Entity Resolution Strategy PAGEREF _Toc232581731 \h 1
11.1 Signals (strong → weak) PAGEREF _Toc232581732 \h 1
11.2 Normalization before comparison PAGEREF _Toc232581733 \h 1
11.3 Algorithm & thresholds PAGEREF _Toc232581734 \h 1
11.4 Error handling PAGEREF _Toc232581735 \h 1
12. Scoring and Confidence Model PAGEREF _Toc232581736 \h 1
12.1 Component scores PAGEREF _Toc232581737 \h 1
12.2 Overall verification status (derived) PAGEREF _Toc232581738 \h 1
12.3 Limitations (stated honestly) PAGEREF _Toc232581739 \h 1
13. UI / Dashboard Plan PAGEREF _Toc232581740 \h 1
14. API Design PAGEREF _Toc232581741 \h 1
15. Security and Compliance Plan PAGEREF _Toc232581742 \h 1
16. Reliability and Operations Plan PAGEREF _Toc232581743 \h 1
17. Testing Plan PAGEREF _Toc232581744 \h 1
17.1 Manual QA checklist (pre-MVP-ship) PAGEREF _Toc232581745 \h 1
17.2 Test data plan PAGEREF _Toc232581746 \h 1
17.3 Acceptance criteria to ship MVP PAGEREF _Toc232581747 \h 1
18. Development Plan PAGEREF _Toc232581748 \h 1
19. Deployment Plan PAGEREF _Toc232581749 \h 1
20. Build vs Buy / Vendor Strategy PAGEREF _Toc232581750 \h 1
21. Cost and Resource Estimate PAGEREF _Toc232581751 \h 1
21.1 Team PAGEREF _Toc232581752 \h 1
21.2 Timeline PAGEREF _Toc232581753 \h 1
21.3 Run costs (ranges to validate) PAGEREF _Toc232581754 \h 1
21.4 Hidden & ongoing costs PAGEREF _Toc232581755 \h 1
22. Risk Register PAGEREF _Toc232581756 \h 1
23. Leadership-Ready Recommendation PAGEREF _Toc232581757 \h 1
23.1 First 10 next steps PAGEREF _Toc232581758 \h 1
23.2 The decision leadership must make PAGEREF _Toc232581759 \h 1
24. Engineer-Ready Execution Summary PAGEREF _Toc232581760 \h 1
24.1 First sprint (2 weeks) tasks PAGEREF _Toc232581761 \h 1
24.2 Required repo structure PAGEREF _Toc232581762 \h 1
24.3 Required stack PAGEREF _Toc232581763 \h 1
24.4 First database migrations PAGEREF _Toc232581764 \h 1
24.5 First connector to build PAGEREF _Toc232581765 \h 1
24.6 First dashboard page PAGEREF _Toc232581766 \h 1
24.7 First tests to write PAGEREF _Toc232581767 \h 1
24.8 First deployment target PAGEREF _Toc232581768 \h 1
24.9 Definition of done for MVP PAGEREF _Toc232581769 \h 1
Appendix: Public Sources PAGEREF _Toc232581770 \h 1


Reading key: FACT = confirmable from public sources. ASSUMPTION = our reasonable working premise (validate if cheap). UNKNOWN = we genuinely do not know; do not build on it until validated.
1. Executive Summary
What we are building. Porter Verify is an internal, evidence-backed platform that tells Porter, in seconds, whether a business lead is real, active, correctly named, registered, lien-encumbered, and worth pursuing — and writes that verified profile back into Salesforce. It is inspired by the public business-verification category (e.g., Cobalt Intelligence, Middesk) but is Porter's own original system, tuned to factoring/asset-based-lending decisions rather than generic KYB.
Why Porter needs it. Porter advances cash against invoices and assets, often within ~24 hours, underwriting on the strength of the receivable and the account debtor. Before a rep spends time and before underwriting commits, Porter must know the applicant is a genuine, active legal entity and understand existing UCC liens that affect collateral priority. Today this is manual: analysts check state websites by hand — slow, inconsistent, and unauditable.
Business problem solved. Cut manual research time, stop wasting sales effort on shells/dissolved entities, surface lien risk early, and give underwriting a clean, sourced, defensible business profile — with a full audit trail Porter can show in an exam.
First shippable version (MVP). A small internal web app + API where a user searches a business by name + state, the system fetches the Secretary of State record (via a purchased vendor connector), normalizes status, captures immutable evidence (timestamped record + hash), produces an explainable confidence status, routes ambiguous cases to a human-review queue, screens against OFAC, and lets a user export the verified profile to Salesforce. Useful on day one even though it is not perfect.
What NOT to build yet. No 50-state in-house scraping engine; no automated credit decisioning; no ML scoring; no native Salesforce embedded UI; no full underwriting automation; no public/external API product. These come in later phases or never.
Why it's valuable. It converts a manual, error-prone task into a fast, consistent, audited workflow that feeds both sales prioritization and underwriting — and the durable IP (workflow, data model, scoring, evidence, Salesforce integration) stays inside Porter while the commodity data layer is rented and swappable.
1.1 Main risks (top 5)
#
Risk
Why it matters
1
UCC/lien coverage gaps
Highest underwriting value, weakest public data; must be validated on real Porter deals before promising it.
2
Entity false-match
Attaching wrong status/liens to a deal corrupts an underwriting decision; mitigated by conservative matching + human review.
3
Vendor cost & lock-in
Per-lookup pricing can balloon; mitigated by caching, swappable connectors, selective insourcing of free gov APIs.
4
Legal/ToS exposure
Direct scraping of gov sites is risky; rent data, restrict Playwright to entitled evidence capture.
5
Salesforce data quality
Messy CRM input degrades matching; mitigated by validation, dedupe, write-back of canonical legal name.
Bottom line: Build the platform, rent the data. MVP is achievable in ~8–12 weeks with 1–2 engineers if SOS data is purchased rather than scraped.

2. Product Vision
Product name: Porter Verify (internal). Alternatives: Beacon, PorterIQ.
Purpose: Be Porter's single source of truth for “is this business real, active, and factorable?” — evidence-backed, auditable, and wired into Salesforce.
2.1 Target internal users
Sales / Business Development (lead qualification & prioritization).
Underwriting / Credit (entity + lien verification, KYB packet).
Operations / Data (bulk list cleaning, portfolio re-verification).
Management / Leadership (throughput, risk, ROI reporting).
Engineering / Admin (connectors, vendor keys, users, config).
Compliance / Audit (read-only evidence & audit trail).
2.2 Vision: long-term vs MVP
Horizon
Vision
Long-term (12–18 mo)
A lead-to-underwriting risk spine: every company Porter touches has a living, sourced profile with status, officers, UCC position, sanctions, a factorability score, and continuous monitoring — feeding sales routing and underwriting automation.
MVP (8–12 wk)
One thing done well: fast, evidence-backed entity + status verification with human review and Salesforce export, powered by a swappable vendor connector + OFAC.
2.3 Success at 30 / 60 / 90 days
Day
What success looks like
30
Phase 0 done: vendor chosen via bake-off on real Porter leads; Salesforce schema mapped; legal sign-off on data use; repo + CI + staging stood up.
60
MVP in pilot: one sales pod + one underwriter verifying from the dashboard; evidence stored; review queue working; baseline accuracy measured on a golden set.
90
MVP adopted: >70% of test leads auto-verify, false-match <1%, manual research time measurably down; Salesforce export in use; go/no-go on Phase 2 (UCC).
2.4 Connection to Porter's workflows
Lead gen → new lead enters Salesforce → Porter Verify enriches it (legal name, status, age, score, evidence link) → reps prioritize real, active, factorable businesses.
Sales → reps stop researching manually; they act on a confidence status + evidence.
Underwriting → the same resolved entity carries forward into a KYB packet (entity + officers + UCC + sanctions + evidence) for human credit review.
Monitoring (later) → the active funded book is re-checked; adverse changes (dissolution, new senior UCC) raise alerts.

3. User Personas
Sales Rep / SDR (“Dana”)
Dimension
Detail
Goals
Spend time only on real, fundable businesses; qualify fast.
Pain today
Manually checks SOS sites; gets burned by shells/dissolved entities; inconsistent notes.
Needs
A clear status + score on each lead; one-click verify; evidence link.
Screens/workflows
Home dashboard, company search, company profile, Salesforce lead view.
Decisions enabled
Pursue / deprioritize / send to research.

Underwriter / Credit Analyst (“Marcus”)
Dimension
Detail
Goals
Confirm entity legitimacy and lien position before committing capital.
Pain today
Re-does verification; UCC research is slow and fragmented; weak audit trail.
Needs
Full KYB packet, parsed UCC with lien position, evidence with timestamps/hashes, ability to record a decision.
Screens/workflows
Company profile, UCC section, evidence timeline, review decision panel, report export.
Decisions enabled
Approve / reject / needs-more-info; record rationale (logged).

Operations / Data Analyst (“Priya”)
Dimension
Detail
Goals
Clean lead lists; re-verify the portfolio periodically.
Pain today
Bulk research is impractical by hand.
Needs
CSV bulk verify; scheduled re-verification; export; error visibility.
Screens/workflows
Bulk upload, run summary, data quality dashboard, error dashboard.
Decisions enabled
Which records need human review; list hygiene actions.

Management / Leadership (“Elena”)
Dimension
Detail
Goals
More throughput without more headcount; lower risk; clear ROI.
Pain today
No visibility into research effort or lead quality.
Needs
Metrics: verification volume, auto-verify rate, time saved, risk flags.
Screens/workflows
Home dashboard (aggregate), reports.
Decisions enabled
Resourcing; phase go/no-go; vendor spend.

Engineering / Admin (“Sam”)
Dimension
Detail
Goals
Keep sources healthy; manage access and config safely.
Pain today
N/A (new system).
Needs
Source registry, credential management (secret refs), user/role admin, health/error dashboards.
Screens/workflows
Admin settings, source health, error dashboard.
Decisions enabled
Enable/disable sources; rotate keys; manage users — no credit decisioning.

Compliance / Auditor (“Rosa”)
Dimension
Detail
Goals
Prove what was verified, when, from where.
Pain today
Evidence scattered; no point-in-time proof.
Needs
Read-only access to evidence + immutable audit trail; export for exams.
Screens/workflows
Evidence timeline, audit log view, report export.
Decisions enabled
Attestation; exam readiness (read-only).


4. Core Use Cases
Each use case lists user, input, system actions, output, edge cases, failure cases, and required audit log.
UC-1 Verify a business from a lead
Aspect
Detail
User
Sales rep / auto-trigger from Salesforce.
Input
Business name + state (optional address, EIN claim, website).
System actions
Normalize → select connector → fetch SOS → normalize status → OFAC screen → resolve entity → score → capture evidence → persist.
Output
Verification status + confidence + key fields + evidence link.
Edge cases
Multiple candidates; multi-state entity; missing fields for that state.
Failure cases
State source down → queue/retry, mark source_unavailable, no charge; no match → “insufficient evidence.”
Audit log
run id, actor, inputs, sources hit, result, evidence hashes.

UC-2 Search for a business by name/state
Aspect
Detail
User
Any authorized user.
Input
Partial/full name + optional state.
System actions
Fuzzy + exact search over cached companies and (optionally) live source; rank candidates.
Output
Candidate list with status + match score.
Edge cases
Common names; cross-state duplicates.
Failure cases
No results → empty state with “run live verify” option.
Audit log
query terms, actor, timestamp.

UC-3 Match a company to a Salesforce lead/account
Aspect
Detail
User
Rep / system.
Input
Salesforce record (name, address, website, owner-provided fields).
System actions
Entity resolution against verified companies; compute SF match confidence.
Output
Linked company id + match confidence, or “needs review.”
Edge cases
SF record has only a DBA; stale SF address.
Failure cases
Ambiguous → review queue; never auto-link below threshold.
Audit log
sf record id, chosen company, score, decision.

UC-4 View business registration evidence
Aspect
Detail
User
Underwriter / auditor.
Input
Company id.
System actions
Fetch evidence items + raw record; verify hash.
Output
Evidence timeline with timestamped record + source URL + hash.
Edge cases
Evidence missing for older record.
Failure cases
Storage unavailable → error state, alert.
Audit log
read of evidence by actor (sensitive-read).

UC-5 View UCC / lien evidence
Aspect
Detail
User
Underwriter.
Input
Verified company id.
System actions
Query UCC connector(s); parse filings; compute lien position.
Output
Lien list (secured party, collateral, dates, status) + position + evidence.
Edge cases
State not covered → explicit “not checked”; debtor-name ambiguity.
Failure cases
Partial coverage → never imply “no liens” for unchecked states.
Audit log
query, sources, results, evidence.

UC-6 Review confidence score
Aspect
Detail
User
Rep / underwriter.
Input
Company id.
System actions
Display score components + evidence behind each.
Output
Status + component breakdown (explainable).
Edge cases
Low data completeness → “insufficient evidence.”
Failure cases
N/A (read).
Audit log
read event.

UC-7 Mark company approved / rejected / needs review
Aspect
Detail
User
Underwriter / manager.
Input
Decision + reason.
System actions
Persist review_decision; update status; (optional) push to SF.
Output
Updated status + decision record.
Edge cases
Override of system status → require reason.
Failure cases
Concurrent edits → optimistic lock.
Audit log
decision, reason, actor, before/after (immutable).

UC-8 Push verified/enriched info to Salesforce
Aspect
Detail
User
Rep / system.
Input
Company id + SF record id.
System actions
Map fields → idempotent upsert via SF API → record sync status.
Output
Updated SF record + evidence URL; sync status.
Edge cases
SF field missing / picklist mismatch.
Failure cases
SF API error → retry/backoff; mark sync_failed.
Audit log
sync attempt, fields, result.

UC-9 Generate internal verification report (PDF)
Aspect
Detail
User
Underwriter / compliance.
Input
Company id.
System actions
Assemble KYB packet (entity, officers, UCC, sanctions, evidence, scores) → render PDF.
Output
Branded PDF + stored copy + hash.
Edge cases
Missing sections labeled “not available.”
Failure cases
Render error → retry; alert.
Audit log
report generated by actor, hash.

UC-10 Track data source errors
Aspect
Detail
User
Admin.
Input
N/A (system-generated).
System actions
Capture connector failures; classify; surface on error dashboard.
Output
Error list + source health.
Edge cases
Transient vs persistent.
Failure cases
N/A.
Audit log
source events + errors retained.

UC-11 Review duplicate company candidates
Aspect
Detail
User
Ops / admin.
Input
Duplicate cluster.
System actions
Show candidates + signals; allow reviewed merge (history-preserving).
Output
Merged canonical company (no hard delete).
Edge cases
False duplicates.
Failure cases
Never auto-merge on fuzzy name alone.
Audit log
merge action, source/target, actor.

UC-12 Review low-confidence matches
Aspect
Detail
User
Underwriter / ops.
Input
Review queue item.
System actions
Show candidates + evidence; accept/reject.
Output
Resolved match + decision.
Edge cases
No good candidate → mark no-match.
Failure cases
N/A.
Audit log
decision + reason.


5. MVP Scope
Scope discipline: The MVP does ONE workflow well — verify a business + capture evidence + human review + Salesforce export. Everything else waits.
5.1 MVP features (in)
Company search (name + state) over cache + live vendor connector.
Verification run: fetch SOS via vendor → normalize status → OFAC screen → resolve → score → evidence.
Company profile page with evidence timeline.
Explainable confidence status (rule-based).
Manual review queue for low-confidence/ambiguous.
Manual Salesforce export (CSV or single-record push).
Admin: source registry + user/role + health/error views.
Audit log on all runs/decisions/reads of sensitive data.
5.2 MVP non-features (out)
No in-house SOS scraping; no UCC in MVP (Phase 2).
No native Salesforce embedded UI / auto-trigger (Phase 3).
No ML scoring; no monitoring/alerts; no underwriting automation.
No external/sellable API; no consumer KYC.
5.3 MVP building blocks
Layer
MVP content
Data sources
1 SOS/KYB vendor (chosen in Phase 0) + OFAC list ingest.
Dashboard screens
Login, Home, Search, Company Profile (+evidence), Review Queue, Admin (sources/users), Error/Health.
Backend services
API, verify orchestration (Prefect), connector framework (vendor + OFAC), entity resolution v1, scoring v1, evidence service, audit service.
Database tables
source_registry, source_credentials, companies, company_identifiers, business_registrations, registered_agents, company_officers, verification_runs, raw_source_events, evidence_items, confidence_scores, review_decisions, salesforce_sync_status, users, roles, audit_logs, error_logs.
Review workflow
Queue → candidate disambiguation → accept/reject with reason.
Security
SSO+MFA, RBAC, secrets manager, TLS, encryption at rest, audit logging, rate limiting.
Logs
Structured JSON logs, Sentry, audit_logs, error_logs.
Deployment
Docker, GitHub Actions CI, staging + production, managed Postgres, object store for evidence.
Tests
Unit, connector contract, entity-resolution golden set, API, permission, source-failure.
5.4 MVP exit criteria
>70% of a real Porter test-lead set auto-verify without human touch.
False-match rate <1% and status-correctness >98% on a labeled golden set.
Every run produces immutable evidence + audit entries; OFAC runs in-flow.
Connector proven swappable (a second stub passes the same contract tests).
Pilot users (sales + underwriting) confirm measurable time savings.

6. Phase Roadmap
Phase 0 — Discovery & validation (1–2 wk)
Aspect
Detail
Goal
De-risk before code: confirm data coverage, vendor fit, Salesforce reality, legal.
Features
None (research artifacts).
Data sources
Vendor trials (Cobalt, Middesk); sample of real Porter leads.
Backend
Throwaway scripts to call vendors + compare coverage.
Frontend
None.
Security
Handle sample data under existing controls.
Testing
Manual accuracy check vs known-good entities.
Deployment
None.
Risks
Coverage (esp. UCC) worse than hoped; messy SF data.
Exit criteria
Vendor chosen; coverage documented; legal sign-off; go/no-go.
Not yet
Connectors, UI, scoring.

Phase 1 — Shippable MVP (4–6 wk)
Aspect
Detail
Goal
Automated, evidence-backed entity + status verification with review.
Features
Search, verify, profile, evidence, confidence status, review queue, manual SF export, admin.
Data sources
Chosen vendor + OFAC.
Backend
FastAPI, Postgres, Prefect, connector framework v1, ER v1, scoring v1, evidence, audit.
Frontend
Streamlit dashboard (see §9 rationale).
Security
SSO/RBAC, secrets, TLS, encryption, audit, rate limit, staging/prod split.
Testing
Unit, connector contract, ER golden set, API, permission, source-failure.
Deployment
Docker + GitHub Actions; staging then production.
Risks
Match accuracy; status normalization edge cases.
Exit criteria
§5.4 met; pilot adoption.
Not yet
UCC, native SF, monitoring, ML.

Phase 2 — Data coverage & UCC intelligence (4–8 wk)
Aspect
Detail
Goal
Add the highest-value lending data: liens, officers, sanctions on officers, scoring.
Features
UCC lookup + parsed liens + lien-position; officer screening; factorability score; bulk + scheduled re-verify; dedupe/merge tooling.
Data sources
UCC vendor + covered states; SAM.gov; optional enrichment.
Backend
UCC connector(s), scoring engine v2, bulk job system.
Frontend
UCC section, bulk upload + run summary, data quality dashboard.
Security
Field-level access for lien/officer PII; vendor DPAs.
Testing
UCC precision/recall; scoring validation; bulk + rate-limit.
Deployment
Scheduled jobs in Prefect.
Risks
UCC coverage gaps; debtor-match false positives.
Exit criteria
UCC on majority of real deals with explicit gap labeling; score tracks analyst judgment.
Not yet
Full underwriting automation.

Phase 3 — Salesforce workflow integration (4–6 wk)
Aspect
Detail
Goal
Put verification where reps/underwriters work; auto-trigger + write-back.
Features
Bidirectional SF sync, one-click verify, evidence links on Lead/Account, KYB packet PDF.
Data sources
Same as P2.
Backend
SF REST/Bulk + Platform Events/webhooks; PDF generation.
Frontend
SF Lightning component or flow action; in-context review.
Security
Scoped connected app; no secrets client-side; sync audit.
Testing
SF sync (idempotency, conflict, partial-failure); packet correctness.
Deployment
SF managed package/connected app config.
Risks
SF data quality; field-mapping drift.
Exit criteria
Reps verify from SF; underwriters get complete packets; adoption metrics.
Not yet
Predictive ML.

Phase 4 — Underwriting & document automation support (4–6 wk)
Aspect
Detail
Goal
Assemble underwriting-ready packets and support doc workflows.
Features
KYB/underwriting packet automation; document retrieval where available; decision capture tied to deal.
Data sources
SOS docs (~18 states), prior phases.
Backend
Packet assembler; document store integration.
Frontend
Underwriting workspace view.
Security
Stronger retention controls for funded-deal evidence.
Testing
Packet completeness; decision audit.
Deployment
Same.
Risks
Doc coverage variance.
Exit criteria
Underwriting uses packets in real decisions.
Not yet
Auto credit decisions.

Phase 5 — Monitoring, alerts & risk intelligence (ongoing)
Aspect
Detail
Goal
Continuous risk visibility on the active book.
Features
Scheduled re-verify + diffs; alerts (dissolution, new senior UCC); portfolio risk dashboard; selective direct gov connectors; ML scoring once labeled data exists.
Data sources
All; direct SAM/OFAC/state where economical.
Backend
Scheduler, diff engine, alerting, optional ML pipeline.
Frontend
Portfolio risk dashboard; alert inbox.
Security
Least-privilege alerts; model governance.
Testing
Change-detection accuracy; alert precision; ML backtest.
Deployment
Recurring flows + notifications.
Risks
Alert fatigue; model drift.
Exit criteria
Adverse changes caught proactively; measurable risk reduction.
Not yet
Anything not validated by P1–P4 usage.


7. Feature Requirements
Condensed PRD per feature: problem, user story, functional + non-functional requirements, data, UI, backend, edge cases, security, audit, acceptance.
7.1 Company Search
Field
Detail
Problem
Find the right entity fast from messy input.
User story
As a rep, I search a name+state and see ranked candidates with status.
Functional
Exact + trigram fuzzy over companies; optional live vendor search; rank by match score.
Non-functional
p95 < 1.5s for cached search; paginated.
Data
companies, business_registrations.
UI
Search box, filters (state, status), results table, empty state.
Backend
GET /companies?q=&state=; ranking service.
Edge cases
Common names; no results → offer live verify.
Security
Authn; results scoped to role.
Audit
Query logged.
Acceptance
Returns correct entity in top-5 for golden-set queries.

7.2 Company Profile Page
Field
Detail
Problem
One place to see the verified truth + evidence.
User story
As an underwriter, I open a company and see status, identity, agent, officers, UCC, evidence, score.
Functional
Aggregate all linked records; show provenance + timestamps.
Non-functional
Loads < 2s; sections lazy-load.
Data
companies + all child tables + evidence.
UI
Header (name/status/score), tabs/sections, evidence timeline.
Backend
GET /companies/{id}/profile.
Edge cases
Missing sections → “not available for state.”
Security
Field-level access (officers/UCC restricted).
Audit
Sensitive-read logged.
Acceptance
All stored facts visible with source + time.

7.3 Business Registration Lookup
Field
Detail
Problem
Confirm the entity exists and key registration facts.
User story
As a rep, verify returns entity id, type, formation date, status.
Functional
Vendor fetch → parse → store registration; normalize status.
Non-functional
Handles per-state field variance gracefully.
Data
business_registrations, raw_source_events.
UI
Registration section on profile.
Backend
Part of verify_flow.
Edge cases
Multi-state; reinstated entities.
Security
Standard.
Audit
Source event stored.
Acceptance
Correct registration for golden set.

7.4 State Status Verification
Field
Detail
Problem
“Is it active?” must be consistent across 50 states.
User story
As an underwriter, I see a normalized status, not raw state jargon.
Functional
Map each state's raw status to {active,inactive,dissolved,delinquent,unknown}; keep raw too.
Non-functional
Mapping table versioned + tested.
Data
business_registrations.status_raw/normalized.
UI
Status badge + raw on hover.
Backend
Status normalizer module.
Edge cases
Ambiguous raw statuses → unknown + review.
Security
Standard.
Audit
Mapping version recorded on run.
Acceptance
Status-correctness >98% on golden set.

7.5 Registered Agent Display
Field
Detail
Problem
Know who represents the entity.
User story
Show agent name + address where available (~49 states).
Functional
Store/display agent; flag if missing.
Non-functional
—
Data
registered_agents.
UI
Agent card.
Backend
Part of verify.
Edge cases
Agent missing for state.
Security
Agent address = PII-adjacent; access-controlled.
Audit
Stored with source.
Acceptance
Matches source where present.

7.6 Officer/Principal Display (where available)
Field
Detail
Problem
Know who controls the entity; feed screening.
User story
Show officers (~28 states) with titles.
Functional
Store officers; screen each vs OFAC.
Non-functional
Clearly mark “not published by state” vs “none.”
Data
company_officers.
UI
Officers list + screen status.
Backend
Officer parser + OFAC screen.
Edge cases
Thin coverage.
Security
PII — restricted role; retention-limited.
Audit
Sensitive-read logged.
Acceptance
Officers + screen result shown where available.

7.7 UCC / Lien Search (Phase 2)
Field
Detail
Problem
Reveal competing secured creditors — core to secured lending.
User story
As an underwriter, I see liens with secured party, collateral, dates, position.
Functional
Debtor search → parse filings → compute lien_rank; conservative over-return + review.
Non-functional
Never imply “no liens” for unchecked states.
Data
ucc_filings.
UI
UCC section + “not checked” banners.
Backend
UCC connector(s) + position logic.
Edge cases
Name ambiguity; partial coverage.
Security
Sensitive financial data; restricted.
Audit
Query + results + evidence.
Acceptance
UCC precision/recall meets agreed bar on golden set.

7.8 Evidence Timeline
Field
Detail
Problem
Prove what was verified, when, from where.
User story
As compliance, I see immutable, hashed evidence per run.
Functional
List evidence items chronologically; verify hash; link to artifact.
Non-functional
Evidence immutable (WORM).
Data
evidence_items, verification_runs.
UI
Timeline with type, time, source, hash.
Backend
GET /companies/{id}/evidence.
Edge cases
Legacy run without screenshot.
Security
Read-only; access-controlled; logged.
Audit
Every view logged.
Acceptance
Hash verifies; artifact retrievable.

7.9 Confidence Score
Field
Detail
Problem
An explainable, non-random signal of trust.
User story
I see a status + the evidence behind each component.
Functional
Rule-based components (§12); thresholds → status.
Non-functional
Deterministic, reproducible, versioned.
Data
confidence_scores.
UI
Score panel with component breakdown.
Backend
Scoring engine.
Edge cases
Low completeness → insufficient evidence.
Security
Standard.
Audit
Score version + inputs stored.
Acceptance
Same inputs → same score; components traceable to evidence.

7.10 Manual Review Workflow
Field
Detail
Problem
Humans must resolve ambiguity in financial decisions.
User story
As a reviewer, I see candidates + evidence and accept/reject with reason.
Functional
Queue; decision capture; status update; optional SF push.
Non-functional
Optimistic locking; SLA visibility.
Data
review_decisions, verification_runs.
UI
Review queue + decision panel.
Backend
POST /review/{id}/decision.
Edge cases
Concurrent reviewers; no good candidate.
Security
Restricted to reviewer/underwriter roles.
Audit
Decision + reason + before/after (immutable).
Acceptance
Decisions persist and are fully auditable.

7.11 Duplicate Resolution
Field
Detail
Problem
Prevent fragmented/duplicate company records.
User story
As ops, I review duplicate clusters and merge safely.
Functional
Surface clusters; reviewed, history-preserving merge.
Non-functional
No hard delete; reversible audit.
Data
companies, audit_logs.
UI
Duplicate review screen.
Backend
Merge service.
Edge cases
False duplicates.
Security
Restricted.
Audit
Merge logged with source/target.
Acceptance
Merges preserve history; never auto-merge on fuzzy name.

7.12 Salesforce Matching
Field
Detail
Problem
Tie verified truth to the CRM record.
User story
Link a SF lead/account to a verified company.
Functional
ER against verified companies; SF match confidence; review if low.
Non-functional
Idempotent linking by external id.
Data
salesforce_sync_status, companies.
UI
SF match section on profile.
Backend
Matching service.
Edge cases
DBA-only SF record.
Security
SF creds server-side only.
Audit
Match + confidence logged.
Acceptance
Correct link above threshold; review below.

7.13 Salesforce Sync
Field
Detail
Problem
Get verified data into the rep's workflow.
User story
Push legal name, status, score, evidence URL, last-verified to SF.
Functional
Field mapping; idempotent upsert; sync status + errors.
Non-functional
Retry/backoff; rate-limit aware.
Data
salesforce_sync_status.
UI
Sync button + status.
Backend
POST /salesforce/sync.
Edge cases
Picklist mismatch; missing field.
Security
Scoped connected app; least privilege.
Audit
Sync attempts + payload fields.
Acceptance
Fields populate; failures recoverable.

7.14 Source Registry
Field
Detail
Problem
Manage swappable data providers + capabilities.
User story
As admin, enable/disable sources and see capabilities/coverage.
Functional
CRUD-lite on sources; capability + state coverage; health.
Non-functional
Drives connector selection.
Data
source_registry, source_credentials.
UI
Admin source list.
Backend
Registry service.
Edge cases
Source deprecated.
Security
Admin-only; secret refs only.
Audit
Config changes logged.
Acceptance
Selection uses registry; no plaintext keys.

7.15 Data Quality Dashboard
Field
Detail
Problem
Catch silent data degradation.
User story
As ops, I see field-fill rates + anomalies per source/state.
Functional
Compute fill rates; flag sudden drops.
Non-functional
Nightly batch + on-demand.
Data
raw_source_events, business_registrations.
UI
DQ dashboard.
Backend
DQ jobs.
Edge cases
Seasonal variance.
Security
Internal.
Audit
—
Acceptance
Detects an injected coverage drop in test.

7.16 Error Monitoring
Field
Detail
Problem
See and triage failures fast.
User story
As admin, I see connector errors + source health.
Functional
Capture/classify errors; Sentry + error dashboard.
Non-functional
Alert on persistent failures.
Data
error_logs.
UI
Error dashboard.
Backend
Error capture middleware.
Edge cases
Transient vs persistent.
Security
Internal; no secrets in errors.
Audit
—
Acceptance
Failures appear with classification.

7.17 Admin Configuration
Field
Detail
Problem
Operate the system safely.
User story
As admin, manage users, roles, sources, credentials.
Functional
User/role CRUD; credential refs; feature flags.
Non-functional
Separation of duties.
Data
users, roles, source_credentials.
UI
Admin settings.
Backend
Admin endpoints.
Edge cases
Last-admin protection.
Security
Admin-only; MFA; logged.
Audit
All admin actions logged.
Acceptance
RBAC enforced; changes audited.

7.18 Internal Report Generation
Field
Detail
Problem
Defensible, shareable verification artifact.
User story
As underwriter, generate a KYB packet PDF.
Functional
Assemble sections → PDF → store + hash.
Non-functional
Deterministic layout.
Data
generated_reports + all profile data.
UI
Report export screen.
Backend
Report service.
Edge cases
Missing sections labeled.
Security
Access-controlled; logged.
Audit
Report + hash stored.
Acceptance
Packet matches profile; retrievable.


8. Data Source Strategy
Honesty: Most state SOS and UCC systems do NOT offer a clean, uniform public API. Assume vendor-mediated access for SOS/UCC; assume official APIs only for SAM.gov and OFAC.
Source
Provides
API?
Scrape risk
Quality / gaps
Refresh
MVP / Phase
State SOS registries
Entity name/ID/type, status, formation, agent, officers, addresses
Mostly NO uniform API (FACT)
High (ToS, captcha, fragility)
Field coverage varies by state (officers ~28, addr ~35)
Real-time at source
Core / MVP via vendor
UCC filing offices
UCC-1 secured party, collateral, dates
Rare API; some paid portals
High; some state fees
Partial coverage; debtor-name ambiguity
Daily–realtime
High value / Phase 2 via vendor
SAM.gov Entity API
Federal reg, UEI, CAGE, exclusions
YES official REST + bulk (FACT)
Low (official)
Good for gov-registered only
Daily extracts
Phase 2 (gov-contractor leads)
OFAC / sanctions
SDN + consolidated lists
Official free files (FACT)
Low
High; fuzzy-match nuance
Daily/as-updated
MVP (cheap win)
Public business records (court/judgment/bankruptcy)
Adverse signals
PACER (paid) federal; state fragmented
Med–High
Fragmented
Varies
Phase 4–5 via vendor
Commercial enrichment (D&B/Experian/Enigma/ZoomInfo)
Firmographics, revenue est., contacts
YES (paid)
Low (licensed)
Cached, not legal-status truth
Daily–weekly
Phase 2–3 for scoring
Salesforce internal data
Porter's leads/accounts/history
YES (SF API)
Low
Quality varies
Real-time
MVP (matching) / Phase 3 (sync)
Manual uploads/imports
CSV lists
N/A
Low
Human-entry errors
On demand
Phase 2 (bulk)
Future paid KYB APIs (Cobalt/Middesk)
Bundled SOS+UCC+watchlist
YES (paid)
Low (licensed)
~$0.50–$2/entity (reported)
Realtime–daily
MVP data layer (buy)
8.1 Per-source notes & how to validate
SOS (FACT/UNKNOWN): existence/status authoritative; per-field coverage uneven. Validate exact coverage by running the chosen vendor on 50–100 real Porter leads (Phase 0).
UCC (UNKNOWN, critical): coverage and per-state cost vary; debtor matching is noisy. Validate by testing vendor + key states on Porter's actual recent UCC situations before promising Phase 2.
SAM.gov (FACT): official free API, rate-limited (e.g., ~1,000/day registered) + bulk extracts; public data. Validate eligibility/rate limits against Porter volume.
OFAC (FACT): free official lists, frequent updates, easy to ingest; fuzzy matching with thresholds is the only engineering.
IRS/EIN (FACT): no public EIN-verification API; IRS TIN Matching is gated to 1099 filers. Treat supplied EIN as a claim; label “name/TIN consistency,” never “IRS-verified.” Validate Porter's TIN-Matching eligibility with tax/compliance.
Legal/compliance: public data is generally usable but access method matters; vendor licensing shifts ToS burden. Get legal review of scraping policy and any FCRA applicability (factoring can touch owners).

9. System Architecture
9.1 Recommended stack & why
Layer
Choice
Why
API
FastAPI (Python)
Async, pydantic validation, auto OpenAPI; matches team Python skills.
DB
PostgreSQL + SQLAlchemy + Alembic
Relational integrity for entities/evidence; jsonb for raw; migrations versioned.
Orchestration
Prefect
Retries, scheduling, observability for verify/bulk/monitor flows; lighter than Temporal, clearer than raw Celery.
Dashboard (MVP)
Streamlit
Fastest path to an internal, Python-native UI; no separate frontend team; perfect for an internal tool.
Dashboard (later)
React/Next.js
Richer review UX + Salesforce-embedded components when needed (Phase 3).
Evidence store
S3-compatible object store (WORM/object-lock)
Immutable, hashed evidence; cheap; versioned.
Cache/queue
Redis
Result TTL caching (cut vendor cost), rate limiting, lightweight queue.
Secrets
Vault or cloud Secrets Manager
No secrets in code/env; rotation; only refs in DB.
Errors/obs
Sentry + structured JSON logs + metrics
Fast triage; tamper-evident logging.
CI/CD
GitHub Actions + Docker
Lint/type/test/scan gates; reproducible images.
Hosting
Cloud (AWS/GCP/Azure) managed Postgres + container service
Managed backups, scaling; UNKNOWN: Porter's cloud preference — validate.
Streamlit vs React (MVP): Use Streamlit for MVP. It is internal-only, single-team Python, and lets one backend engineer ship a usable dashboard without a separate frontend stack. Move to React in Phase 3 when Salesforce-embedded UX and richer interactions justify the cost.
9.2 Logical architecture
PRESENTATION
  Streamlit dashboard (MVP) -> React + SF Lightning component (later)
        | HTTPS / OIDC SSO
API LAYER  (FastAPI)
  authn/z, RBAC, rate limit, pydantic validation
  /companies /verify /verify/bulk /ucc /evidence /review
  /salesforce/sync /reports /admin/sources /health
        | enqueue
ORCHESTRATION (Prefect)
  verify_flow: resolve -> fetch -> normalize -> screen -> score -> persist -> evidence -> audit
  bulk_flow, monitor_flow (later)
        | calls
SERVICE LAYER
  Connector Framework | Normalization | Entity Resolution | Scoring
  Screening(OFAC) | Evidence | Review | Salesforce | Report | Audit | Admin
        | reads/writes
DATA LAYER
  PostgreSQL (core)   Object store (evidence WORM)   Redis (cache/limits)   Secrets mgr
CROSS-CUTTING: Sentry, structured logs, metrics, backups, staging/prod
9.3 Connector framework (the swappability contract)
class SourceConnector(Protocol):
    name: str
    capabilities: set[str]      # {"entity","status","officers","ucc","screenshot","ofac"}
    states: set[str]
    def search(self, q: EntityQuery) -> list[RawResult]: ...
    def fetch(self, ref: SourceRef) -> RawRecord: ...
    def capture_evidence(self, ref: SourceRef) -> EvidenceBlob | None: ...
    def health(self) -> SourceHealth: ...
 
# registry-driven selection by state + capability + health + cost
conn = registry.select(state="TX", capability="status")
9.4 Component responsibilities (brief)
Raw ingestion: persist every source response verbatim (raw_source_events) before parsing — enables reprocessing.
Normalization: map raw → canonical fields + status enum; versioned mappings.
Entity resolution: conservative matching (§11); below threshold → review.
Scoring: rule-based, explainable, versioned (§12).
Evidence: immutable artifact + SHA-256; never overwritten.
Review: queue + decision capture; immutable decisions.
Salesforce: idempotent upsert by external id; sync status tracked.
Report: KYB packet PDF + hash.
Audit: append-only, on all mutations + sensitive reads.
Admin: source registry, users/roles, credential refs.
9.5 Environments
Separate staging and production: separate DBs, secrets, vendor test/live keys; IaC; no prod data in staging; daily encrypted backups + PITR; tested restores.

10. Database Design
Principles: canonical company spine; append-only verification/evidence/audit; explicit source provenance on every fact; raw-before-normalized; conservative dedupe; no destructive overwrites.
10.1 Table catalog
Table
Purpose
Key columns / FKs
companies
Canonical resolved entity
id PK, canonical_legal_name, normalized_name, home_state, status_normalized, entity_age_days, dedupe_key UNIQUE
company_identifiers
All IDs (1:N)
id PK, company_id FK, id_type, id_value, source_id FK; UNIQUE(id_type,id_value)
business_registrations
Per-state registration
id PK, company_id FK, state, state_entity_id, entity_type, formation_date, status_raw, status_normalized, source_id FK; UNIQUE(state,state_entity_id)
registered_agents
Agent per registration
id PK, registration_id FK, agent_name, agent_address, source_id FK
company_officers
Officers (1:N)
id PK, company_id FK, name, title, address, screened_ofac, source_id FK
ucc_filings
Lien records
id PK, company_id FK, state, filing_number, secured_party, collateral_desc, filing_date, lapse_date, status, lien_rank, match_confidence; UNIQUE(state,filing_number)
evidence_items
Immutable proof
id PK, verification_run_id FK, type, storage_uri, sha256, captured_at (NO update/delete)
raw_source_events
Verbatim source responses
id PK, verification_run_id FK, source_id FK, request, response_blob jsonb, response_code, latency_ms, raw_hash, cost_credits, occurred_at
verification_runs
One verification execution
id PK, company_id FK, requested_by FK, trigger, match_confidence, risk_score, status, score_version, started_at, finished_at
source_registry
Connectors/capabilities
id PK, name, capabilities[], states[], cost_per_lookup, health_status, enabled
source_credentials
Secret refs only
id PK, source_id FK, secret_ref, env, rotated_at (NO plaintext)
confidence_scores
Score breakdown
id PK, verification_run_id FK, component, value, weight, explanation
review_decisions
Human decisions
id PK, verification_run_id FK, reviewer_id FK, decision, reason, candidate_chosen, decided_at (immutable)
salesforce_sync_status
SF sync state
id PK, company_id FK, sf_object, sf_record_id, last_synced_at, sync_status, error; UNIQUE(sf_object,sf_record_id)
users
Internal users
id PK, email UNIQUE, sso_sub, role_id FK, active
roles
RBAC roles
id PK, name UNIQUE, permissions[]
audit_logs
Append-only audit
id PK bigserial, actor, action, entity_type, entity_id, before jsonb, after jsonb, request_id, occurred_at
error_logs
Operational errors
id PK, source_id FK, run_id FK, error_type, message, occurred_at
generated_reports
KYB packets
id PK, company_id FK, storage_uri, sha256, generated_by FK, generated_at
10.2 Representative DDL
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
 
CREATE TABLE companies (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  canonical_legal_name text NOT NULL,
  normalized_name text NOT NULL,
  home_state char(2),
  status_normalized text CHECK (status_normalized IN
    ('active','inactive','dissolved','delinquent','unknown')),
  entity_age_days int,
  dedupe_key text UNIQUE,                 -- home_state|normalized_name
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_companies_name_trgm ON companies USING gin (normalized_name gin_trgm_ops);
 
CREATE TABLE raw_source_events (             -- RAW, immutable, enables reprocessing
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  verification_run_id uuid NOT NULL REFERENCES verification_runs(id),
  source_id uuid NOT NULL REFERENCES source_registry(id),
  request jsonb, response_blob jsonb,
  response_code int, latency_ms int,
  raw_hash char(64) NOT NULL,
  cost_credits numeric(8,3) DEFAULT 0,
  occurred_at timestamptz NOT NULL DEFAULT now()
);
 
CREATE TABLE evidence_items (                -- WORM: revoke UPDATE/DELETE via role
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  verification_run_id uuid NOT NULL REFERENCES verification_runs(id),
  type text CHECK (type IN ('screenshot','raw_json','pdf')),
  storage_uri text NOT NULL,
  sha256 char(64) NOT NULL,
  captured_at timestamptz NOT NULL DEFAULT now()
);
 
CREATE TABLE ucc_filings (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id uuid NOT NULL REFERENCES companies(id),
  state char(2) NOT NULL, filing_number text NOT NULL,
  secured_party text, collateral_desc text,
  filing_date date, lapse_date date, status text,
  lien_rank int, match_confidence numeric(4,3),
  source_id uuid REFERENCES source_registry(id),
  captured_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (state, filing_number)
);
 
CREATE TABLE audit_logs (                    -- append-only
  id bigserial PRIMARY KEY, actor text NOT NULL, action text NOT NULL,
  entity_type text, entity_id text, before jsonb, after jsonb,
  request_id text, occurred_at timestamptz NOT NULL DEFAULT now()
);
10.3 Data-handling rules
Raw vs normalized: store the verbatim response in raw_source_events first; normalization writes typed fields referencing the raw event. Re-parsing old raw enables reprocessing without re-paying the vendor.
Evidence preservation: evidence_items in WORM storage; SHA-256 stored; new runs add new evidence, never overwrite.
Prevent accidental overwrite: append-only tables (verification_runs, evidence_items, raw_source_events, audit_logs, review_decisions) — DB role lacks UPDATE/DELETE; facts carry captured_at + source_id.
Source versioning: score_version + normalization-mapping version recorded per run; source_registry tracks connector version.
Deduplication: companies.dedupe_key + unique (state,state_entity_id); merges are reviewed and history-preserving.
PII minimization: no raw EIN (store salted hash if needed); officer addresses access-controlled + retention-limited.
Retention/audit: evidence for funded deals retained per policy (e.g., 7 yrs — confirm); transient lead data purged on schedule; all sensitive reads/writes audited.

11. Entity Resolution Strategy
Principle: In financial services a false match is worse than a miss. Bias the system toward “ask a human” over “guess.” Fuzzy matching may SURFACE candidates for review but must never AUTO-MERGE.
11.1 Signals (strong → weak)
Signal
Strength
Use
State reg number + state
Very strong
Auto key when exact.
UEI (SAM.gov)
Strong
Auto for gov-registered.
Exact legal name + state + address
Strong
Auto-accept with corroboration.
EIN (claimed)
Medium (unverifiable)
Supporting only; never sole basis; store hashed.
Normalized name + state
Medium
Needs corroboration; names collide.
Registered agent
Medium (corroborating)
Support only — agents serve many entities.
Domain / website
Medium
Corroboration.
Phone
Weak
Corroboration only.
DBA / trade name
Weak–Medium
Map DBA→legal; never use as proof of identity.
11.2 Normalization before comparison
Lowercase; strip punctuation; collapse whitespace.
Canonicalize suffixes (LLC/L.L.C./Inc/Incorporated/Corp/Co/Ltd/LP/LLP).
Standardize addresses (USPS); split unit/suite.
Synonym map (“&”↔“and”, “St”↔“Street”).
11.3 Algorithm & thresholds
def resolve(q) -> Resolution:
    cands = search_sources(q)               # over-fetch
    for c in cands: c.score = weighted_match(q, c)
    cands.sort(key=lambda c: -c.score)
    top = cands[0] if cands else None
    if top and top.score >= 0.92 and unambiguous(cands):
        return Resolution("AUTO_ACCEPT", top, components(top))
    if top and 0.75 <= top.score < 0.92:
        return Resolution("NEEDS_REVIEW", top, cands[:5])
    if multiple_within(cands, 0.05):
        return Resolution("NEEDS_REVIEW", None, cands[:5])
    return Resolution("NO_MATCH", None)     # never force a match
 
def weighted_match(q, c):
    s  = 0.45*exact(q.reg_id, c.reg_id)
    s += 0.25*name_sim(q.norm_name, c.norm_name)   # token + trigram
    s += 0.15*state_eq(q.state, c.state)
    s += 0.10*addr_sim(q.address, c.address)
    s += 0.05*agent_sim(q.agent, c.agent)
    return min(s, 1.0)
Outcome
Rule
Auto-accept
score ≥ 0.92 AND no other candidate within 0.05 AND status retrievable.
Mandatory review
0.75–0.92; OR any UCC debtor match used for underwriting; OR multiple close candidates; OR status-changing result.
No match
< 0.75 → “insufficient evidence / needs input” (never a forced guess).
11.4 Error handling
False positive (wrong entity): high threshold + ambiguity check + review; store score components for audit.
False negative (missed match/lien): over-fetch, trigram fuzzy, multi-source fallback, explicit “source not checked” states so a gap is never read as “clear.”
Duplicate prevention: dedupe_key + reviewed merges; never auto-merge on fuzzy name alone; all merges audited and reversible.

12. Scoring and Confidence Model
Not AI guessing: Scores are deterministic, rule-based, versioned, and traceable to evidence. The same inputs always produce the same score. ML is deferred until labeled outcomes exist (Phase 5).
12.1 Component scores
Component
Inputs
Logic / thresholds
Evidence required
Review trigger
Business existence
Found in SOS
Found=high; not found=insufficient
SOS record + screenshot
Not found
Entity match
ER score (§11)
≥0.92 high; 0.75–0.92 medium
Match components
<0.92
Registration status
normalized status
active=high; delinquent=medium; dissolved=fail
Status field + raw
Unknown status
Data freshness
captured_at age
<30d full; 30–90d partial; >90d stale
Timestamp
Stale on key decision
UCC/lien risk (P2)
#liens, position, recency
clean=low; senior liens=high risk
UCC filings
Any senior lien
Source reliability
source health/history
primary>secondary
Source registry
Degraded source
Salesforce match
SF match conf.
≥0.92 auto-link
Match components
<0.92
Manual review status
reviewer decision
overrides system status
Decision record
—
12.2 Overall verification status (derived)
Status
Meaning
Condition (illustrative)
Verified
Real, active, well-matched, fresh evidence
existence high + match ≥0.92 + status active + fresh
Likely Match
Probably right, minor gaps
match 0.85–0.92 OR slightly stale
Needs Review
Human must decide
match 0.75–0.92, ambiguity, or status-change
Insufficient Evidence
Not enough data to judge
not found OR key fields missing for state
Inactive / Not Eligible
Dissolved/delinquent
status dissolved/delinquent
Risk Flag
Adverse signal present
OFAC hit, senior UCC, or anomaly
12.3 Limitations (stated honestly)
Scores reflect data availability, which varies by state — “insufficient evidence” is a valid, common outcome, not a failure.
EIN cannot be authoritatively verified; it never drives a high score alone.
UCC absence in an uncovered state is NOT “no liens” — the model encodes “not checked.”
Rule weights are initial assumptions; calibrate against analyst judgment on the golden set and adjust with versioning.

13. UI / Dashboard Plan
Screens for the Streamlit MVP (React later). Each: purpose, components, actions, data, filters, empty state, error state, permissions.
13.1 Login
Aspect
Detail
Purpose
Authenticate via Porter SSO.
Components
SSO button, error banner.
Actions
Sign in (OIDC/SAML) + MFA.
Data
None client-side.
Filters
—
Empty state
—
Error state
Auth failed message; no detail leak.
Permissions
Public route; everything else gated.

13.2 Home Dashboard
Aspect
Detail
Purpose
Snapshot + entry point.
Components
KPI cards (verifications today, auto-verify %, review queue size, source health), recent activity, search bar.
Actions
Search, jump to review queue.
Data
Aggregates from runs.
Filters
Date range.
Empty state
“No verifications yet — run your first search.”
Error state
Metric load error → retry.
Permissions
All roles (aggregate scoped).

13.3 Company Search
Aspect
Detail
Purpose
Find an entity.
Components
Search box, state filter, results table (name, status, score).
Actions
Search, open profile, run live verify.
Data
companies + registrations.
Filters
State, status.
Empty state
“No matches — run a live verification.”
Error state
Source error banner.
Permissions
All authorized.

13.4 Company Profile
Aspect
Detail
Purpose
The verified truth in one place.
Components
Header (name/status/score), Identity, Agent, Officers, UCC, SF match, Evidence timeline, Score panel, Review panel.
Actions
Run verify, export report, push to SF, open review.
Data
All linked tables + evidence.
Filters
—
Empty state
Section-level “not available for state X.”
Error state
Per-section error without breaking page.
Permissions
Officers/UCC restricted by role.

13.5 Evidence Timeline
Aspect
Detail
Purpose
Point-in-time proof.
Components
Chronological list: type, time, source URL, hash, thumbnail.
Actions
Open artifact, verify hash.
Data
evidence_items.
Filters
Type.
Empty state
“No evidence yet.”
Error state
Storage error message.
Permissions
Read; logged as sensitive-read.

13.6 UCC / Lien Section (P2)
Aspect
Detail
Purpose
Show liens + position.
Components
Lien table, position summary, “not checked” banners per uncovered state.
Actions
Open evidence, send to review.
Data
ucc_filings.
Filters
Status, secured party.
Empty state
Distinguish “no liens found” vs “not checked.”
Error state
Coverage/error banner.
Permissions
Underwriter+.

13.7 Salesforce Match
Aspect
Detail
Purpose
Link CRM to verified company.
Components
Matched SF record, confidence, sync status.
Actions
Confirm match, push sync.
Data
salesforce_sync_status.
Filters
—
Empty state
“No SF link — search to match.”
Error state
Sync error + retry.
Permissions
Rep+.

13.8 Confidence Score Panel
Aspect
Detail
Purpose
Explainable trust.
Components
Overall status + component bars + evidence links.
Actions
Drill into component.
Data
confidence_scores.
Filters
—
Empty state
“Insufficient evidence.”
Error state
—
Permissions
All authorized.

13.9 Review Decision Panel / Queue
Aspect
Detail
Purpose
Resolve ambiguity.
Components
Queue list, candidate compare, decision buttons, reason field.
Actions
Accept/reject/needs-info with reason.
Data
verification_runs, review_decisions.
Filters
Status, age.
Empty state
“Queue clear.”
Error state
Lock conflict message.
Permissions
Reviewer/underwriter.

13.10 Source Health Dashboard
Aspect
Detail
Purpose
See connector health.
Components
Source list, status, latency, success rate.
Actions
Disable/enable (admin).
Data
source_registry, source_events.
Filters
Source.
Empty state
—
Error state
—
Permissions
Admin.

13.11 Error Dashboard
Aspect
Detail
Purpose
Triage failures.
Components
Error list, classification, counts.
Actions
Filter, link to Sentry.
Data
error_logs.
Filters
Type, source, date.
Empty state
“No errors.”
Error state
—
Permissions
Admin.

13.12 Admin Settings
Aspect
Detail
Purpose
Operate safely.
Components
Users/roles, sources, credential refs, flags.
Actions
CRUD users/roles/sources.
Data
users, roles, source_credentials.
Filters
—
Empty state
—
Error state
Validation errors.
Permissions
Admin + MFA; logged.

13.13 Report Export
Aspect
Detail
Purpose
Generate KYB packet.
Components
Section preview, generate button, download.
Actions
Generate PDF, download.
Data
generated_reports + profile.
Filters
—
Empty state
—
Error state
Render error + retry.
Permissions
Underwriter/compliance; logged.


14. API Design
REST/JSON, FastAPI, OIDC bearer tokens, RBAC per endpoint. All mutating + sensitive-read endpoints write audit_logs with actor + request_id. Errors use a consistent shape: {error:{code,message,request_id}}.
POST /companies/search
Field
Detail
Request
{ query, state?, limit?, offset? }
Response
{ results:[{company_id,name,status,match_score}], total }
Auth
Any authenticated role.
Errors
400 invalid; 401; 429 rate limit.
Audit
Query terms + actor.

POST /verify
Field
Detail
Request
{ name, state?, address?, ein_claim?, website?, trigger }
Response
{ verification_run_id, status, confidence, company_id?, needs_review }
Auth
Rep+.
Errors
400; 422 unresolved; 502 source_unavailable (no charge); 429.
Audit
Inputs, sources hit, result, evidence hashes.

GET /companies/{id}/profile
Field
Detail
Request
path id.
Response
{ company, registrations, agent, officers, ucc, sf_match, scores }
Auth
Role-scoped (officers/ucc filtered).
Errors
404; 403.
Audit
Sensitive-read if officers/ucc included.

GET /companies/{id}/evidence
Field
Detail
Request
path id.
Response
{ items:[{type,storage_uri,sha256,captured_at}] }
Auth
Underwriter/compliance/admin.
Errors
404;403.
Audit
Every access logged (sensitive-read).

POST /companies/{id}/ucc  (Phase 2)
Field
Detail
Request
{ refresh? }
Response
{ filings:[...], lien_position, states_checked, states_not_checked }
Auth
Underwriter+.
Errors
404;403;502 partial-coverage.
Audit
Query + results + evidence.

POST /review/{run_id}/decision
Field
Detail
Request
{ decision: approved|rejected|needs_info, reason, candidate_chosen? }
Response
{ run_id, new_status }
Auth
Reviewer/underwriter.
Errors
404;409 lock conflict;422 missing reason.
Audit
Decision+reason+before/after (immutable).

POST /salesforce/sync
Field
Detail
Request
{ company_id, sf_object, sf_record_id, fields[] }
Response
{ sync_status, synced_fields, error? }
Auth
Rep+ (SF creds server-side).
Errors
424 SF error; 409 conflict; 429.
Audit
Attempt + fields + result.

POST /reports/{company_id}
Field
Detail
Request
{ sections? }
Response
{ report_id, storage_uri, sha256 }
Auth
Underwriter/compliance.
Errors
404;500 render.
Audit
Report + hash + actor.

GET /admin/sources/health
Field
Detail
Request
—
Response
{ sources:[{name,status,latency_ms,success_rate}] }
Auth
Admin.
Errors
403.
Audit
—

PUT /admin/sources/{id}
Field
Detail
Request
{ enabled?, cost_per_lookup?, states?, secret_ref? }
Response
{ source }
Auth
Admin + MFA.
Errors
403;400.
Audit
Config change before/after.


15. Security and Compliance Plan
Control
Design
Authentication
Porter SSO (OIDC/SAML) + enforced MFA; no local staff passwords; short-lived service tokens.
Authorization / RBAC
Roles (rep, manager, underwriter, ops, admin, auditor); enforced at API + data layer; deny by default; field-level restrictions on officers/UCC.
Secrets management
Vault/Secrets Manager; DB stores only secret refs; automated rotation; no secrets in repo/CI logs.
API key storage
Vendor + SF keys server-side only; never sent to dashboard/SF client; per-environment scoping.
Encryption in transit
TLS 1.2+ for all client, vendor, DB, and internal traffic.
Encryption at rest
DB + object store AES-256 via managed KMS; evidence bucket WORM/object-lock.
Audit logs
Append-only audit_logs + shipped to write-once store; cover auth, sensitive reads, decisions, config, syncs.
PII handling
Minimize (no raw EIN; hash); officer/agent addresses restricted + retention-limited; PII excluded from logs.
Sensitive business data
UCC/lien + scores access-controlled; least-privilege exports.
Salesforce credentials
Scoped connected app, OAuth, least privilege, server-side only, rotated.
Least privilege
Per-role + per-environment; prod DB write limited; service accounts scoped.
Admin access
Admin actions require MFA and are fully logged; separation of duties (admin ≠ decisioning).
Data retention
Policy-driven: funded-deal evidence long-retained (e.g., 7 yrs — confirm); transient lead data purged on schedule.
Backup & restore
Daily encrypted backups + PITR; cross-region evidence copy; quarterly restore drills.
Incident response
Runbook: detect→contain→eradicate→recover→post-mortem; severities; on-call; breach-notice path.
Monitoring
Sentry, metrics + alerts (latency, failure rate, source health, cost spikes, anomalous access).
Rate limiting
Per-user/endpoint/vendor; circuit breakers on failing sources; bulk backpressure.
Vendor risk
Security review + DPA per vendor; verify SOC 2; monitor uptime/breach notices; design for swap.
ToS review (public data)
Legal review of each source's terms; rent via vendor to shift ToS burden; no aggressive prod scraping.
SOC 2-style controls
Change mgmt, code review, separation of duties, least privilege, logging/monitoring, IR, vendor mgmt.
Secure SDLC
PR review, branch protection, secret scanning, SAST/dependency scanning, no direct prod pushes.
Dependency scanning
Automated in CI; block on critical CVEs; periodic upgrades.
Logging policy
Structured JSON, request IDs, no secrets/full PII, centralized, retention-defined, tamper-evident.
Production access
Just-in-time, MFA, logged; no standing prod DB access; break-glass procedure documented.
Legal honesty: Government registry data is public, but a site's terms can restrict automated access; CFAA/contract exposure exists for circumvention. Rent data through licensed vendors, restrict Playwright to capturing records Porter is entitled to view at human scale, and get legal sign-off on FCRA applicability (factoring can touch business owners).

16. Reliability and Operations Plan
Area
Design
Scheduled jobs
Prefect schedules: nightly DQ checks, OFAC list refresh, (P2) bulk re-verify, (P5) monitoring diffs.
Retry / backoff
Exponential backoff with jitter per source; max attempts; dead-letter for persistent failures.
Rate limits
Token-bucket per source respecting vendor quotas; global + per-user caps.
Source downtime
Mark source_unavailable; no credit/charge; queue + callback retry; surface on health dashboard.
Partial failure
Row-level isolation in bulk; per-section isolation in profile; partial results clearly labeled.
Quarantine
Bad/anomalous data flagged + held out of canonical until reviewed (DQ rules).
Idempotency
Verify keyed by (input hash + day); SF upserts by external id; safe re-runs.
Reprocessing
Re-parse stored raw_source_events without re-paying vendor; versioned normalization.
Alerting
Sentry + metric alerts to Slack/email; severities; on-call rotation (small team: primary+backup).
Observability
Metrics (latency, success, cost/lookup, queue depth), structured logs, traces on verify_flow.
Health checks
/health (liveness) + /ready (DB, cache, secrets, vendor ping).
Backups
Daily Postgres snapshot + PITR; evidence cross-region; documented RPO/RTO.
Restore testing
Quarterly restore drill into staging; verify integrity + WORM immutability.
Staging
Mirrors prod config with test vendor keys; no prod data.
Production deploy
Containerized, GitHub Actions, migrations gated, blue/green or rolling; rollback ready.
Runbook
Per incident type: source down, vendor outage, SF sync failure, bad-data quarantine, restore.

17. Testing Plan
Test type
Covers
Unit
Normalization, suffix handling, status mapping, scoring math, address parsing.
Integration
verify_flow end-to-end vs vendor sandbox; DB writes; evidence storage.
DB migration
Alembic up/down on a seeded DB; no data loss; constraints hold.
Connector
Contract tests every connector must pass (schema, errors, health); recorded fixtures to detect upstream drift.
Entity resolution
Labeled golden set; track precision, recall, false-match rate; regression on threshold changes.
Scoring
Deterministic outputs for fixed inputs; threshold boundary cases; version pinning.
API
Endpoint contract + auth + error-shape tests.
UI
Smoke tests of key Streamlit flows (search→profile→review→export).
Permission
Each role limited to allowed actions; auditor read-only; field-level PII enforced.
Security
Authz tests, secret scanning, dependency/SAST scans, pre-go-live pen test.
Source failure
4xx/5xx, timeout, malformed response → graceful review fallback, no charge.
Salesforce sync
Idempotent upsert, conflict, partial failure, field-mapping correctness (SF sandbox).
Backup/restore
Restore drill verifies integrity + immutability.
Data quality
Fill-rate checks; injected coverage-drop detected.
Regression
Golden outputs for fixed company set; fail build on unexpected diffs.
17.1 Manual QA checklist (pre-MVP-ship)
20 known-good entities across states → correct status/IDs.
10 dissolved/delinquent → flagged inactive/not eligible.
5 multi-state entities → correct home-state resolution.
5 ambiguous names → land in review, not auto-accept.
3 nonexistent businesses → insufficient evidence, no forced result.
Evidence screenshot + hash stored and retrievable; hash verifies.
Salesforce export populates fields correctly.
Audit log captures actor/action for each run/decision/sensitive read.
OFAC test name → risk flag raised.
17.2 Test data plan
Golden set ~200 entities (active, dissolved, multi-state, ambiguous, gov-contractor, OFAC test names) with human-verified truth.
Use vendor test mode + recorded fixtures so tests don't burn credits or depend on live sites.
Porter's real recent leads/deals = the coverage test that actually matters (Phase 0).
17.3 Acceptance criteria to ship MVP
>70% auto-verify; false-match <1%; status-correctness >98% on golden set.
All evidence immutable + hashed; full audit trail present.
Permission tests pass for every role; secrets never exposed.
Connector swappable (second stub passes contract tests).
Restore drill succeeds; staging/prod separated.

18. Development Plan
Engineer-ready steps in build order. Each: goal, modules, build, tests, verify, definition of done (DoD), dependencies, risk.
Step 1 — Repository setup
Field
Detail
Goal
Monorepo + CI skeleton.
Modules
/api /workers /connectors /dashboard /db /infra
Build
Repo, ruff+mypy, pytest, pre-commit, GitHub Actions, Dockerfiles.
Tests
CI runs lint/type/test on PR.
Verify
Green pipeline on empty app.
DoD
Protected main; CI gates.
Deps
None.
Risk
Low.

Step 2 — Environment setup
Field
Detail
Goal
Local + staging config.
Modules
/infra, docker-compose.
Build
Postgres, Redis, app containers; .env.sample; secrets via manager (refs).
Tests
Compose up healthy.
Verify
/health green locally.
DoD
One-command local boot.
Deps
1.
Risk
Low.

Step 3 — Database schema
Field
Detail
Goal
Core tables.
Modules
/db/models (SQLAlchemy).
Build
All §10 tables; constraints; indexes; append-only roles.
Tests
Model + constraint tests.
Verify
Schema reflects design.
DoD
Models reviewed.
Deps
2.
Risk
Med (get it right early).

Step 4 — Migrations
Field
Detail
Goal
Versioned schema.
Modules
/db/alembic.
Build
Initial migration; up/down.
Tests
Migration up/down on seeded DB.
Verify
Round-trip no data loss.
DoD
Migration in CI.
Deps
3.
Risk
Med.

Step 5 — Source registry
Field
Detail
Goal
Manage sources/credentials.
Modules
/connectors/registry, admin endpoints.
Build
source_registry + source_credentials (refs); selection logic.
Tests
Selection by state/capability/health.
Verify
Returns correct connector.
DoD
No plaintext secrets.
Deps
3,4.
Risk
Low.

Step 6 — First connector (vendor + OFAC)
Field
Detail
Goal
Real data in.
Modules
/connectors/vendor, /connectors/ofac.
Build
Implement SourceConnector for chosen vendor (test mode) + OFAC ingest.
Tests
Contract + fixture tests; OFAC match test.
Verify
Live test-mode lookup returns record.
DoD
Passes contract tests.
Deps
5.
Risk
Med (vendor quirks).

Step 7 — Raw event storage
Field
Detail
Goal
Persist verbatim responses.
Modules
/api ingestion, raw_source_events.
Build
Store request/response + hash before parsing.
Tests
Raw persisted + hashed.
Verify
Reprocess from raw works.
DoD
Raw immutable.
Deps
6.
Risk
Low.

Step 8 — Normalization
Field
Detail
Goal
Raw → canonical.
Modules
/api/normalize, status mapper.
Build
Field + status normalization; versioned mappings.
Tests
Status-mapping unit tests per state sample.
Verify
>98% on golden subset.
DoD
Mapping versioned.
Deps
7.
Risk
Med.

Step 9 — Company table & identifiers
Field
Detail
Goal
Canonical spine.
Modules
companies, company_identifiers.
Build
Upsert canonical company; dedupe_key.
Tests
Dedupe + identifier uniqueness.
Verify
No accidental dupes.
DoD
Dedupe enforced.
Deps
8.
Risk
Med.

Step 10 — Evidence table & store
Field
Detail
Goal
Immutable proof.
Modules
evidence_items, object store.
Build
Capture screenshot/raw + SHA-256 to WORM.
Tests
Hash verify; no overwrite.
Verify
Artifact retrievable.
DoD
WORM enforced.
Deps
7.
Risk
Med.

Step 11 — Entity resolution
Field
Detail
Goal
Safe matching.
Modules
/api/resolve.
Build
Normalization + weighted match + thresholds + review routing.
Tests
Golden-set precision/recall; false-match <1%.
Verify
Ambiguous → review.
DoD
Meets accuracy bar.
Deps
9.
Risk
High.

Step 12 — Verification run
Field
Detail
Goal
End-to-end flow.
Modules
/workers/verify_flow (Prefect).
Build
resolve→fetch→normalize→OFAC→score→persist→evidence→audit.
Tests
Integration vs sandbox; failure paths.
Verify
Run produces full record.
DoD
Idempotent + audited.
Deps
6–11.
Risk
High.

Step 13 — Confidence score
Field
Detail
Goal
Explainable status.
Modules
/api/scoring.
Build
Component scores + status derivation; versioned.
Tests
Deterministic; boundary cases.
Verify
Components trace to evidence.
DoD
Reproducible.
Deps
12.
Risk
Med.

Step 14 — Review workflow
Field
Detail
Goal
Human resolution.
Modules
/api/review, review_decisions.
Build
Queue + decision capture + status update.
Tests
Permission + immutability + lock.
Verify
Decisions audited.
DoD
Immutable decisions.
Deps
12.
Risk
Med.

Step 15 — Dashboard MVP
Field
Detail
Goal
Usable UI.
Modules
/dashboard (Streamlit).
Build
Login, Home, Search, Profile+Evidence, Review, Admin, Error/Health.
Tests
Smoke flows.
Verify
Pilot user completes verify→review→export.
DoD
Core flows work.
Deps
12–14.
Risk
Med.

Step 16 — Reports
Field
Detail
Goal
KYB packet PDF.
Modules
/api/reports.
Build
Assemble + render + store + hash.
Tests
Packet matches profile.
Verify
Retrievable + hashed.
DoD
Deterministic packet.
Deps
12.
Risk
Low–Med.

Step 17 — Salesforce matching + export
Field
Detail
Goal
CRM linkage + manual export.
Modules
/api/salesforce.
Build
ER vs verified companies; manual push/CSV export; sync status.
Tests
Sandbox sync; idempotency.
Verify
Fields populate.
DoD
Recoverable failures.
Deps
11,12.
Risk
Med.

Step 18 — Logs / monitoring
Field
Detail
Goal
Operability.
Modules
logging, Sentry, error_logs.
Build
Structured logs, Sentry, error dashboard, metrics, /ready.
Tests
Error capture; alert fires.
Verify
Failures visible.
DoD
Alerts wired.
Deps
12.
Risk
Low.

Step 19 — Security hardening
Field
Detail
Goal
Production security.
Modules
authn/z, rate limit, scans.
Build
SSO/MFA, RBAC, rate limits, secret/dep scans, JIT prod access.
Tests
Permission + security tests; scans clean.
Verify
Pen test pre-launch.
DoD
Security review passed.
Deps
all.
Risk
High.

Step 20 — Staging deployment
Field
Detail
Goal
Prod-like env.
Modules
/infra.
Build
Deploy to staging; migrations; smoke.
Tests
Full regression in staging.
Verify
Golden-set run passes.
DoD
Staging stable.
Deps
19.
Risk
Med.

Step 21 — Production release
Field
Detail
Goal
Ship MVP.
Modules
CI/CD, runbook.
Build
Prod deploy, backups, monitoring, access control, release checklist.
Tests
Post-release validation.
Verify
Pilot live; metrics tracked.
DoD
§5.4 exit criteria met.
Deps
20.
Risk
Med.


19. Deployment Plan
Aspect
Plan
Local development
docker-compose (app, Postgres, Redis); .env.sample; vendor test keys; seed script.
Staging
Cloud, prod-like, test vendor/SF keys, no prod data; auto-deploy on main.
Production
Cloud container service + managed Postgres + object store; manual-approval deploy.
Environment variables
Non-secret config via env; secrets via manager (only refs in app).
Secrets
Vault/Secrets Manager; rotation; never in repo/CI logs.
Database migrations
Alembic; gated step in pipeline; backward-compatible; run before app switch.
Docker
Multi-stage images; pinned base; scanned in CI.
CI/CD
GitHub Actions: lint→type→test→scan→build→deploy(staging)→manual approve→prod.
Rollback
Versioned images; one-click previous image; migrations designed reversible/backward-compatible.
Backup
Daily snapshot + PITR; evidence cross-region; pre-deploy backup.
Monitoring
Sentry + metrics dashboards + alerts active before prod traffic.
Release checklist
Migrations reviewed, backup taken, secrets present, smoke tests green, on-call assigned, rollback ready.
Post-release validation
Run golden-set smoke in prod; verify evidence + audit + SF export; watch error rate 24h.
Access control setup
SSO groups → roles; JIT prod access; admin MFA; least privilege verified.

20. Build vs Buy / Vendor Strategy
Option
Cost
Time
Risk
Data quality
Control
Maintenance
Long-term
Verdict
Build everything
High
6–12+ mo
High (legal/maint)
Variable
Total
Heavy
High if survived
No — don't start here
Buy Cobalt/Middesk only
$/lookup
Days
Low tech
High (live)
Low
Vendor's
Low (no owned IP)
Good start, not destination
Hybrid: buy data, build platform
Medium
8–12 wk MVP
Low–Med
High
High
Medium
High
RECOMMENDED
Vendor first + build workflow around
Medium
Immediate
Low
High
Growing
Medium
High
Recommended bridge
Outsource enrichment, build only workflow
Medium
Weeks
Low
Good
High
Low–Med
High
Yes for scoring data
Build connectors gradually
Incremental
Ongoing
Med
Variable
High
Growing
High
Yes, selectively post-MVP
Recommendation: Hybrid in three moves: (1) BUY a real-time SOS/KYB vendor (bake-off Cobalt vs Middesk on Porter's real leads) as the MVP data layer; (2) BUILD Porter's owned platform around it (connectors, ER, scoring, evidence/audit, Salesforce, review); (3) selectively INSOURCE free/official sources (SAM.gov, OFAC) and high-volume state connectors later to cut cost. Rent the commodity, own the differentiator.

21. Cost and Resource Estimate
Honesty: Dollar figures below are ASSUMPTIONS/ranges for planning, not quotes. Vendor pricing, Porter volume, and cloud choice are UNKNOWN until validated (see §8, §23).
21.1 Team
Role
MVP need
Notes
Backend/data engineer
1–2 (lead + 1)
Core build; Python/FastAPI/Postgres/Prefect.
Product/PM (part-time)
0.5
Scope control, Phase 0 validation, stakeholder mgmt.
Security review (part-time/shared)
0.25
Pre-launch review + controls sign-off.
Salesforce admin/dev (Phase 3)
0.5
Schema mapping (Phase 0), integration (Phase 3).
QA (can be shared)
0.25–0.5
Golden set, regression, manual QA.
21.2 Timeline
Milestone
Estimate (ASSUMPTION)
Phase 0 (discovery/validation)
1–2 weeks
Phase 1 (MVP ship)
4–6 weeks after Phase 0 (total ~8–12 wk with 1–2 eng)
Phase 2 (UCC + scoring)
4–8 weeks
Phase 3 (Salesforce integration)
4–6 weeks
Phase 4–5
ongoing
21.3 Run costs (ranges to validate)
Cost
Range (ASSUMPTION)
Validate by
Vendor lookups
~$0.50–$2.00/lookup (reported); volume tiers
Direct quote at Porter's monthly volume
UCC lookups
Vendor + possible per-state fees
Phase 2 vendor + state research
Cloud infra (MVP)
Low–moderate (managed Postgres + containers + object store)
Pick cloud; size to volume
Enrichment (Phase 2–3)
Subscription/usage ($$$)
Only if scoring needs it
SAM.gov / OFAC
Free (rate-limited)
Confirm rate limits vs volume
21.4 Hidden & ongoing costs
Connector maintenance (vendors and any direct sources change).
Status-mapping upkeep as states change terminology.
On-call/operational support for a production internal tool.
Vendor security reviews/DPAs; periodic pen tests; dependency upkeep.
Salesforce schema drift handling.

22. Risk Register
Risk
Sev
Like.
Impact
Mitigation
Owner
Review
UCC coverage gaps
High
High
Miss competing liens → bad collateral call
Vendor + covered states; explicit gap labels; human review; never imply clear
Underwriting+Eng
Phase 0 & each P2 release
Entity false-match
High
Med
Wrong status/liens on a deal
Conservative thresholds; ambiguity check; mandatory review; audited rate
Eng lead
Each ER change
Vendor cost at scale
Med
Med
Budget overrun
Cache+TTL; insource free sources; volume tiers
PM/Finance
Monthly
Vendor lock-in/outage
Med
Med
Single point of failure
Connector abstraction; multi-vendor capability; health monitor
Eng lead
Quarterly
Scraping/ToS/legal
High
Low–Med
Legal exposure
Rent data; restrict Playwright; legal sign-off
Legal+Eng
Before any direct source
FCRA/AML/exam compliance
High
Low
Regulatory action
Legal review; OFAC process; audit trail; retention policy
Compliance
Quarterly
Salesforce data quality
Med
High
Bad matches/syncs
Validation; dedupe; write-back canonical name; review queue
Ops+SF admin
Ongoing
SF integration drift
Med
Med
Sync breakage
Field-mapping tests; sandbox; versioned mapping
SF dev
Each SF change
Scoring miscalibration
Med
Med
Misleading status
Rule-based+versioned; calibrate vs analysts; limitations stated
Eng+Underwriting
Each score version
Data freshness/state lag
Med
Med
Outdated status
Timestamp everything; re-verify on key events; monitoring (P5)
Eng
Ongoing
Operational/on-call
Med
Med
Downtime, slow triage
Runbooks; alerting; health checks; restore drills
Eng lead
Quarterly
Maintenance burden
Med
High
Connector/mapping rot
Keep sources few; buy where possible; contract tests catch drift
Eng lead
Quarterly
Security breach / PII
High
Low
Data loss, trust/legal
RBAC, encryption, secrets mgr, audit, least privilege, IR plan
Security
Quarterly + post-incident

23. Leadership-Ready Recommendation
Build first: the platform Porter owns — verification workflow, canonical data model, explainable scoring, immutable evidence/audit, human review, and Salesforce export. This is durable, Porter-specific IP.
Do NOT build first: in-house 50-state scraping, UCC (until validated), native Salesforce UI, ML scoring, underwriting automation, or any external/sellable API.
Buy / validate before building: buy a real-time SOS/KYB vendor as the MVP data layer; validate, in Phase 0, the vendor's real field-level coverage (especially UCC) on Porter's actual recent leads, plus the Salesforce schema and legal/ToS posture.
MVP scope: search → verify → normalized status → OFAC screen → evidence → explainable status → human review → Salesforce export, on a swappable vendor connector.
Timeline & resources: ~8–12 weeks with 1–2 engineers (+ part-time PM/security/QA). ASSUMPTION pending volume/cloud/vendor confirmation.
Main risks: UCC coverage; entity false-match; vendor cost/lock-in; legal/ToS if scraping; Salesforce data quality.
23.1 First 10 next steps
Leadership sign-off on the hybrid approach + Phase 0 budget.
Pull 50–100 real, recent Porter leads/deals (incl. known UCC cases) as a test set.
Start Cobalt + Middesk trials; request volume quotes.
Score field-level coverage (status/officers/UCC) per vendor on the test set.
Run a Salesforce schema/automation session with Porter's SF admin.
Legal review: vendor terms, scraping policy, FCRA applicability, retention.
Choose vendor; finalize MVP scope + success gates.
Stand up repo, CI, staging/prod, secrets manager, connector skeleton.
Build Phase 1 (verify + evidence + review + OFAC + dashboard) on vendor sandbox.
Pilot with one sales pod + one underwriter; measure accuracy + time saved; iterate.
23.2 The decision leadership must make
Decision: Approve the hybrid (buy data, build platform) and fund a 1–2 week Phase 0 validation before any committed build. The single gating question Phase 0 answers: is vendor data coverage — especially UCC — good enough on Porter's real deals to justify the platform investment? Everything else follows from that answer.

24. Engineer-Ready Execution Summary
24.1 First sprint (2 weeks) tasks
Repo + CI (lint/type/test/scan) + Docker + docker-compose (Steps 1–2).
SQLAlchemy models + initial Alembic migration for core tables (Steps 3–4).
Source registry + credential refs + selection logic (Step 5).
First connector: chosen vendor (test mode) + OFAC ingest, passing contract tests (Step 6).
Raw event storage + hashing (Step 7).
Golden test set (~200 entities) assembled from real Porter leads.
24.2 Required repo structure
porter-verify/
  api/            # FastAPI app, routers, schemas (pydantic)
  workers/        # Prefect flows (verify_flow, bulk_flow)
  connectors/     # SourceConnector protocol + vendor, ofac, registry
  dashboard/      # Streamlit app (MVP)
  db/             # SQLAlchemy models + alembic/
  services/       # normalize, resolve, scoring, evidence, review, salesforce, report, audit
  tests/          # unit, contract, golden, api, permission
  infra/          # docker, compose, IaC, CI
  pyproject.toml  .env.sample  README.md
24.3 Required stack
Python 3.12, FastAPI, SQLAlchemy 2.x, Alembic, Prefect, Streamlit, Redis, PostgreSQL 16, Docker, GitHub Actions, Sentry, Vault/Secrets Manager, S3-compatible object store (WORM).
24.4 First database migrations
0001_init: source_registry, source_credentials, companies, company_identifiers, business_registrations, registered_agents, company_officers, verification_runs, raw_source_events, evidence_items, confidence_scores, review_decisions, salesforce_sync_status, users, roles, audit_logs, error_logs, generated_reports — with constraints, indexes (trigram on normalized_name), and append-only roles.
24.5 First connector to build
Chosen SOS/KYB vendor in test mode behind the SourceConnector contract, plus OFAC list ingest. Prove swappability with a second stub connector passing the same contract tests.
24.6 First dashboard page
Company Search → Company Profile (with status, identity, evidence timeline, score panel) — the smallest end-to-end slice a pilot user can use.
24.7 First tests to write
Status-normalization unit tests; connector contract tests; entity-resolution golden-set test (false-match <1%); permission tests per role; source-failure path test (no charge, review fallback).
24.8 First deployment target
Staging (cloud, prod-like, vendor test keys, no prod data); production after §5.4 exit criteria + security review.
24.9 Definition of done for MVP
>70% auto-verify; false-match <1%; status-correctness >98% on golden set.
Every run → immutable evidence + audit; OFAC in-flow.
Connector swappable (second stub passes contract tests).
RBAC + secrets + encryption + rate limiting verified; restore drill passed.
Pilot users (sales + underwriting) confirm measurable time savings.

Appendix: Public Sources
Cobalt Intelligence — product, returned fields, FAQ, pricing model: https://cobaltintelligence.com/
Cobalt Intelligence — public API documentation: https://documentation.cobaltintelligence.com/
Cobalt blog — SOS APIs vs Middesk analysis: https://cobaltintelligence.com/blog/post/secretary-of-state-apis-vs-middesk-a-critical-analysis-for-alternative-lenders
Middesk — Secretary of State API overview: https://www.middesk.com/blog/secretary-of-state-api
Middesk — UCC / liens API & docs: https://www.middesk.com/ucc-api
SAM.gov — Entity Management API (GSA Open Tech): https://open.gsa.gov/api/entity-api/
Porter Capital — invoice factoring & financing (company site): https://portercap.com/
Porter Capital review — model, advance rates, underwriting: https://www.unitedcapitalsource.com/business-loans/lender-reviews/porter-capital-review/
