"""Add durable current/last-green integration anchors.

Revision ID: 0003_integration_state
Revises: 0002_task_leases
Create Date: 2026-08-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_integration_state"
down_revision: str | None = "0002_task_leases"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "integration_state",
        sa.Column(
            "run_id",
            sa.String(length=64),
            sa.ForeignKey("ii.runs.run_id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("current_commit", sa.String(length=64), nullable=False),
        sa.Column("last_green_commit", sa.String(length=64), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        schema="ii",
    )


def downgrade() -> None:
    op.drop_table("integration_state", schema="ii")
