"""Shared ingestion path for targeted public UCC search results."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Callable

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from porter_verify.db.base import utcnow
from porter_verify.db.models import UccFiling
from porter_verify.services.ucc_intelligence import apply_lender_classification, normalize_ucc_name


@dataclass(frozen=True)
class PublicSearchUccResult:
    state: str
    filing_id: str
    debtor_name: str
    filing_type: str
    status: str
    search_query: str
    source_url: str
    secured_party_name: str | None = None
    filing_date: date | None = None
    termination_date: date | None = None
    collateral_description: str | None = None
    debtor_address: str | None = None
    debtor_city: str | None = None
    debtor_state: str | None = None
    debtor_zip: str | None = None
    match_confidence: int | None = None


def ucc_name_variants(company_name: str) -> list[str]:
    normalized = normalize_ucc_name(company_name)
    if not normalized:
        return []
    suffixes = {"LLC", "L L C", "INC", "CORP", "CORPORATION", "CO", "COMPANY", "LTD"}
    tokens = [token for token in normalized.split() if token not in suffixes]
    variants = [company_name.strip(), normalized]
    if tokens:
        variants.append(" ".join(tokens))
    if len(tokens) >= 2:
        variants.append(" ".join(tokens[:2]))
    deduped: list[str] = []
    seen: set[str] = set()
    for variant in variants:
        key = variant.strip()
        if key and key not in seen:
            deduped.append(variant)
            seen.add(key)
    return deduped


def ingest_public_search_results(
    session: Session,
    results: list[PublicSearchUccResult],
) -> int:
    rows = []
    for result in results:
        filing = _filing_from_result(result)
        apply_lender_classification(session, filing)
        rows.append(_filing_dict(filing))
    _upsert(session, rows)
    session.commit()
    return len(rows)


def _filing_from_result(result: PublicSearchUccResult) -> UccFiling:
    secured_party = result.secured_party_name
    filing_type = _filing_type(result.filing_type)
    termination_date = result.termination_date
    if filing_type == "UCC3" and termination_date is None:
        termination_date = result.filing_date
    state = result.state.upper()
    return UccFiling(
        id=f"{state}:SEARCH:{result.filing_id}",
        filing_id=result.filing_id,
        state=state,
        filing_type=filing_type,
        debtor_name=result.debtor_name,
        debtor_normalized=normalize_ucc_name(result.debtor_name),
        debtor_address=result.debtor_address,
        debtor_city=result.debtor_city,
        debtor_state=result.debtor_state,
        debtor_zip=result.debtor_zip,
        secured_party_name=secured_party,
        secured_party_normalized=normalize_ucc_name(secured_party),
        collateral_description=result.collateral_description,
        filing_date=result.filing_date,
        termination_date=termination_date,
        status=_status(result.status, filing_type),
        lender_type="UNKNOWN",
        is_factoring_related=False,
        is_mca_related=False,
        source_state=state,
        source_url=result.source_url,
        acquisition_method="PUBLIC_SEARCH",
        search_query=result.search_query,
        match_confidence=result.match_confidence,
    )


def _upsert(session: Session, rows: list[dict]) -> None:
    if not rows:
        return
    table = UccFiling.__table__
    dialect = session.get_bind().dialect.name
    if dialect == "sqlite":
        statement = sqlite_insert(table).values(rows)
    elif dialect == "postgresql":
        statement = pg_insert(table).values(rows)
    else:
        for row in rows:
            session.merge(UccFiling(**row))
        return
    excluded = statement.excluded
    updates = {
        column.name: getattr(excluded, column.name)
        for column in table.columns
        if column.name not in {"id", "created_at", "updated_at"}
    }
    updates["updated_at"] = utcnow()
    session.execute(statement.on_conflict_do_update(index_elements=[table.c.id], set_=updates))


def _filing_dict(filing: UccFiling) -> dict:
    return {
        "id": filing.id,
        "filing_id": filing.filing_id,
        "state": filing.state,
        "filing_type": filing.filing_type,
        "debtor_name": filing.debtor_name,
        "debtor_normalized": filing.debtor_normalized,
        "debtor_address": filing.debtor_address,
        "debtor_city": filing.debtor_city,
        "debtor_state": filing.debtor_state,
        "debtor_zip": filing.debtor_zip,
        "secured_party_name": filing.secured_party_name,
        "secured_party_normalized": filing.secured_party_normalized,
        "collateral_description": filing.collateral_description,
        "filing_date": filing.filing_date,
        "termination_date": filing.termination_date,
        "status": filing.status,
        "lender_type": filing.lender_type,
        "is_factoring_related": filing.is_factoring_related,
        "is_mca_related": filing.is_mca_related,
        "source_state": filing.source_state,
        "source_url": filing.source_url,
        "acquisition_method": filing.acquisition_method,
        "search_query": filing.search_query,
        "match_confidence": filing.match_confidence,
    }


def _filing_type(value: str) -> str:
    text = normalize_ucc_name(value)
    if "TERMIN" in text or "RELEASE" in text:
        return "UCC3"
    if "CONTINUATION" in text:
        return "CONTINUATION"
    if "AMEND" in text:
        return "AMENDMENT"
    return "UCC1"


def _status(value: str, filing_type: str) -> str:
    text = normalize_ucc_name(value)
    if filing_type == "UCC3" or "TERMINATED" in text or "RELEASED" in text:
        return "TERMINATED"
    if "ACTIVE" in text or "FILED" in text:
        return "ACTIVE"
    if filing_type == "AMENDMENT":
        return "AMENDED"
    return value.upper() if value else "ACTIVE"


def _run_new_jersey(company: str) -> list[PublicSearchUccResult]:
    from porter_verify.connectors.new_jersey_ucc import search_new_jersey_ucc
    from porter_verify.connectors.new_jersey_ucc import (
        to_public_search_results as to_results,
    )

    return to_results(company, search_new_jersey_ucc(company))


def _run_idaho(company: str) -> list[PublicSearchUccResult]:
    from porter_verify.connectors.idaho_ucc import search_idaho_ucc
    from porter_verify.connectors.idaho_ucc import to_public_search_results as to_results

    return to_results(company, search_idaho_ucc(company))


def _run_ny(company: str) -> list[PublicSearchUccResult]:
    from porter_verify.connectors.ny_ucc import search_ny_ucc, to_public_search_results

    return to_public_search_results(company, search_ny_ucc(company))


def _run_ca(company: str) -> list[PublicSearchUccResult]:
    from porter_verify.connectors.ca_ucc import search_ca_ucc, to_public_search_results

    return to_public_search_results(company, search_ca_ucc(company))


def _run_il(company: str) -> list[PublicSearchUccResult]:
    from porter_verify.connectors.il_ucc import search_il_ucc, to_public_search_results

    return to_public_search_results(company, search_il_ucc(company))


def _run_pa(company: str) -> list[PublicSearchUccResult]:
    from porter_verify.connectors.pa_ucc import search_pa_ucc, to_public_search_results

    return to_public_search_results(company, search_pa_ucc(company))


def _run_mi(company: str) -> list[PublicSearchUccResult]:
    from porter_verify.connectors.mi_ucc import search_mi_ucc, to_public_search_results

    return to_public_search_results(company, search_mi_ucc(company))


def _run_nc(company: str) -> list[PublicSearchUccResult]:
    from porter_verify.connectors.nc_ucc import search_nc_ucc, to_public_search_results

    return to_public_search_results(company, search_nc_ucc(company))


def _run_md(company: str) -> list[PublicSearchUccResult]:
    from porter_verify.connectors.md_ucc import search_md_ucc, to_public_search_results

    return to_public_search_results(company, search_md_ucc(company))


def _run_mn(company: str) -> list[PublicSearchUccResult]:
    # mn_ucc.search_mn_ucc already returns PublicSearchUccResult objects
    # directly (debtor-name search requires a paid MBLS account and raises
    # MnUccAuthRequired / MnUccPaywallError if credentials are missing).
    from porter_verify.connectors.mn_ucc import search_mn_ucc

    return search_mn_ucc(company)


def _run_sc(company: str) -> list[PublicSearchUccResult]:
    from porter_verify.connectors.sc_ucc import search_sc_ucc, to_public_search_results

    return to_public_search_results(company, search_sc_ucc(company))


def _run_ky(company: str) -> list[PublicSearchUccResult]:
    from porter_verify.connectors.ky_ucc import search_ky_ucc, to_public_search_results

    return to_public_search_results(company, search_ky_ucc(company))


def _run_mo(company: str) -> list[PublicSearchUccResult]:
    # mo_ucc.search_mo_ucc always raises MissouriUccAuthRequiredError today;
    # MO's UCC search portal requires an authenticated Corporate E-account.
    from porter_verify.connectors.mo_ucc import search_mo_ucc, to_public_search_results

    return to_public_search_results(company, search_mo_ucc(company))


def _run_az(company: str) -> list[PublicSearchUccResult]:
    from porter_verify.connectors.az_ucc import search_az_ucc, to_public_search_results

    return to_public_search_results(company, search_az_ucc(company))


def _run_wi(company: str) -> list[PublicSearchUccResult]:
    from porter_verify.connectors.wi_ucc import search_wi_ucc, to_public_search_results

    return to_public_search_results(company, search_wi_ucc(company))


def _run_in(company: str) -> list[PublicSearchUccResult]:
    # in_ucc.search_in_ucc always raises InUccCaptchaRequiredError today;
    # IN's UCC search portal requires solving a CAPTCHA.
    from porter_verify.connectors.in_ucc import search_in_ucc, to_public_search_results

    return to_public_search_results(company, search_in_ucc(company))


def _run_nv(company: str) -> list[PublicSearchUccResult]:
    # nv_ucc.search_nv_ucc always raises NvUccBlockedError today; both known
    # NV UCC search entry points are bot-management blocked.
    from porter_verify.connectors.nv_ucc import search_nv_ucc, to_public_search_results

    return to_public_search_results(company, search_nv_ucc(company))


def _run_ar(company: str) -> list[PublicSearchUccResult]:
    from porter_verify.connectors.ar_ucc import search_ar_ucc, to_public_search_results

    return to_public_search_results(company, search_ar_ucc(company))


# Registry of every state supported via targeted live public search (as
# opposed to bulk-loaded states, which are ingested via scheduler.py cron
# jobs calling fetch_XX_ucc_rows/ingest_XX_ucc_rows). Each callable takes a
# company name and returns a list of PublicSearchUccResult ready for
# ingest_public_search_results(). Imports are deferred to avoid pulling in
# every connector's dependencies (httpx, playwright, etc.) at import time.
SUPPORTED_STATES: dict[str, Callable[[str], list[PublicSearchUccResult]]] = {
    "NJ": _run_new_jersey,
    "ID": _run_idaho,
    "NY": _run_ny,
    "CA": _run_ca,
    "IL": _run_il,
    "PA": _run_pa,
    "MI": _run_mi,
    "NC": _run_nc,
    "MD": _run_md,
    "MN": _run_mn,
    "SC": _run_sc,
    "KY": _run_ky,
    "MO": _run_mo,
    "AZ": _run_az,
    "WI": _run_wi,
    "IN": _run_in,
    "NV": _run_nv,
    "AR": _run_ar,
}


def run_targeted_search(state: str, company_name: str) -> list[PublicSearchUccResult]:
    """Run the targeted public search connector for ``state`` if supported.

    Raises KeyError if the state is not in SUPPORTED_STATES.
    """
    handler = SUPPORTED_STATES[state.upper()]
    return handler(company_name)
