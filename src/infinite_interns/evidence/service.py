"""Requirement-level status derived only from current mandatory evidence."""

from collections.abc import Iterable

from infinite_interns.domain.enums import EvidenceResult, RequirementStatus
from infinite_interns.domain.models import EvidenceRecord

from .models import GateRequirement, ReleasePolicy


class EvidenceService:
    @staticmethod
    def requirement_status(
        requirement_id: str,
        policy: ReleasePolicy,
        evidence: Iterable[EvidenceRecord],
        *,
        current_commit: str,
        environment_hash: str,
    ) -> RequirementStatus:
        required_gates = tuple(
            gate
            for gate in policy.gates
            if gate.mandatory and gate.requirement_id == requirement_id
        )
        if not required_gates:
            return RequirementStatus.UNVERIFIED

        records = tuple(evidence)
        missing = False
        blocked = False
        unstable = False

        for gate in required_gates:
            current = tuple(
                record
                for record in records
                if _matches_gate(record, gate)
                and record.commit_sha == current_commit
                and record.environment_hash == environment_hash
            )
            if not current:
                missing = True
                continue

            results = {record.result for record in current}
            if EvidenceResult.FAIL in results:
                return RequirementStatus.FAILED
            if EvidenceResult.BLOCKED in results or EvidenceResult.INFRA_ERROR in results:
                blocked = True
            if EvidenceResult.UNSTABLE in results:
                unstable = True

        if blocked:
            return RequirementStatus.BLOCKED
        if unstable:
            return RequirementStatus.UNSTABLE
        if missing:
            return RequirementStatus.UNVERIFIED
        return RequirementStatus.VERIFIED


def _matches_gate(record: EvidenceRecord, gate: GateRequirement) -> bool:
    return record.gate_id == gate.gate_id and record.requirement_id == gate.requirement_id
