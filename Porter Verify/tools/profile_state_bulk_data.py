"""Profile a state bulk-data directory containing Filings/Agents/Principals CSVs."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd


DELIMITER = r"\*\|\*"


def read_table(path: Path) -> pd.DataFrame:
    return pd.read_csv(
        path,
        sep=DELIMITER,
        engine="python",
        dtype=str,
        keep_default_na=False,
    )


def basic_profile(frame: pd.DataFrame) -> dict:
    return {
        "rows": len(frame),
        "columns": len(frame.columns),
        "column_names": frame.columns.tolist(),
        "exact_duplicate_rows": int(frame.duplicated().sum()),
    }


def main() -> None:
    source_dir = Path(sys.argv[1])
    filings = read_table(source_dir / "Filings.csv")
    agents = read_table(source_dir / "Agents.csv")
    principals = read_table(source_dir / "Principals.csv")

    filing_dates = pd.to_datetime(filings["INITIAL_FILING_DATE"], errors="coerce")
    entity_ids = set(filings["ENTITY_NUM"])
    agent_ids = set(agents["ENTITY_NUM"])
    principal_ids = set(principals["ENTITY_NUM"])
    agent_has_identity = agents[["ORG_NAME", "FIRST_NAME", "LAST_NAME"]].apply(
        lambda column: column.str.strip().ne("")
    ).any(axis=1)
    principal_has_identity = principals[["ORG_NAME", "FIRST_NAME", "LAST_NAME"]].apply(
        lambda column: column.str.strip().ne("")
    ).any(axis=1)
    staffing_pattern = (
        r"(?i)staffing|recruit(?:ing|ment|er)?|workforce|personnel|"
        r"employment (?:agency|services?)|human resources?|temporary help|"
        r"professional employer|\bpeo\b"
    )
    staffing_text = filings["ENTITY_NAME"].str.cat(filings["TYPE_OF_BUSINESS"], sep=" ")
    staffing_candidates = filings.loc[
        staffing_text.str.contains(staffing_pattern, regex=True, na=False),
        [
            "ENTITY_NAME",
            "ENTITY_NUM",
            "INITIAL_FILING_DATE",
            "ENTITY_TYPE",
            "TYPE_OF_BUSINESS",
        ],
    ]

    result = {
        "filings": basic_profile(filings),
        "agents": basic_profile(agents),
        "principals": basic_profile(principals),
        "filing_grain": {
            "blank_entity_ids": int(filings["ENTITY_NUM"].eq("").sum()),
            "duplicate_entity_ids": int(filings["ENTITY_NUM"].duplicated(keep=False).sum()),
            "distinct_entity_ids": int(filings["ENTITY_NUM"].nunique()),
        },
        "dates": {
            "minimum_initial_filing_date": filing_dates.min().date().isoformat(),
            "maximum_initial_filing_date": filing_dates.max().date().isoformat(),
            "invalid_or_blank_initial_filing_dates": int(filing_dates.isna().sum()),
            "rows_by_initial_filing_date": {
                date.strftime("%Y-%m-%d"): int(count)
                for date, count in filing_dates.value_counts().sort_index().items()
            },
        },
        "coverage": {
            "filings_with_agent": int(filings["ENTITY_NUM"].isin(agent_ids).sum()),
            "filings_with_principal_row": int(filings["ENTITY_NUM"].isin(principal_ids).sum()),
            "agent_rows_with_unknown_entity": int((~agents["ENTITY_NUM"].isin(entity_ids)).sum()),
            "principal_rows_with_unknown_entity": int(
                (~principals["ENTITY_NUM"].isin(entity_ids)).sum()
            ),
            "filings_with_nonblank_type_of_business": int(
                filings["TYPE_OF_BUSINESS"].str.strip().ne("").sum()
            ),
            "agent_rows_with_named_person_or_organization": int(agent_has_identity.sum()),
            "filings_with_named_agent": int(
                filings["ENTITY_NUM"].isin(set(agents.loc[agent_has_identity, "ENTITY_NUM"])).sum()
            ),
            "principal_rows_with_named_person_or_organization": int(
                principal_has_identity.sum()
            ),
            "filings_with_named_principal": int(
                filings["ENTITY_NUM"].isin(
                    set(principals.loc[principal_has_identity, "ENTITY_NUM"])
                ).sum()
            ),
            "filings_with_principal_address": int(
                filings["PRINCIPAL_ADDRESS"].str.strip().ne("").sum()
            ),
            "filings_with_mailing_address": int(
                filings["MAILING_ADDRESS"].str.strip().ne("").sum()
            ),
        },
        "distributions": {
            "entity_type": filings["ENTITY_TYPE"].value_counts().to_dict(),
            "filing_type": filings["FILING_TYPE"].value_counts().to_dict(),
            "entity_status": filings["ENTITY_STATUS"].value_counts().to_dict(),
            "jurisdiction_top_20": filings["JURISDICTION"].value_counts().head(20).to_dict(),
            "type_of_business_top_30": filings.loc[
                filings["TYPE_OF_BUSINESS"].str.strip().ne(""), "TYPE_OF_BUSINESS"
            ]
            .value_counts()
            .head(30)
            .to_dict(),
        },
        "relationship_grain": {
            "agents_duplicate_entity_ids": int(agents["ENTITY_NUM"].duplicated(keep=False).sum()),
            "principals_duplicate_entity_ids": int(
                principals["ENTITY_NUM"].duplicated(keep=False).sum()
            ),
            "max_agents_per_entity": int(agents.groupby("ENTITY_NUM").size().max()),
            "max_principals_per_entity": int(principals.groupby("ENTITY_NUM").size().max()),
        },
        "staffing_keyword_screen": {
            "candidate_count": len(staffing_candidates),
            "candidate_rows": staffing_candidates.to_dict(orient="records"),
        },
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
