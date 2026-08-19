from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from infinite_interns.domain.enums import EvidenceResult, RequirementStatus, RunStatus
from infinite_interns.domain.models import EvidenceRecord

EXPECTED_REQUIREMENT_STATUSES = {
    "unverified",
    "verified",
    "failed",
    "blocked",
    "unstable",
}


def test_requirement_status_has_exact_non_done_values() -> None:
    assert {member.value for member in RequirementStatus} == EXPECTED_REQUIREMENT_STATUSES


def test_run_status_has_no_intermediate_pass_state() -> None:
    assert "pass" not in {member.value for member in RunStatus}


def test_evidence_requires_commit_and_environment_hash() -> None:
    with pytest.raises(ValidationError):
        EvidenceRecord.model_validate(
            {
                "evidence_id": "ev_1",
                "run_id": "run_1",
                "requirement_id": "REQ-1",
                "gate_id": "ACC-1",
                "result": EvidenceResult.PASS,
                "producer": "pytest",
                "verifier_version": "1",
                "created_at": datetime.now(UTC),
            }
        )
