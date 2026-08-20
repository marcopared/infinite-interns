"""Strict contracts for repository bootstrap and baseline evidence."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class BootstrapModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class RepositoryKind(StrEnum):
    BROWNFIELD = "brownfield"
    GREENFIELD = "greenfield"


class CommandKind(StrEnum):
    INSTALL = "install"
    BUILD = "build"
    TYPECHECK = "typecheck"
    LINT = "lint"
    UNIT = "unit"
    INTEGRATION = "integration"
    START = "start"


class DetectedCommand(BootstrapModel):
    kind: CommandKind
    argv: tuple[str, ...] = Field(min_length=1)
    source: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)

    @field_validator("argv")
    @classmethod
    def validate_argv(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if any(not token or "\x00" in token for token in value):
            raise ValueError("command argv tokens must be non-empty and NUL-free")
        return value


class GuidanceRef(BootstrapModel):
    path: str = Field(min_length=1)
    commit_sha: str = Field(min_length=1)
    content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    trust_label: str = "REPOSITORY_CONTENT"

    @field_validator("trust_label")
    @classmethod
    def require_repository_content(cls, value: str) -> str:
        if value != "REPOSITORY_CONTENT":
            raise ValueError("repository guidance must retain REPOSITORY_CONTENT trust")
        return value


class BaselineFailure(BootstrapModel):
    failure_id: str = Field(min_length=1)
    command_kind: CommandKind
    exit_code: int
    summary: str = Field(min_length=1)
    artifact_uri: str = Field(min_length=1)
    base_commit: str = Field(min_length=1)
    pre_existing: bool = True

    @field_validator("pre_existing")
    @classmethod
    def require_preexisting(cls, value: bool) -> bool:
        if value is not True:
            raise ValueError("bootstrap failures must be marked pre-existing")
        return value


class BaselineSummary(BootstrapModel):
    repo_kind: RepositoryKind
    base_commit: str = Field(min_length=1)
    default_branch: str = Field(min_length=1)
    languages: tuple[str, ...] = ()
    package_managers: tuple[str, ...] = ()
    guidance_refs: tuple[GuidanceRef, ...] = ()
    commands: tuple[DetectedCommand, ...] = ()
    failures: tuple[BaselineFailure, ...] = ()
    architecture_hints: tuple[str, ...] = ()
    dependency_hints: tuple[str, ...] = ()
    generated_at: datetime

    @field_validator("generated_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("generated_at must be timezone-aware")
        return value
