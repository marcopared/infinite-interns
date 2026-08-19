"""Authoritative status and classification enums for the control plane."""

from enum import StrEnum


class RunStatus(StrEnum):
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    FAILED = "failed"
    BLOCKED = "blocked"
    UNSTABLE = "unstable"
    PASS = "pass"
    DONE = "done"


class RequirementStatus(StrEnum):
    UNVERIFIED = "unverified"
    VERIFIED = "verified"
    FAILED = "failed"
    BLOCKED = "blocked"
    UNSTABLE = "unstable"


class TaskStatus(StrEnum):
    PLANNED = "planned"
    READY = "ready"
    CLAIMED = "claimed"
    RUNNING = "running"
    VERIFYING = "verifying"
    REVIEWING = "reviewing"
    REPAIR = "repair"
    CANDIDATE = "candidate"
    INTEGRATING = "integrating"
    VERIFIED = "verified"
    DONE = "done"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"
    SUPERSEDED = "superseded"


class EvidenceResult(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    BLOCKED = "blocked"
    UNSTABLE = "unstable"
    INFRA_ERROR = "infra_error"


class FailureClass(StrEnum):
    INFRA_TRANSIENT = "infra_transient"
    ENGINEERING_FAILURE = "engineering_failure"
    EXTERNAL_BLOCKER = "external_blocker"
    CONTROL_PLANE_FAILURE = "control_plane_failure"


class RiskClass(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
