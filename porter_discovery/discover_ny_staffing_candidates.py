#!/usr/bin/env python3
"""NY Staffing Candidate Discovery MVP.

Scans New York DOS "Corporations and Other Entities: All Filings" records
for legal names that conservatively match staffing/PEO keywords, and writes
a reviewable candidate list. A keyword match is not a confirmed
classification, so every output record is tagged evidence_level=candidate.

Usage:
    python discover_ny_staffing_candidates.py --check
    python discover_ny_staffing_candidates.py --input samples/ny_dos_filings.csv
    python discover_ny_staffing_candidates.py --from-date 2026-08-01 --to-date 2026-08-07 --per-day-limit 3000
"""
import argparse
import csv
import io
import json
import shutil
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
OUT_DIR = SCRIPT_DIR / "out"

SOCRATA_DATASET_ID = "63wc-4exh"
SOCRATA_CSV_URL = f"https://data.ny.gov/resource/{SOCRATA_DATASET_ID}.csv"
DATASET_PAGE_URL = (
    "https://data.ny.gov/Economic-Development/"
    "Corporations-and-Other-Entities-All-Filings/63wc-4exh"
)
SOURCE_NAME = "NY DOS Corporations and Other Entities: All Filings"

# Conservative legal-name keywords only. No fuzzy matching.
KEYWORDS = [
    "staffing",
    "recruiting",
    "recruitment",
    "workforce",
    "employment agency",
    "temporary staffing",
    "temp agency",
    "talent acquisition",
    "professional employer",
    "peo",
    "employee leasing",
    "payroll staffing",
]

OUTPUT_FIELDS = [
    "source_state",
    "source_name",
    "source_registration_id",
    "legal_name",
    "filing_date",
    "entity_type",
    "jurisdiction",
    "matched_keyword",
    "candidate_reason",
    "evidence_level",
    "source_url",
    "documenttype",
    "for_inc_date",
    "fict_name",
]


def normalize_row_keys(row):
    return {(k or "").strip().lower(): (v or "").strip() for k, v in row.items()}


def match_keyword(legal_name):
    """Return the first matching keyword, or None. Plain substring match only."""
    name_lower = legal_name.lower()
    for keyword in KEYWORDS:
        if keyword in name_lower:
            return keyword
    return None


def normalize_record(row):
    """Turn one raw DOS filing row into a reviewable candidate record, or None."""
    legal_name = row.get("corp_name", "")
    if not legal_name:
        return None

    matched_keyword = match_keyword(legal_name)
    if matched_keyword is None:
        return None

    registration_id = row.get("corpid_num", "")
    source_url = (
        f"https://data.ny.gov/resource/{SOCRATA_DATASET_ID}.json?corpid_num={registration_id}"
        if registration_id
        else DATASET_PAGE_URL
    )

    return {
        "source_state": "NY",
        "source_name": SOURCE_NAME,
        "source_registration_id": registration_id,
        "legal_name": legal_name,
        "filing_date": row.get("date_filed", ""),
        "entity_type": row.get("entitytype", ""),
        "jurisdiction": row.get("juris", ""),
        "matched_keyword": matched_keyword,
        "candidate_reason": f"Legal name matches staffing/PEO keyword '{matched_keyword}'",
        "evidence_level": "candidate",
        "source_url": source_url,
        "documenttype": row.get("documenttype", ""),
        "for_inc_date": row.get("for_inc_date", ""),
        "fict_name": row.get("fict_name", ""),
        "evidence": row,
    }


def find_candidates(raw_rows):
    rows = (normalize_row_keys(r) for r in raw_rows)
    records = [normalize_record(r) for r in rows]
    records = [r for r in records if r is not None]
    records.sort(key=lambda r: r["filing_date"], reverse=True)
    return records


