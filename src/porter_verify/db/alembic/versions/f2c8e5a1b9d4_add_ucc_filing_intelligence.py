"""add UCC filing intelligence

Revision ID: f2c8e5a1b9d4
Revises: e1b7d4c9a8f3
Create Date: 2026-07-01
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

import sqlalchemy as sa
from alembic import op

revision: str = "f2c8e5a1b9d4"
down_revision: str | None = "e1b7d4c9a8f3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

KNOWN_FACTORS = (
    ("triumph-business-capital", "Triumph Business Capital", "FACTOR"),
    ("riviera-finance", "Riviera Finance", "FACTOR"),
    ("rts-financial", "RTS Financial", "FACTOR"),
    ("tci-business-capital", "TCI Business Capital", "FACTOR"),
    ("apex-capital-corp", "Apex Capital Corp", "FACTOR"),
    ("altline-southern-bank-company", "altLINE (Southern Bank Company)", "FACTOR"),
    ("universal-funding-corporation", "Universal Funding Corporation", "FACTOR"),
    ("prn-funding", "PRN Funding (healthcare staffing)", "FACTOR"),
    ("summar-financial", "Summar Financial", "FACTOR"),
    ("bluevine", "BlueVine", "FACTOR"),
    ("fundbox", "Fundbox", "FACTOR"),
    ("breakout-capital", "Breakout Capital", "FACTOR"),
)


def upgrade() -> None:
    op.create_table(
        "ucc_filings",
        sa.Column("id", sa.String(length=100), nullable=False),
        sa.Column("filing_id", sa.String(length=100), nullable=False),
        sa.Column("state", sa.String(length=2), nullable=False),
        sa.Column("filing_type", sa.String(length=30), nullable=False),
        sa.Column("debtor_name", sa.String(length=500), nullable=False),
        sa.Column("debtor_normalized", sa.String(length=500), nullable=False),
        sa.Column("debtor_address", sa.Text(), nullable=True),
        sa.Column("debtor_city", sa.String(length=200), nullable=True),
        sa.Column("debtor_state", sa.String(length=2), nullable=True),
        sa.Column("debtor_zip", sa.String(length=20), nullable=True),
        sa.Column("secured_party_name", sa.String(length=500), nullable=True),
        sa.Column("secured_party_normalized", sa.String(length=500), nullable=True),
        sa.Column("collateral_description", sa.Text(), nullable=True),
        sa.Column("filing_date", sa.Date(), nullable=True),
        sa.Column("termination_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=True),
        sa.Column("lender_type", sa.String(length=30), nullable=False),
        sa.Column("is_factoring_related", sa.Boolean(), nullable=False),
        sa.Column("is_mca_related", sa.Boolean(), nullable=False),
        sa.Column("source_state", sa.String(length=2), nullable=True),
        sa.Column("source_url", sa.String(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ucc_filings_filing_id", "ucc_filings", ["filing_id"])
    op.create_index("ix_ucc_filings_state", "ucc_filings", ["state"])
    op.create_index("ix_ucc_filings_debtor_normalized", "ucc_filings", ["debtor_normalized"])
    op.create_index(
        "ix_ucc_filings_secured_party_normalized",
        "ucc_filings",
        ["secured_party_normalized"],
    )
    op.create_index("ix_ucc_filings_filing_date", "ucc_filings", ["filing_date"])
    op.create_index("ix_ucc_filings_termination_date", "ucc_filings", ["termination_date"])

    op.create_table(
        "known_factors",
        sa.Column("id", sa.String(length=100), nullable=False),
        sa.Column("company_name", sa.String(length=500), nullable=False),
        sa.Column("normalized_name", sa.String(length=500), nullable=False),
        sa.Column("lender_type", sa.String(length=30), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("added_by", sa.String(length=320), nullable=True),
        sa.Column("added_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_known_factors_normalized_name", "known_factors", ["normalized_name"])

    op.create_table(
        "ucc_exit_signals",
        sa.Column("id", sa.String(length=100), nullable=False),
        sa.Column("debtor_name", sa.String(length=500), nullable=False),
        sa.Column("debtor_normalized", sa.String(length=500), nullable=False),
        sa.Column("state", sa.String(length=2), nullable=False),
        sa.Column("previous_factor", sa.String(length=500), nullable=True),
        sa.Column("ucc1_filing_id", sa.String(length=100), nullable=True),
        sa.Column("ucc3_filing_id", sa.String(length=100), nullable=False),
        sa.Column("ucc1_date", sa.Date(), nullable=True),
        sa.Column("ucc3_date", sa.Date(), nullable=False),
        sa.Column("days_since_exit", sa.Integer(), nullable=False),
        sa.Column("replacement_filed", sa.Boolean(), nullable=False),
        sa.Column("signal_strength", sa.String(length=10), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ucc_exit_signals_debtor_normalized",
        "ucc_exit_signals",
        ["debtor_normalized"],
    )
    op.create_index("ix_ucc_exit_signals_state", "ucc_exit_signals", ["state"])
    op.create_index("ix_ucc_exit_signals_ucc3_date", "ucc_exit_signals", ["ucc3_date"])

    op.create_table(
        "ucc_refresh_log",
        sa.Column("id", sa.String(length=100), nullable=False),
        sa.Column("state", sa.String(length=2), nullable=False),
        sa.Column("refresh_type", sa.String(length=20), nullable=False),
        sa.Column("records_added", sa.Integer(), nullable=False),
        sa.Column("records_updated", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("error_text", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ucc_refresh_log_state", "ucc_refresh_log", ["state"])

    known_factors = sa.table(
        "known_factors",
        sa.column("id", sa.String),
        sa.column("company_name", sa.String),
        sa.column("normalized_name", sa.String),
        sa.column("lender_type", sa.String),
        sa.column("notes", sa.Text),
        sa.column("added_by", sa.String),
        sa.column("added_at", sa.DateTime),
    )
    op.bulk_insert(
        known_factors,
        [
            {
                "id": row_id,
                "company_name": name,
                "normalized_name": _normalize(name),
                "lender_type": lender_type,
                "notes": "Initial Porter Verify seed list.",
                "added_by": "migration",
                "added_at": datetime(2026, 7, 1),
            }
            for row_id, name, lender_type in KNOWN_FACTORS
        ],
    )


def downgrade() -> None:
    op.drop_index("ix_ucc_refresh_log_state", table_name="ucc_refresh_log")
    op.drop_table("ucc_refresh_log")
    op.drop_index("ix_ucc_exit_signals_ucc3_date", table_name="ucc_exit_signals")
    op.drop_index("ix_ucc_exit_signals_state", table_name="ucc_exit_signals")
    op.drop_index("ix_ucc_exit_signals_debtor_normalized", table_name="ucc_exit_signals")
    op.drop_table("ucc_exit_signals")
    op.drop_index("ix_known_factors_normalized_name", table_name="known_factors")
    op.drop_table("known_factors")
    op.drop_index("ix_ucc_filings_termination_date", table_name="ucc_filings")
    op.drop_index("ix_ucc_filings_filing_date", table_name="ucc_filings")
    op.drop_index("ix_ucc_filings_secured_party_normalized", table_name="ucc_filings")
    op.drop_index("ix_ucc_filings_debtor_normalized", table_name="ucc_filings")
    op.drop_index("ix_ucc_filings_state", table_name="ucc_filings")
    op.drop_index("ix_ucc_filings_filing_id", table_name="ucc_filings")
    op.drop_table("ucc_filings")


def _normalize(value: str) -> str:
    return " ".join("".join(ch if ch.isalnum() else " " for ch in value.upper()).split())
