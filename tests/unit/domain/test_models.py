from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from infinite_interns.domain import enums, models


EXPECTED_REQUIREMENT_STATUSES = {
    "unverified",
    "verified",
    "failed",
    "blocked",
    "unstable",
}


def test_requirement_status_has_exact_non_done_values() -> None:
    requirement_status = getattr(enums, "RequirementStatus", None)
    assert requirement_status is not None
    assert {member.value for member in requirement_status} == EXPECTED_REQUIREMENT_STATUSES


def test_evidence_requires_commit_and_environment_hash() -> None:
    evidence_record = getattr(models, "EvidenceRecord", None)
    evidence_result = getattr(enums, "EvidenceResult", None)
    assert evidence_record is not None
    assert evidence_result is not None

    with pytest.raises(ValidationError):
        evidence_record(
            evidence_id="ev_1",
            run_id="run_1",
            requirement_id="REQ-1",
            gate_id="ACC-1",
            result=evidence_result.PASS,
            producer="pytest",
            verifier_version="1",
            created_at=datetime.now(UTC),
        )
