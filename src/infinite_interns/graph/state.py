"""Compact durable state carried by the parent factory graph."""

from pydantic import BaseModel, ConfigDict, Field


class FactoryState(BaseModel):
    """Small orchestration state containing references and decisions, never heavy artifacts."""

    model_config = ConfigDict(extra="forbid")

    run_id: str
    baseline_ref: str | None = None
    spec_version: str | None = None
    requirement_ids: list[str] = Field(default_factory=list)
    ready_task_ids: list[str] = Field(default_factory=list)
    running_task_ids: list[str] = Field(default_factory=list)
    passed_task_ids: list[str] = Field(default_factory=list)
    failed_task_ids: list[str] = Field(default_factory=list)
    blocked_task_ids: list[str] = Field(default_factory=list)
    current_commit: str = ""
    last_green_commit: str = ""
    failing_gate_ids: list[str] = Field(default_factory=list)
    convergence_iteration: int = 0
    deployment_ref: str | None = None
    spend_usd: float = 0.0
    elapsed_seconds: int = 0
    escalation_level: int = 0
