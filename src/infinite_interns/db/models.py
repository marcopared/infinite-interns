"""SQLAlchemy rows for InfiniteInterns application state."""

from datetime import datetime
from typing import Any

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class RunRow(Base):
    __tablename__ = "runs"

    run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    repo: Mapped[str] = mapped_column(Text, nullable=False)
    base_commit: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    baseline_ref: Mapped[str | None] = mapped_column(Text)


class SpecVersionRow(Base):
    __tablename__ = "spec_versions"

    run_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("ii.runs.run_id", ondelete="CASCADE"), primary_key=True
    )
    version: Mapped[int] = mapped_column(Integer, primary_key=True)
    artifact_ref: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RequirementRow(Base):
    __tablename__ = "requirements"

    run_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("ii.runs.run_id", ondelete="CASCADE"), primary_key=True
    )
    requirement_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    criticality: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)


class TaskRow(Base):
    __tablename__ = "tasks"

    run_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("ii.runs.run_id", ondelete="CASCADE"), primary_key=True
    )
    task_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    risk: Mapped[str] = mapped_column(String(32), nullable=False)
    lease_owner: Mapped[str | None] = mapped_column(String(128))
    lease_epoch: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class TaskDependencyRow(Base):
    __tablename__ = "task_dependencies"
    __table_args__ = (
        ForeignKeyConstraint(
            ["run_id", "upstream_task_id"],
            ["ii.tasks.run_id", "ii.tasks.task_id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["run_id", "downstream_task_id"],
            ["ii.tasks.run_id", "ii.tasks.task_id"],
            ondelete="CASCADE",
        ),
    )

    run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    upstream_task_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    downstream_task_id: Mapped[str] = mapped_column(String(64), primary_key=True)


class AttemptRow(Base):
    __tablename__ = "attempts"
    __table_args__ = (
        ForeignKeyConstraint(
            ["run_id", "task_id"],
            ["ii.tasks.run_id", "ii.tasks.task_id"],
            ondelete="CASCADE",
        ),
    )

    attempt_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(64), nullable=False)
    task_id: Mapped[str] = mapped_column(String(64), nullable=False)
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class EvidenceRow(Base):
    __tablename__ = "evidence"
    __table_args__ = (
        ForeignKeyConstraint(
            ["run_id", "requirement_id"],
            ["ii.requirements.run_id", "ii.requirements.requirement_id"],
            ondelete="CASCADE",
        ),
        UniqueConstraint(
            "run_id",
            "requirement_id",
            "gate_id",
            "commit_sha",
            "environment_hash",
            "verifier_version",
            name="uq_evidence_identity",
        ),
    )

    evidence_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(64), nullable=False)
    requirement_id: Mapped[str] = mapped_column(String(64), nullable=False)
    gate_id: Mapped[str] = mapped_column(String(128), nullable=False)
    result: Mapped[str] = mapped_column(String(32), nullable=False)
    commit_sha: Mapped[str] = mapped_column(String(64), nullable=False)
    environment_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    producer: Mapped[str] = mapped_column(String(128), nullable=False)
    verifier_version: Mapped[str] = mapped_column(String(128), nullable=False)
    artifact_uri: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ReviewFindingRow(Base):
    __tablename__ = "review_findings"

    finding_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("ii.runs.run_id", ondelete="CASCADE"), nullable=False
    )
    requirement_id: Mapped[str | None] = mapped_column(String(64))
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class EventRow(Base):
    __tablename__ = "events"

    event_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("ii.runs.run_id", ondelete="CASCADE"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(64))
    entity_id: Mapped[str | None] = mapped_column(String(64))
    data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class DeploymentRow(Base):
    __tablename__ = "deployments"

    deployment_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("ii.runs.run_id", ondelete="CASCADE"), nullable=False
    )
    commit_sha: Mapped[str] = mapped_column(String(64), nullable=False)
    environment_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    url: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class BudgetRow(Base):
    __tablename__ = "budgets"

    run_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("ii.runs.run_id", ondelete="CASCADE"), primary_key=True
    )
    soft_model_usd: Mapped[float] = mapped_column(Float, nullable=False)
    hard_model_usd: Mapped[float] = mapped_column(Float, nullable=False)
    spend_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    deadline_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
