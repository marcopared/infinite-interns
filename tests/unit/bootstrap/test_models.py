from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from infinite_interns.bootstrap.models import (
    BaselineFailure,
    BaselineSummary,
    CommandKind,
    DetectedCommand,
    GuidanceRef,
    RepositoryKind,
)


def test_command_argv_must_be_nonempty() -> None:
    with pytest.raises(ValidationError):
        DetectedCommand(kind=CommandKind.BUILD, argv=(), source="config", confidence=1.0)


def test_command_confidence_is_bounded() -> None:
    with pytest.raises(ValidationError):
        DetectedCommand(
            kind=CommandKind.BUILD,
            argv=("uv", "run", "python", "-m", "build"),
            source="detector",
            confidence=1.1,
        )


def test_baseline_failure_has_preexisting_commit_provenance() -> None:
    failure = BaselineFailure(
        failure_id="unit:deadbeef",
        command_kind=CommandKind.UNIT,
        exit_code=1,
        summary="one test failed",
        artifact_uri="artifact://runs/run-1/baseline/unit-deadbeef",
        base_commit="abc123",
        pre_existing=True,
    )
    assert failure.pre_existing is True
    assert failure.base_commit == "abc123"


def test_guidance_ref_is_repository_content_with_hashes() -> None:
    guidance = GuidanceRef(
        path="AGENTS.md",
        commit_sha="abc123",
        content_sha256="0" * 64,
    )
    assert guidance.trust_label == "REPOSITORY_CONTENT"


def test_baseline_summary_is_frozen() -> None:
    summary = BaselineSummary(
        repo_kind=RepositoryKind.GREENFIELD,
        base_commit="abc123",
        default_branch="main",
        generated_at=datetime.now(UTC),
    )
    with pytest.raises(ValidationError):
        summary.base_commit = "changed"  # type: ignore[misc]
