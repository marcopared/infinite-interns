from datetime import UTC, datetime

from infinite_interns.domain.enums import EvidenceResult, RequirementStatus
from infinite_interns.domain.models import EvidenceRecord
from infinite_interns.evidence.models import GateRequirement, ReleasePolicy
from infinite_interns.evidence.service import EvidenceService


def record(evidence_id: str, result: EvidenceResult, *, gate_id: str = "ACC-1") -> EvidenceRecord:
    return EvidenceRecord(
        evidence_id=evidence_id,
        run_id="run_1",
        requirement_id="REQ-1",
        gate_id=gate_id,
        result=result,
        commit_sha="abc",
        environment_hash="env",
        producer="pytest",
        verifier_version="1",
        created_at=datetime.now(UTC),
    )


def requirement_policy() -> ReleasePolicy:
    return ReleasePolicy(
        gates=(
            GateRequirement(gate_id="ACC-1", mandatory=True, requirement_id="REQ-1"),
            GateRequirement(gate_id="INT-1", mandatory=True, requirement_id="REQ-1"),
        )
    )


def test_requirement_is_unverified_when_mandatory_evidence_is_missing() -> None:
    status = EvidenceService.requirement_status(
        "REQ-1",
        requirement_policy(),
        [record("ev_1", EvidenceResult.PASS)],
        current_commit="abc",
        environment_hash="env",
    )
    assert status is RequirementStatus.UNVERIFIED


def test_requirement_verified_only_when_all_current_mandatory_gates_pass() -> None:
    status = EvidenceService.requirement_status(
        "REQ-1",
        requirement_policy(),
        [
            record("ev_1", EvidenceResult.PASS),
            record("ev_2", EvidenceResult.PASS, gate_id="INT-1"),
        ],
        current_commit="abc",
        environment_hash="env",
    )
    assert status is RequirementStatus.VERIFIED


def test_requirement_failure_is_not_washed_by_retry_pass() -> None:
    status = EvidenceService.requirement_status(
        "REQ-1",
        requirement_policy(),
        [
            record("ev_fail", EvidenceResult.FAIL),
            record("ev_pass", EvidenceResult.PASS),
            record("ev_int", EvidenceResult.PASS, gate_id="INT-1"),
        ],
        current_commit="abc",
        environment_hash="env",
    )
    assert status is RequirementStatus.FAILED
