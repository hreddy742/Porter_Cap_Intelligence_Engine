"""add Alabama business entities

Revision ID: d1a7c9e4b6f2
Revises: c6f4a0e3b8d2
Create Date: 2026-06-29
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d1a7c9e4b6f2"
down_revision: str | None = "c6f4a0e3b8d2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "al_business_entities",
        sa.Column("entity_id", sa.String(length=50), nullable=False),
        sa.Column("entity_name", sa.String(length=500), nullable=False),
        sa.Column("normalized_name", sa.String(length=500), nullable=False),
        sa.Column("status_raw", sa.String(length=200), nullable=True),
        sa.Column("entity_type", sa.String(length=100), nullable=True),
        sa.Column("formation_date", sa.Date(), nullable=True),
        sa.Column("principal_address", sa.Text(), nullable=True),
        sa.Column("mailing_address", sa.Text(), nullable=True),
        sa.Column("jurisdiction", sa.String(length=100), nullable=True),
        sa.Column("source_record_url", sa.String(length=1000), nullable=True),
        sa.Column("agent_name", sa.String(length=300), nullable=True),
        sa.Column("agent_address", sa.Text(), nullable=True),
        sa.Column("officers", sa.JSON(), nullable=False),
        sa.Column("raw", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("entity_id"),
    )
    op.create_index(
        op.f("ix_al_business_entities_normalized_name"),
        "al_business_entities",
        ["normalized_name"],
    )
    op.create_index(
        op.f("ix_al_business_entities_formation_date"),
        "al_business_entities",
        ["formation_date"],
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_al_business_entities_formation_date"), table_name="al_business_entities")
    op.drop_index(
        op.f("ix_al_business_entities_normalized_name"), table_name="al_business_entities"
    )
    op.drop_table("al_business_entities")
