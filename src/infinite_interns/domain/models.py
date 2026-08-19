"""Immutable domain records for deterministic factory state."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from .enums import EvidenceResult, RequirementStatus, RiskClass, RunStatus, TaskStatus
from .ids import EvidenceId, RequirementId, RunId, TaskId


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class EvidenceRecord(StrictModel):
    evidence_id: EvidenceId
    run_id: RunId
    requirement_id: RequirementId
    gate_id: str
    result: EvidenceResult
    commit_sha: str
    environment_hash: str
    producer: str
    verifier_version: str
    artifact_uri: str | None = None
    created_at: datetime


class RequirementRecord(StrictModel):
    requirement_id: RequirementId
    run_id: RunId
    text: str
    criticality: RiskClass
    status: RequirementStatus = RequirementStatus.UNVERIFIED


class TaskRecord(StrictModel):
    task_id: TaskId
    run_id: RunId
    title: str
    status: TaskStatus
    risk: RiskClass


class RunRecord(StrictModel):
    run_id: RunId
    repo: str
    base_commit: str
    status: RunStatus
    started_at: datetime
