"""index staging formation dates

Revision ID: c6f4a0e3b8d2
Revises: b5e3f9d2a7c1
Create Date: 2026-06-19
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "c6f4a0e3b8d2"
down_revision: str | None = "b5e3f9d2a7c1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = (
    "co_business_entities",
    "ct_business_entities",
    "or_business_entities",
    "oh_business_entities",
)


def upgrade() -> None:
    for table in TABLES:
        op.create_index(op.f(f"ix_{table}_formation_date"), table, ["formation_date"])


def downgrade() -> None:
    for table in reversed(TABLES):
        op.drop_index(op.f(f"ix_{table}_formation_date"), table_name=table)
