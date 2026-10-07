"""add ucc leads

Revision ID: b7d3f8a2c5e1
Revises: ab12c4d9e8f0
Create Date: 2026-07-03
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b7d3f8a2c5e1"
down_revision: str | None = "ab12c4d9e8f0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ucc_leads",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("exit_signal_id", sa.String(length=100), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=True),
        sa.Column("debtor_name", sa.String(length=500), nullable=False),
        sa.Column("state", sa.String(length=2), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("assigned_to_email", sa.String(length=320), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by_email", sa.String(length=320), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["exit_signal_id"], ["ucc_exit_signals.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("exit_signal_id", name="uq_ucc_leads_exit_signal_id"),
    )
    op.create_index("ix_ucc_leads_exit_signal_id", "ucc_leads", ["exit_signal_id"])
    op.create_index("ix_ucc_leads_company_id", "ucc_leads", ["company_id"])
    op.create_index("ix_ucc_leads_state", "ucc_leads", ["state"])
    op.create_index("ix_ucc_leads_status", "ucc_leads", ["status"])


def downgrade() -> None:
    op.drop_index("ix_ucc_leads_status", table_name="ucc_leads")
    op.drop_index("ix_ucc_leads_state", table_name="ucc_leads")
    op.drop_index("ix_ucc_leads_company_id", table_name="ucc_leads")
    op.drop_index("ix_ucc_leads_exit_signal_id", table_name="ucc_leads")
    op.drop_table("ucc_leads")
