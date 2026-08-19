from datetime import UTC, datetime

import pytest

from infinite_interns.domain.enums import EvidenceResult
from infinite_interns.domain.models import EvidenceRecord
from infinite_interns.evidence.models import EvaluationStatus, GateRequirement, ReleasePolicy
from infinite_interns.evidence.predicate import ReleasePredicate


def evidence(
    evidence_id: str,
    result: EvidenceResult,
    *,
    gate_id: str = "ACC-1",
    requirement_id: str = "REQ-1",
    commit_sha: str = "abc",
    environment_hash: str = "env",
) -> EvidenceRecord:
    return EvidenceRecord(
        evidence_id=evidence_id,
        run_id="run_1",
        requirement_id=requirement_id,
        gate_id=gate_id,
        result=result,
        commit_sha=commit_sha,
        environment_hash=environment_hash,
        producer="pytest",
        verifier_version="1",
        created_at=datetime.now(UTC),
    )


def policy() -> ReleasePolicy:
    return ReleasePolicy(
        gates=(GateRequirement(gate_id="ACC-1", mandatory=True, requirement_id="REQ-1"),)
    )


@pytest.mark.parametrize(
    ("bad_result", "expected_status"),
    [
        (EvidenceResult.FAIL, EvaluationStatus.FAIL),
        (EvidenceResult.BLOCKED, EvaluationStatus.BLOCKED),
        (EvidenceResult.UNSTABLE, EvaluationStatus.UNSTABLE),
        (EvidenceResult.INFRA_ERROR, EvaluationStatus.BLOCKED),
    ],
)
def test_bad_mandatory_gate_prevents_pass(
    bad_result: EvidenceResult,
    expected_status: EvaluationStatus,
) -> None:
    evaluation = ReleasePredicate.evaluate(
        policy(),
        [evidence("ev_bad", bad_result)],
        current_commit="abc",
        environment_hash="env",
    )
    assert evaluation.status is expected_status
    assert evaluation.failing_gate_ids == ("ACC-1",)


def test_missing_mandatory_gate_fails() -> None:
    evaluation = ReleasePredicate.evaluate(
        policy(),
        [],
        current_commit="abc",
        environment_hash="env",
    )
    assert evaluation.status is EvaluationStatus.FAIL
    assert evaluation.failing_gate_ids == ("ACC-1",)


def test_stale_commit_prevents_pass() -> None:
    evaluation = ReleasePredicate.evaluate(
        policy(),
        [evidence("ev_old", EvidenceResult.PASS, commit_sha="old")],
        current_commit="abc",
        environment_hash="env",
    )
    assert evaluation.status is not EvaluationStatus.PASS
    assert evaluation.stale_evidence_ids == ("ev_old",)


def test_only_all_current_mandatory_gates_pass() -> None:
    evaluation = ReleasePredicate.evaluate(
        policy(),
        [evidence("ev_pass", EvidenceResult.PASS)],
        current_commit="abc",
        environment_hash="env",
    )
    assert evaluation.status is EvaluationStatus.PASS
    assert evaluation.failing_gate_ids == ()


def test_retry_cannot_wash_current_failure_into_pass() -> None:
    evaluation = ReleasePredicate.evaluate(
        policy(),
        [
            evidence("ev_fail", EvidenceResult.FAIL),
            evidence("ev_pass", EvidenceResult.PASS),
        ],
        current_commit="abc",
        environment_hash="env",
    )
    assert evaluation.status is EvaluationStatus.FAIL
