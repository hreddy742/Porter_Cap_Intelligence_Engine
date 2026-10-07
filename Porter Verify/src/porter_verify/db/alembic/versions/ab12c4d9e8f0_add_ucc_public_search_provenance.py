"""Add UCC public-search provenance fields.

Revision ID: ab12c4d9e8f0
Revises: f2c8e5a1b9d4
Create Date: 2026-07-01 20:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "ab12c4d9e8f0"
down_revision = "f2c8e5a1b9d4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("ucc_filings", sa.Column("acquisition_method", sa.String(length=30)))
    op.add_column("ucc_filings", sa.Column("search_query", sa.String(length=500)))
    op.add_column("ucc_filings", sa.Column("match_confidence", sa.Integer()))


def downgrade() -> None:
    op.drop_column("ucc_filings", "match_confidence")
    op.drop_column("ucc_filings", "search_query")
    op.drop_column("ucc_filings", "acquisition_method")
