"""add UCC search orders

Revision ID: b5e3f9d2a7c1
Revises: a4d2e8c1f6b9
Create Date: 2026-06-19
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b5e3f9d2a7c1"
down_revision: str | None = "a4d2e8c1f6b9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ucc_search_orders",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("state", sa.String(length=2), nullable=False),
        sa.Column("search_name", sa.String(length=500), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("outcome", sa.String(length=30), nullable=True),
        sa.Column("source_url", sa.String(length=1000), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("requested_by_email", sa.String(length=320), nullable=False),
        sa.Column("completed_by_email", sa.String(length=320), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_ucc_search_orders_company_id"), "ucc_search_orders", ["company_id"]
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_ucc_search_orders_company_id"), table_name="ucc_search_orders")
    op.drop_table("ucc_search_orders")
