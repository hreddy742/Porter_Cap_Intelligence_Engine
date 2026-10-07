"""Deterministic UCC filing classification and exit-signal logic."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from sqlalchemy import and_, func, or_, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from porter_verify.db.base import utcnow
from porter_verify.db.models import KnownFactor, UccExitSignal, UccFiling, UccRefreshLog

MCA_INDICATORS = (
    "merchant",
    "advance",
    "funding solutions",
    "capital solutions",
    "bizfunding",
    "can capital",
    "yellowstone",
    "rapid advance",
    "greenbox",
)
BANK_INDICATORS = (
    "bank",
    "national bank",
    "federal savings",
    "credit union",
    "financial",
    "trust company",
)
EQUIPMENT_INDICATORS = ("equipment", "leasing", "capital corp", "systems finance")
INITIAL_KNOWN_FACTORS = (
    ("Triumph Business Capital", "FACTOR"),
    ("Riviera Finance", "FACTOR"),
    ("RTS Financial", "FACTOR"),
    ("TCI Business Capital", "FACTOR"),
    ("Apex Capital Corp", "FACTOR"),
    ("altLINE (Southern Bank Company)", "FACTOR"),
    ("Universal Funding Corporation", "FACTOR"),
    ("PRN Funding (healthcare staffing)", "FACTOR"),
    ("Summar Financial", "FACTOR"),
    ("BlueVine", "FACTOR"),
    ("Fundbox", "FACTOR"),
    ("Breakout Capital", "FACTOR"),
)


@dataclass(frozen=True)
class LenderClassification:
    lender_type: str
    is_factoring_related: bool
    is_mca_related: bool


def normalize_ucc_name(value: str | None) -> str:
    if not value:
        return ""
    return " ".join("".join(ch if ch.isalnum() else " " for ch in value.upper()).split())


def classify_lender(session: Session, secured_party_name: str | None) -> LenderClassification:
    seed_known_factors(session)
    normalized = normalize_ucc_name(secured_party_name)
    if not normalized:
        return LenderClassification("UNKNOWN", False, False)

    known_type = _known_lender_types(session).get(normalized)
    if known_type is not None:
        return LenderClassification(known_type, known_type == "FACTOR", False)

    text = normalized.lower()
    if any(indicator in text for indicator in MCA_INDICATORS):
        return LenderClassification("MCA", False, True)
    if any(indicator in text for indicator in BANK_INDICATORS):
        return LenderClassification("BANK", False, False)
    if any(indicator in text for indicator in EQUIPMENT_INDICATORS):
        return LenderClassification("EQUIPMENT", False, False)
    return LenderClassification("UNKNOWN", False, False)


def apply_lender_classification(session: Session, filing: UccFiling) -> None:
    result = classify_lender(session, filing.secured_party_name)
    filing.lender_type = result.lender_type
    filing.is_factoring_related = result.is_factoring_related
    filing.is_mca_related = result.is_mca_related


def find_ucc_filings(session: Session, company: str, state: str | None = None) -> list[UccFiling]:
    normalized = normalize_ucc_name(company)
    if not normalized:
        return []

    variants = _lookup_variants(normalized)
    name_filters = [UccFiling.debtor_normalized.in_(variants)]
    name_filters.extend(UccFiling.debtor_normalized.like(f"{variant} %") for variant in variants)
    filters = [or_(*name_filters)]
    if state:
        filters.append(UccFiling.state == state.upper())
    return list(
        session.scalars(
            select(UccFiling)
            .where(*filters)
            .order_by(UccFiling.filing_date.desc().nullslast(), UccFiling.filing_id)
            .limit(200)
        )
    )


def _lookup_variants(normalized: str) -> list[str]:
    suffixes = {"LLC", "L L C", "INC", "CORP", "CORPORATION", "CO", "COMPANY", "LTD"}
    tokens = normalized.split()
    stripped = " ".join(token for token in tokens if token not in suffixes)
    variants = [normalized, stripped]
    return [
        variant
        for index, variant in enumerate(variants)
        if variant and variant not in variants[:index]
    ]


def known_factors(session: Session) -> list[KnownFactor]:
    seed_known_factors(session)
    return list(session.scalars(select(KnownFactor).order_by(KnownFactor.company_name)))


def seed_known_factors(session: Session) -> None:
    try:
        existing = session.scalar(select(func.count()).select_from(KnownFactor)) or 0
    except OperationalError:
        session.rollback()
        return
    if existing:
        return
    added_at = utcnow()
    for company_name, lender_type in INITIAL_KNOWN_FACTORS:
        session.add(
            KnownFactor(
                id=_known_factor_id(company_name),
                company_name=company_name,
                normalized_name=normalize_ucc_name(company_name),
                lender_type=lender_type,
                notes="Initial Porter Verify seed list.",
                added_by="system",
                added_at=added_at,
            )
        )
    session.commit()


def add_known_factor(
    session: Session,
    *,
    company_name: str,
    lender_type: str,
    notes: str | None,
    added_by: str,
) -> KnownFactor:
    normalized = normalize_ucc_name(company_name)
    row = session.scalar(select(KnownFactor).where(KnownFactor.normalized_name == normalized))
    if row is None:
        row = KnownFactor(
            id=str(uuid.uuid4()),
            company_name=company_name.strip(),
            normalized_name=normalized,
            lender_type=lender_type,
            notes=notes,
            added_by=added_by,
            added_at=utcnow(),
        )
        session.add(row)
    else:
        row.company_name = company_name.strip()
        row.lender_type = lender_type
        row.notes = notes
    session.commit()
    session.refresh(row)
    return row


def _known_factor_id(company_name: str) -> str:
    return normalize_ucc_name(company_name).lower().replace(" ", "-")


def _known_lender_types(session: Session) -> dict[str, str]:
    cached = session.info.get("known_lender_types")
    if isinstance(cached, dict):
        return cached
    rows = session.execute(select(KnownFactor.normalized_name, KnownFactor.lender_type)).all()
    known = {normalized: lender_type for normalized, lender_type in rows}
    session.info["known_lender_types"] = known
    return known


def detect_exit_signals(session: Session, *, today: date | None = None) -> int:
    today = today or date.today()
    since = today - timedelta(days=90)
    created = 0
    terminations = session.scalars(
        select(UccFiling).where(
            UccFiling.filing_type == "UCC3",
            UccFiling.termination_date >= since,
            UccFiling.debtor_normalized != "",
        )
    ).all()

    for termination in terminations:
        ucc1 = _matching_original(session, termination)
        if ucc1 is None or ucc1.is_mca_related:
            continue
        replacement = _replacement_filed(session, termination)
        if replacement:
            continue
        strength = _signal_strength(ucc1)
        if strength is None:
            continue
        signal_id = f"{termination.state}:{termination.filing_id}"
        existing = session.get(UccExitSignal, signal_id)
        if existing is not None:
            continue
        ucc3_date = termination.termination_date or termination.filing_date
        if ucc3_date is None:
            continue
        session.add(
            UccExitSignal(
                id=signal_id,
                debtor_name=termination.debtor_name,
                debtor_normalized=termination.debtor_normalized,
                state=termination.state,
                previous_factor=ucc1.secured_party_name,
                ucc1_filing_id=ucc1.filing_id,
                ucc3_filing_id=termination.filing_id,
                ucc1_date=ucc1.filing_date,
                ucc3_date=ucc3_date,
                days_since_exit=(today - ucc3_date).days,
                replacement_filed=False,
                signal_strength=strength,
                created_at=utcnow(),
            )
        )
        created += 1
    session.commit()
    return created


def ucc_counts(session: Session) -> dict:
    filing_count = session.scalar(select(func.count()).select_from(UccFiling)) or 0
    exit_count = session.scalar(select(func.count()).select_from(UccExitSignal)) or 0
    states = [
        row[0]
        for row in session.execute(
            select(UccFiling.state).distinct().order_by(UccFiling.state)
        ).all()
    ]
    refreshes = {
        state: value.isoformat() if value else None
        for state, value in session.execute(
            select(UccRefreshLog.state, func.max(UccRefreshLog.finished_at)).group_by(
                UccRefreshLog.state
            )
        ).all()
    }
    return {
        "ucc_filing_count": filing_count,
        "ucc_exit_signals": exit_count,
        "ucc_states_loaded": states,
        "last_ucc_refresh": refreshes,
    }


def record_refresh_log(
    session: Session,
    *,
    state: str,
    refresh_type: str,
    records_added: int,
    records_updated: int,
    started_at: datetime,
    status: str,
    error_text: str | None = None,
) -> UccRefreshLog:
    row = UccRefreshLog(
        id=str(uuid.uuid4()),
        state=state.upper(),
        refresh_type=refresh_type,
        records_added=records_added,
        records_updated=records_updated,
        started_at=started_at,
        finished_at=utcnow(),
        status=status,
        error_text=error_text,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def _matching_original(session: Session, termination: UccFiling) -> UccFiling | None:
    filters = [
        UccFiling.state == termination.state,
        UccFiling.debtor_normalized == termination.debtor_normalized,
        UccFiling.filing_type == "UCC1",
    ]
    if termination.secured_party_normalized:
        filters.append(
            or_(
                UccFiling.secured_party_normalized == termination.secured_party_normalized,
                UccFiling.secured_party_normalized.is_(None),
            )
        )
    return session.scalar(
        select(UccFiling)
        .where(*filters)
        .order_by(UccFiling.filing_date.desc().nullslast())
        .limit(1)
    )


def _replacement_filed(session: Session, termination: UccFiling) -> bool:
    ucc3_date = termination.termination_date or termination.filing_date
    if ucc3_date is None:
        return False
    replacement = session.scalar(
        select(UccFiling.id)
        .where(
            and_(
                UccFiling.state == termination.state,
                UccFiling.debtor_normalized == termination.debtor_normalized,
                UccFiling.filing_type == "UCC1",
                UccFiling.filing_date > ucc3_date,
                UccFiling.filing_date <= ucc3_date + timedelta(days=30),
            )
        )
        .limit(1)
    )
    return replacement is not None


def _signal_strength(ucc1: UccFiling) -> str | None:
    if ucc1.lender_type == "FACTOR" or ucc1.is_factoring_related:
        return "HOT"
    if ucc1.lender_type in {"BANK", "EQUIPMENT", "ABL"}:
        return "WARM"
    return None
