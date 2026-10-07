# Wolters Kluwer Lien Solutions Analysis - Source Notes

Generated: June 19, 2026

## Reporting Job

- Audience: Product stakeholders
- Decision: Define what Porter should build after understanding Lien Solutions end to end
- Delivery mode: Static HTML
- Comparison baseline: Current `codex/four-state-live-connectors` codebase
- Scope: Publicly documented capabilities; no private demo, pricing, API, SLA, contract, or security materials

## Official Product Sources

- https://www.wolterskluwer.com/en/solutions/lien-solutions
- https://www.wolterskluwer.com/en/solutions/lien-solutions/markets/factoring
- https://www.wolterskluwer.com/en/solutions/lien-solutions/ucc-filing-and-public-records-search
- https://www.wolterskluwer.com/en/solutions/lien-solutions/ucc-filing-and-public-records-search/public-records-search
- https://www.wolterskluwer.com/en/solutions/lien-solutions/ucc-filing-and-public-records-search/lien-filings
- https://www.wolterskluwer.com/en/solutions/lien-solutions/ucc-filing-and-public-records-search/lien-management
- https://www.wolterskluwer.com/en/solutions/lien-solutions/ucc-filing-and-public-records-search/lien-management/analytics-and-reporting
- https://www.wolterskluwer.com/en/solutions/lien-solutions/ucc-filing-and-public-records-search/lien-management/auto-continuation
- https://www.wolterskluwer.com/en/solutions/lien-solutions/ucc-filing-and-public-records-search/lien-management/monitoring
- https://www.wolterskluwer.com/en/solutions/lien-solutions/ucc-filing-and-public-records-search/lien-management/portfolio-sync
- https://www.wolterskluwer.com/en/solutions/lien-solutions/ucc-filing-and-public-records-search/ilien-borrower-analytics

## Current Porter Evidence

- `src/porter_verify/connectors/`: SOS connector contract plus CO, CT, OR and OH implementations
- `src/porter_verify/workers/verify_flow.py`: entity resolution, evidence, OFAC and scoring flow
- `src/porter_verify/db/models/`: company, registration, evidence, audit, source policy and review models
- `src/porter_verify/api/`: current verify, company, evidence, review and source-health surfaces
- `docs/product_plan.md`: planned UCC, monitoring, security and underwriting requirements

## Report Structure Mapping

- Executive Summary: direct recommendation and current gap
- Key Findings: lifecycle taxonomy and capability comparison tables
- Recommended Next Steps: phased Porter Lien Intelligence build sequence
- Further Questions: decisions needed before implementation
- Caveats and Assumptions: public-material and validation limitations

## Omitted Visuals

No quantitative chart was used because the source material does not provide a comparable dataset, denominator, pricing series, verified performance metrics, or customer outcome measures. Exact capability and control tables are more defensible than a synthetic score or maturity chart.
