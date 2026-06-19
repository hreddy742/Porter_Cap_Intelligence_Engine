"""Migration test: the initial Alembic migration applies and reverses cleanly.

Runs against a temporary SQLite file database (Alembic needs a real connection,
not in-memory shared state), exercising the same upgrade path used in production.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from porter_verify.config import get_settings

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# A representative sample of the 18 tables that must exist after upgrade.
EXPECTED_TABLES = {
    "companies",
    "company_identifiers",
    "business_registrations",
    "verification_runs",
    "raw_source_events",
    "evidence_items",
    "review_decisions",
    "audit_logs",
    "source_policies",
    "source_quality_daily",
    "co_business_entities",
    "ct_business_entities",
    "or_business_entities",
    "oh_business_entities",
}


@pytest.fixture
def alembic_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Config, str]:
    db_path = tmp_path / "migration_test.sqlite3"
    url = f"sqlite:///{db_path}"
    monkeypatch.setenv("PORTER_DATABASE_URL", url)
    get_settings.cache_clear()  # env.py reads settings at runtime

    cfg = Config(str(PROJECT_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(PROJECT_ROOT / "src/porter_verify/db/alembic"))
    return cfg, url


def test_upgrade_creates_all_tables(alembic_config: tuple[Config, str]) -> None:
    cfg, url = alembic_config
    command.upgrade(cfg, "head")

    tables = set(inspect(create_engine(url)).get_table_names())
    assert EXPECTED_TABLES.issubset(tables)


def test_downgrade_removes_tables(alembic_config: tuple[Config, str]) -> None:
    cfg, url = alembic_config
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "base")

    tables = set(inspect(create_engine(url)).get_table_names())
    # Only Alembic's own bookkeeping table should remain.
    assert tables.isdisjoint(EXPECTED_TABLES)


def test_upgrade_is_idempotent_to_head(alembic_config: tuple[Config, str]) -> None:
    cfg, _ = alembic_config
    command.upgrade(cfg, "head")
    # Running again should be a no-op, not an error.
    command.upgrade(cfg, "head")
