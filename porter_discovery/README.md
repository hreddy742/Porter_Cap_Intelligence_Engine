# Porter Discovery

Porter Discovery is a new system for finding newly registered staffing and PEO companies, collecting evidence, researching intent signals, and preparing reviewed leads for sales.

This system is intentionally separate from Porter Verify. Porter Verify may be used as a reference, but Porter Discovery should not depend on Porter Verify being fully working unless a future task explicitly chooses that dependency.

Initial build order:

1. Define the project boundary and rules.
2. Build a small ingestion foundation with sample data.
3. Add the first real state source.
4. Classify staffing and PEO candidates.
5. Resolve company identity.
6. Research intent signals.
7. Score and explain candidates.
8. Add human review.
9. Export or send approved leads to Salesforce.

Keep each step small, tested where useful, and easy for a human engineer to review.

## NY Staffing Candidate Discovery MVP

Scans NY DOS "Corporations and Other Entities: All Filings" for legal names
matching a conservative staffing/PEO keyword list, and writes a reviewable
candidate list to `out/`. Every match is `evidence_level: candidate`, not a
confirmed classification. Standard library only. Run from the repository
root (one level above `porter_discovery/`):

```
python porter_discovery/discover_ny_staffing_candidates.py --check
python porter_discovery/discover_ny_staffing_candidates.py --input porter_discovery/samples/ny_dos_filings.csv
python porter_discovery/discover_ny_staffing_candidates.py --from-date 2026-08-01 --to-date 2026-08-07 --per-day-limit 3000
```
