"""Immutable models for deterministic evidence evaluation."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, model_validator


class StrictEvidenceModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class EvaluationStatus(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    BLOCKED = "blocked"
    UNSTABLE = "unstable"


class GateRequirement(StrictEvidenceModel):
    gate_id: str
    mandatory: bool = True
    requirement_id: str | None = None


class ReleasePolicy(StrictEvidenceModel):
    gates: tuple[GateRequirement, ...]

    @model_validator(mode="after")
    def validate_gate_policy(self) -> "ReleasePolicy":
        identities = [(gate.gate_id, gate.requirement_id) for gate in self.gates]
        if len(identities) != len(set(identities)):
            raise ValueError("release policy contains duplicate gate identity")
        if not any(gate.mandatory for gate in self.gates):
            raise ValueError("release policy requires at least one mandatory gate")
        return self


class ReleaseEvaluation(StrictEvidenceModel):
    status: EvaluationStatus
    failing_gate_ids: tuple[str, ...] = ()
    stale_evidence_ids: tuple[str, ...] = ()
