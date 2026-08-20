"""Add durable baseline artifact reference to runs.

Revision ID: 0004_run_baseline_ref
Revises: 0003_integration_state
Create Date: 2026-08-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_run_baseline_ref"
down_revision: str | None = "0003_integration_state"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("runs", sa.Column("baseline_ref", sa.Text(), nullable=True), schema="ii")


def downgrade() -> None:
    op.drop_column("runs", "baseline_ref", schema="ii")