def read_local_rows(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def fetch_day_rows(day_str, per_day_limit, timeout=30):
    where = f"date_filed between '{day_str}T00:00:00' and '{day_str}T23:59:59'"
    params = {"$where": where, "$limit": str(per_day_limit)}
    url = SOCRATA_CSV_URL + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "porter-discovery/0.1"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        text = resp.read().decode("utf-8")
    return list(csv.DictReader(io.StringIO(text)))


def fetch_remote_rows(from_date, to_date, per_day_limit):
    rows = []
    errors = []
    day = from_date
    while day <= to_date:
        day_str = day.isoformat()
        try:
            day_rows = fetch_day_rows(day_str, per_day_limit)
            rows.extend(day_rows)
            print(f"  {day_str}: {len(day_rows)} rows fetched", file=sys.stderr)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            errors.append((day_str, str(exc)))
            print(f"  {day_str}: FAILED ({exc})", file=sys.stderr)
        day += timedelta(days=1)

    if errors and not rows:
        raise RuntimeError(
            f"all {len(errors)} day(s) failed to fetch; first error on {errors[0][0]}: {errors[0][1]}"
        )
    return rows


def write_outputs(records, out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / "ny_staffing_candidates.json"
    json_path.write_text(json.dumps(records, indent=2), encoding="utf-8")

    csv_path = out_dir / "ny_staffing_candidates.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_FIELDS + ["evidence"])
        writer.writeheader()
        for record in records:
            row = {k: record.get(k, "") for k in OUTPUT_FIELDS}
            row["evidence"] = json.dumps(record["evidence"], ensure_ascii=False)
            writer.writerow(row)

    return json_path, csv_path


def parse_date(value):
    return datetime.strptime(value, "%Y-%m-%d").date()


CHECK_FIXTURE_ROWS = [
    {
        "corpid_num": "1001",
        "film_num": "A1",
        "date_filed": "2026-08-20",
        "corp_name": "Acme Staffing Solutions Inc",
        "entitytype": "DOMESTIC BUSINESS CORPORATION",
        "documenttype": "INITIAL FILING",
        "juris": "NEW YORK",
        "for_inc_date": "",
        "fict_name": "",
    },
    {
        "corpid_num": "1002",
        "film_num": "A2",
        "date_filed": "2026-08-21",
        "corp_name": "Best Workforce Solutions LLC",
        "entitytype": "DOMESTIC LLC",
        "documenttype": "INITIAL FILING",
        "juris": "NEW YORK",
        "for_inc_date": "",
        "fict_name": "",
    },
    {
        "corpid_num": "1003",
        "film_num": "A3",
        "date_filed": "2026-08-19",
        "corp_name": "Stafford Consulting Group Inc",
        "entitytype": "DOMESTIC BUSINESS CORPORATION",
        "documenttype": "INITIAL FILING",
        "juris": "NEW YORK",
        "for_inc_date": "",
        "fict_name": "",
    },
    {
        "corpid_num": "1004",
        "film_num": "A4",
        "date_filed": "2026-08-18",
        "corp_name": "Acme Widgets Manufacturing Inc",
        "entitytype": "DOMESTIC BUSINESS CORPORATION",
        "documenttype": "INITIAL FILING",
        "juris": "NEW YORK",
        "for_inc_date": "",
        "fict_name": "",
    },
]


def run_check():
    records = find_candidates(CHECK_FIXTURE_ROWS)

    assert len(records) >= 2, f"expected at least 2 candidates, got {len(records)}"

    names = {r["legal_name"] for r in records}
    assert "Stafford Consulting Group Inc" not in names, "Stafford must not match"
    assert "Acme Widgets Manufacturing Inc" not in names, "non-staffing company must not match"

    for r in records:
        assert r["evidence_level"] == "candidate", "evidence_level must be 'candidate'"
        assert r["evidence"], "raw evidence row must be preserved"

    check_dir = OUT_DIR / "_check"
    json_path, csv_path = write_outputs(records, check_dir)
    assert json_path.exists() and csv_path.exists(), "outputs must be written"
    written_back = json.loads(json_path.read_text(encoding="utf-8"))
    assert len(written_back) == len(records), "JSON output must round-trip all records"
    shutil.rmtree(check_dir)

    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="run built-in self-check and exit")
    parser.add_argument("--input", help="path to a local NY DOS filings CSV")
    parser.add_argument("--from-date", help="start date YYYY-MM-DD (inclusive)")
    parser.add_argument("--to-date", help="end date YYYY-MM-DD (inclusive)")
    parser.add_argument("--per-day-limit", type=int, default=3000, help="max rows fetched per day")
    args = parser.parse_args()

    if args.check:
        records = run_check()
        print(f"OK: --check passed ({len(records)} candidates in fixture)")
        return

    if args.input:
        raw_rows = read_local_rows(args.input)
    elif args.from_date and args.to_date:
        from_date = parse_date(args.from_date)
        to_date = parse_date(args.to_date)
        if from_date > to_date:
            parser.error("--from-date must not be after --to-date")
        raw_rows = fetch_remote_rows(from_date, to_date, args.per_day_limit)
    else:
        parser.error("provide --check, --input, or both --from-date and --to-date")

    records = find_candidates(raw_rows)
    json_path, csv_path = write_outputs(records, OUT_DIR)

    print(f"Scanned {len(raw_rows)} filing(s), found {len(records)} candidate(s)")
    print(f"Wrote {json_path}")
    print(f"Wrote {csv_path}")
    for r in records[:5]:
        print(f"  - {r['legal_name']} ({r['filing_date']}, matched '{r['matched_keyword']}')")


if __name__ == "__main__":
    main()
