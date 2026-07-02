"""index state registry updated timestamps

Revision ID: e1b7d4c9a8f3
Revises: d0a6c3e2f5b8
Create Date: 2026-06-30
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "e1b7d4c9a8f3"
down_revision: str | None = "d0a6c3e2f5b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = (
    "al_business_entities",
    "co_business_entities",
    "ct_business_entities",
    "fl_business_entities",
    "ga_business_entities",
    "ms_business_entities",
    "oh_business_entities",
    "or_business_entities",
    "tn_business_entities",
    "tx_business_entities",
    "va_business_entities",
)


def upgrade() -> None:
    for table in TABLES:
        op.create_index(f"ix_{table}_updated_at", table, ["updated_at"])


def downgrade() -> None:
    for table in reversed(TABLES):
        op.drop_index(f"ix_{table}_updated_at", table_name=table)
