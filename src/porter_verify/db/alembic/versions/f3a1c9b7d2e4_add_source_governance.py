"""add source governance and quality metrics

Revision ID: f3a1c9b7d2e4
Revises: e99621b7f97c
Create Date: 2026-06-18
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f3a1c9b7d2e4"
down_revision: str | None = "e99621b7f97c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "source_policies",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("acquisition_method", sa.String(length=30), nullable=False),
        sa.Column("legal_review_status", sa.String(length=20), nullable=False),
        sa.Column("allowed_purposes", sa.JSON(), nullable=False),
        sa.Column("retention_days", sa.Integer(), nullable=True),
        sa.Column("freshness_sla_hours", sa.Integer(), nullable=True),
        sa.Column("terms_url", sa.String(length=1000), nullable=True),
        sa.Column("owner", sa.String(length=320), nullable=True),
        sa.Column("approved_by", sa.String(length=320), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["source_id"], ["source_registry.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_id"),
    )
    op.create_table(
        "source_quality_daily",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("metric_date", sa.Date(), nullable=False),
        sa.Column("request_count", sa.Integer(), nullable=False),
        sa.Column("success_count", sa.Integer(), nullable=False),
        sa.Column("record_count", sa.Integer(), nullable=False),
        sa.Column("avg_latency_ms", sa.Integer(), nullable=True),
        sa.Column("freshness_pass_rate", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column("estimated_cost", sa.Numeric(precision=12, scale=3), nullable=False),
        sa.Column("schema_drift_detected", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["source_id"], ["source_registry.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_id", "metric_date", name="source_quality_day"),
    )


def downgrade() -> None:
    op.drop_table("source_quality_daily")
    op.drop_table("source_policies")
