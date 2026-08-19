"""Add renewable task leases and fencing epochs.

Revision ID: 0002_task_leases
Revises: 0001_initial_control_plane
Create Date: 2026-08-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_task_leases"
down_revision: str | None = "0001_initial_control_plane"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("tasks", sa.Column("lease_owner", sa.String(length=128)), schema="ii")
    op.add_column(
        "tasks",
        sa.Column("lease_epoch", sa.Integer(), nullable=False, server_default="0"),
        schema="ii",
    )
    op.add_column(
        "tasks",
        sa.Column("lease_expires_at", sa.DateTime(timezone=True)),
        schema="ii",
    )
    op.create_index(
        "ix_tasks_claimable",
        "tasks",
        ["run_id", "status", "lease_expires_at", "task_id"],
        schema="ii",
    )


def downgrade() -> None:
    op.drop_index("ix_tasks_claimable", table_name="tasks", schema="ii")
    op.drop_column("tasks", "lease_expires_at", schema="ii")
    op.drop_column("tasks", "lease_epoch", schema="ii")
    op.drop_column("tasks", "lease_owner", schema="ii")
