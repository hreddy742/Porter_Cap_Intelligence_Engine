"""add run idempotency/cache columns and webhook delivery tables

Revision ID: d4e8f1a3c6b9
Revises: b7d3f8a2c5e1
Create Date: 2026-07-03
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d4e8f1a3c6b9"
down_revision: str | None = "b7d3f8a2c5e1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("verification_runs", sa.Column("idempotency_key", sa.String(length=255), nullable=True))
    op.add_column("verification_runs", sa.Column("query_name", sa.String(length=500), nullable=True))
    op.add_column(
        "verification_runs", sa.Column("query_name_normalized", sa.String(length=500), nullable=True)
    )
    op.add_column("verification_runs", sa.Column("query_state", sa.String(length=2), nullable=True))
    op.create_index(
        "ix_verification_runs_idempotency_key",
        "verification_runs",
        ["idempotency_key"],
        unique=True,
    )
    op.create_index(
        "ix_verification_runs_query_name_normalized",
        "verification_runs",
        ["query_name_normalized"],
    )
    op.create_index("ix_verification_runs_query_state", "verification_runs", ["query_state"])

    op.create_table(
        "webhook_endpoints",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("url", sa.String(length=1000), nullable=False),
        sa.Column("secret", sa.String(length=100), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("created_by_email", sa.String(length=320), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "webhook_deliveries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("endpoint_id", sa.Uuid(), nullable=False),
        sa.Column("verification_run_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("response_code", sa.Integer(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["endpoint_id"], ["webhook_endpoints.id"]),
        sa.ForeignKeyConstraint(["verification_run_id"], ["verification_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "endpoint_id", "verification_run_id", name="uq_webhook_deliveries_endpoint_run"
        ),
    )
    op.create_index("ix_webhook_deliveries_endpoint_id", "webhook_deliveries", ["endpoint_id"])
    op.create_index(
        "ix_webhook_deliveries_verification_run_id", "webhook_deliveries", ["verification_run_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_webhook_deliveries_verification_run_id", table_name="webhook_deliveries")
    op.drop_index("ix_webhook_deliveries_endpoint_id", table_name="webhook_deliveries")
    op.drop_table("webhook_deliveries")
    op.drop_table("webhook_endpoints")

    op.drop_index("ix_verification_runs_query_state", table_name="verification_runs")
    op.drop_index("ix_verification_runs_query_name_normalized", table_name="verification_runs")
    op.drop_index("ix_verification_runs_idempotency_key", table_name="verification_runs")
    op.drop_column("verification_runs", "query_state")
    op.drop_column("verification_runs", "query_name_normalized")
    op.drop_column("verification_runs", "query_name")
    op.drop_column("verification_runs", "idempotency_key")
