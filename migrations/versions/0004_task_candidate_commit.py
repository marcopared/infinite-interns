"""Bind task candidates to exact Git commits.

Revision ID: 0004_task_candidate_commit
Revises: 0003_integration_state
Create Date: 2026-08-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_task_candidate_commit"
down_revision: str | None = "0003_integration_state"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "tasks",
        sa.Column("candidate_commit", sa.String(length=64), nullable=True),
        schema="ii",
    )


def downgrade() -> None:
    op.drop_column("tasks", "candidate_commit", schema="ii")
