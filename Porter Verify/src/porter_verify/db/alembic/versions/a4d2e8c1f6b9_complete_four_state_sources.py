"""complete four-state source staging

Revision ID: a4d2e8c1f6b9
Revises: f3a1c9b7d2e4
Create Date: 2026-06-18
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a4d2e8c1f6b9"
down_revision: str | None = "f3a1c9b7d2e4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = ("co_business_entities", "ct_business_entities", "or_business_entities")


def upgrade() -> None:
    with op.batch_alter_table("business_registrations") as batch:
        batch.add_column(sa.Column("mailing_address", sa.String(length=500), nullable=True))
        batch.add_column(sa.Column("jurisdiction", sa.String(length=100), nullable=True))
        batch.add_column(sa.Column("source_record_url", sa.String(length=1000), nullable=True))

    for table in TABLES:
        with op.batch_alter_table(table) as batch:
            batch.add_column(sa.Column("mailing_address", sa.Text(), nullable=True))
            batch.add_column(sa.Column("jurisdiction", sa.String(length=100), nullable=True))
            batch.add_column(sa.Column("source_record_url", sa.String(length=1000), nullable=True))
            batch.add_column(sa.Column("officers", sa.JSON(), nullable=False, server_default="[]"))

    op.create_table(
        "oh_business_entities",
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
        op.f("ix_oh_business_entities_normalized_name"),
        "oh_business_entities",
        ["normalized_name"],
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_oh_business_entities_normalized_name"), table_name="oh_business_entities")
    op.drop_table("oh_business_entities")
    for table in reversed(TABLES):
        with op.batch_alter_table(table) as batch:
            batch.drop_column("officers")
            batch.drop_column("source_record_url")
            batch.drop_column("jurisdiction")
            batch.drop_column("mailing_address")
    with op.batch_alter_table("business_registrations") as batch:
        batch.drop_column("source_record_url")
        batch.drop_column("jurisdiction")
        batch.drop_column("mailing_address")
