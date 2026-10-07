"""Seed sample data by running verifications against the mock vendor.

Usage (after `alembic upgrade head`):

    python scripts/seed.py

Idempotent: re-running adds new runs but no duplicate companies (dedupe_key). Uses
the configured database (PORTER_DATABASE_URL) and evidence dir.
"""

from __future__ import annotations

from sqlalchemy.orm import sessionmaker

from porter_verify.config import get_settings
from porter_verify.connectors.factory import build_default_registry
from porter_verify.db.session import create_db_engine
from porter_verify.services.evidence import EvidenceStore
from porter_verify.workers.verify_flow import run_verification

# Sample leads spanning the verification outcomes.
SAMPLE_LEADS = [
    ("Acme Logistics LLC", "TX"),
    ("Zenith Pharmaceuticals Inc", "CA"),
    ("Defunct Holdings LLC", "DE"),
    ("Lone Star Freight Co", "TX"),
    ("Acme Logistics", "TX"),  # partial name -> needs review
]


def main() -> None:
    settings = get_settings()
    engine = create_db_engine(settings)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    registry = build_default_registry()
    store = EvidenceStore(settings.evidence_dir)

    with factory() as session:
        for name, state in SAMPLE_LEADS:
            outcome = run_verification(
                session,
                registry=registry,
                evidence_store=store,
                name=name,
                state=state,
                actor="seed@portercap.net",
            )
            status = outcome.verification_status.value if outcome.verification_status else "n/a"
            print(f"  {name} ({state}) -> {status}")

    print("Seed complete.")


if __name__ == "__main__":
    main()
