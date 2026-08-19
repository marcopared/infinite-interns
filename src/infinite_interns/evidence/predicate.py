"""Pure release evaluation over immutable evidence."""

from collections.abc import Iterable

from infinite_interns.domain.enums import EvidenceResult
from infinite_interns.domain.models import EvidenceRecord

from .models import (
    EvaluationStatus,
    GateRequirement,
    ReleaseEvaluation,
    ReleasePolicy,
)


class ReleasePredicate:
    @staticmethod
    def evaluate(
        policy: ReleasePolicy,
        evidence: Iterable[EvidenceRecord],
        *,
        current_commit: str,
        environment_hash: str,
    ) -> ReleaseEvaluation:
        evidence_records = tuple(evidence)
        failing: set[str] = set()
        stale: set[str] = set()
        statuses: list[EvaluationStatus] = []

        for gate in policy.gates:
            matching = tuple(
                record for record in evidence_records if _matches_gate(record, gate)
            )
            stale.update(
                record.evidence_id
                for record in matching
                if record.commit_sha != current_commit
                or record.environment_hash != environment_hash
            )
            if not gate.mandatory:
                continue

            current = tuple(
                record
                for record in matching
                if record.commit_sha == current_commit
                and record.environment_hash == environment_hash
            )
            gate_status = _mandatory_gate_status(current)
            if gate_status is not EvaluationStatus.PASS:
                failing.add(gate.gate_id)
            statuses.append(gate_status)

        status = _aggregate_status(statuses)
        return ReleaseEvaluation(
            status=status,
            failing_gate_ids=tuple(sorted(failing)),
            stale_evidence_ids=tuple(sorted(stale)),
        )


def _matches_gate(record: EvidenceRecord, gate: GateRequirement) -> bool:
    if record.gate_id != gate.gate_id:
        return False
    return gate.requirement_id is None or record.requirement_id == gate.requirement_id


def _mandatory_gate_status(records: tuple[EvidenceRecord, ...]) -> EvaluationStatus:
    if not records:
        return EvaluationStatus.FAIL

    results = {record.result for record in records}
    if EvidenceResult.FAIL in results:
        return EvaluationStatus.FAIL
    if EvidenceResult.BLOCKED in results or EvidenceResult.INFRA_ERROR in results:
        return EvaluationStatus.BLOCKED
    if EvidenceResult.UNSTABLE in results:
        return EvaluationStatus.UNSTABLE
    if results == {EvidenceResult.PASS}:
        return EvaluationStatus.PASS
    return EvaluationStatus.FAIL


def _aggregate_status(statuses: list[EvaluationStatus]) -> EvaluationStatus:
    if EvaluationStatus.FAIL in statuses:
        return EvaluationStatus.FAIL
    if EvaluationStatus.BLOCKED in statuses:
        return EvaluationStatus.BLOCKED
    if EvaluationStatus.UNSTABLE in statuses:
        return EvaluationStatus.UNSTABLE
    return EvaluationStatus.PASS
