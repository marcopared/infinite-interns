"""Typed contract between the factory control plane and executor daemon."""

from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictExecutionModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ExecutionStatus(StrEnum):
    CREATED = "created"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    TERMINATED = "terminated"


class ExecutionRequest(StrictExecutionModel):
    operation_key: str
    run_id: str
    task_id: str
    attempt_id: str
    lease_epoch: int = Field(ge=1)
    worktree_path: str
    image: str
    argv: tuple[str, ...]
    artifact_path: str
    environment_names: tuple[str, ...] = ()
    cpu_limit: float = Field(gt=0)
    memory_limit_mb: int = Field(gt=0)
    network_profile: str

    @model_validator(mode="after")
    def validate_operation_key(self) -> "ExecutionRequest":
        prefix = f"{self.run_id}:{self.task_id}:{self.attempt_id}:"
        if not self.operation_key.startswith(prefix) or self.operation_key == prefix:
            raise ValueError("operation_key must be scoped to run/task/attempt and name an operation")
        if not self.argv:
            raise ValueError("argv must be non-empty")
        return self


class ExecutionHandle(StrictExecutionModel):
    execution_id: str
    operation_key: str
    status: ExecutionStatus


class ExecutionBackend(Protocol):
    async def create(self, request: ExecutionRequest) -> ExecutionHandle: ...

    async def status(self, handle: ExecutionHandle) -> ExecutionStatus: ...

    async def terminate(self, handle: ExecutionHandle) -> None: ...
