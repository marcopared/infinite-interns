"""Create InfiniteInterns application control-plane schema.

Revision ID: 0001_initial_control_plane
Revises:
Create Date: 2026-08-18
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial_control_plane"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(sa.text("CREATE SCHEMA IF NOT EXISTS ii"))

    op.create_table(
        "runs",
        sa.Column("run_id", sa.String(length=64), primary_key=True),
        sa.Column("repo", sa.Text(), nullable=False),
        sa.Column("base_commit", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        schema="ii",
    )

    op.create_table(
        "spec_versions",
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("artifact_ref", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["ii.runs.run_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("run_id", "version"),
        schema="ii",
    )

    op.create_table(
        "requirements",
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("requirement_id", sa.String(length=64), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("criticality", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["ii.runs.run_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("run_id", "requirement_id"),
        schema="ii",
    )

    op.create_table(
        "tasks",
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("task_id", sa.String(length=64), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("risk", sa.String(length=32), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["ii.runs.run_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("run_id", "task_id"),
        schema="ii",
    )

    op.create_table(
        "task_dependencies",
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("upstream_task_id", sa.String(length=64), nullable=False),
        sa.Column("downstream_task_id", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(
            ["run_id", "upstream_task_id"],
            ["ii.tasks.run_id", "ii.tasks.task_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["run_id", "downstream_task_id"],
            ["ii.tasks.run_id", "ii.tasks.task_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("run_id", "upstream_task_id", "downstream_task_id"),
        schema="ii",
    )

    op.create_table(
        "attempts",
        sa.Column("attempt_id", sa.String(length=64), primary_key=True),
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("task_id", sa.String(length=64), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column(
            "details",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(
            ["run_id", "task_id"],
            ["ii.tasks.run_id", "ii.tasks.task_id"],
            ondelete="CASCADE",
        ),
        schema="ii",
    )

    op.create_table(
        "evidence",
        sa.Column("evidence_id", sa.String(length=64), primary_key=True),
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("requirement_id", sa.String(length=64), nullable=False),
        sa.Column("gate_id", sa.String(length=128), nullable=False),
        sa.Column("result", sa.String(length=32), nullable=False),
        sa.Column("commit_sha", sa.String(length=64), nullable=False),
        sa.Column("environment_hash", sa.String(length=128), nullable=False),
        sa.Column("producer", sa.String(length=128), nullable=False),
        sa.Column("verifier_version", sa.String(length=128), nullable=False),
        sa.Column("artifact_uri", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["run_id", "requirement_id"],
            ["ii.requirements.run_id", "ii.requirements.requirement_id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "run_id",
            "requirement_id",
            "gate_id",
            "commit_sha",
            "environment_hash",
            "verifier_version",
            name="uq_evidence_identity",
        ),
        schema="ii",
    )

    op.create_table(
        "review_findings",
        sa.Column("finding_id", sa.String(length=64), primary_key=True),
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("requirement_id", sa.String(length=64)),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["ii.runs.run_id"], ondelete="CASCADE"),
        schema="ii",
    )

    op.create_table(
        "events",
        sa.Column("event_id", sa.String(length=64), primary_key=True),
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("entity_type", sa.String(length=64)),
        sa.Column("entity_id", sa.String(length=64)),
        sa.Column(
            "data",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["ii.runs.run_id"], ondelete="CASCADE"),
        schema="ii",
    )

    op.create_table(
        "deployments",
        sa.Column("deployment_id", sa.String(length=64), primary_key=True),
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("commit_sha", sa.String(length=64), nullable=False),
        sa.Column("environment_hash", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("url", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["ii.runs.run_id"], ondelete="CASCADE"),
        schema="ii",
    )

    op.create_table(
        "budgets",
        sa.Column("run_id", sa.String(length=64), primary_key=True),
        sa.Column("soft_model_usd", sa.Float(), nullable=False),
        sa.Column("hard_model_usd", sa.Float(), nullable=False),
        sa.Column("spend_usd", sa.Float(), nullable=False, server_default="0"),
        sa.Column("deadline_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["ii.runs.run_id"], ondelete="CASCADE"),
        schema="ii",
    )


def downgrade() -> None:
    for table in (
        "budgets",
        "deployments",
        "events",
        "review_findings",
        "evidence",
        "attempts",
        "task_dependencies",
        "tasks",
        "requirements",
        "spec_versions",
        "runs",
    ):
        op.drop_table(table, schema="ii")
    op.execute(sa.text("DROP SCHEMA IF EXISTS ii"))
