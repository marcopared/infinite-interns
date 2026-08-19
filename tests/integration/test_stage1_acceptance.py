from datetime import UTC, datetime
import os
from pathlib import Path
from uuid import uuid4

import pytest

from infinite_interns.artifacts.filesystem import FilesystemArtifactStore
from infinite_interns.db.engine import create_engine, create_session_factory
from infinite_interns.db.repositories import EvidenceRepository, RequirementRepository, RunRepository
from infinite_interns.domain.enums import EvidenceResult, RequirementStatus, RiskClass, RunStatus
from infinite_interns.domain.models import EvidenceRecord, RequirementRecord, RunRecord
from infinite_interns.evidence.models import EvaluationStatus, GateRequirement, ReleasePolicy
from infinite_interns.evidence.predicate import ReleasePredicate


@pytest.mark.asyncio
async def test_stage1_release_evidence_is_complete_current_and_commit_bound(tmp_path: Path) -> None:
    database_url = os.environ["INFINITE_INTERNS_DATABASE_URL"]
    engine = create_engine(database_url)
    sessions = create_session_factory(engine)
    run_id = f"run_{uuid4().hex}"
    now = datetime.now(UTC)
    current_commit = "abc123"

    policy = ReleasePolicy(
        gates=(
            GateRequirement(gate_id="ACC-1", mandatory=True, requirement_id="REQ-1"),
            GateRequirement(gate_id="ACC-2", mandatory=True, requirement_id="REQ-2"),
        )
    )
    store = FilesystemArtifactStore(tmp_path / "artifacts")
    policy_uri = store.put(
        run_id,
        "policies",
        "release-v1.json",
        policy.model_dump_json().encode(),
    )
    persisted_policy = ReleasePolicy.model_validate_json(store.get(policy_uri))

    run = RunRecord(
        run_id=run_id,
        repo="fixture",
        base_commit=current_commit,
        status=RunStatus.CREATED,
        started_at=now,
    )
    requirements = (
        RequirementRecord(
            requirement_id="REQ-1",
            run_id=run_id,
            text="First requirement",
            criticality=RiskClass.HIGH,
            status=RequirementStatus.UNVERIFIED,
        ),
        RequirementRecord(
            requirement_id="REQ-2",
            run_id=run_id,
            text="Second requirement",
            criticality=RiskClass.HIGH,
            status=RequirementStatus.UNVERIFIED,
        ),
    )

    try:
        async with sessions() as session:
            await RunRepository(session).add(run)
            requirement_repo = RequirementRepository(session)
            for requirement in requirements:
                await requirement_repo.add(requirement)
            evidence_repo = EvidenceRepository(session)
            await evidence_repo.add(
                _evidence("ev_1", run_id, "REQ-1", "ACC-1", current_commit, now)
            )
            await session.commit()

        async with sessions() as session:
            evidence_repo = EvidenceRepository(session)
            partial_evidence = [
                *await evidence_repo.for_requirement(run_id, "REQ-1"),
                *await evidence_repo.for_requirement(run_id, "REQ-2"),
            ]
        partial = ReleasePredicate.evaluate(
            persisted_policy,
            partial_evidence,
            current_commit=current_commit,
            environment_hash="env1",
        )
        assert partial.status is not EvaluationStatus.PASS
        assert partial.failing_gate_ids == ("ACC-2",)

        async with sessions() as session:
            await EvidenceRepository(session).add(
                _evidence("ev_2", run_id, "REQ-2", "ACC-2", current_commit, now)
            )
            await session.commit()

        async with sessions() as session:
            evidence_repo = EvidenceRepository(session)
            complete_evidence = [
                *await evidence_repo.for_requirement(run_id, "REQ-1"),
                *await evidence_repo.for_requirement(run_id, "REQ-2"),
            ]
        complete = ReleasePredicate.evaluate(
            persisted_policy,
            complete_evidence,
            current_commit=current_commit,
            environment_hash="env1",
        )
        assert complete.status is EvaluationStatus.PASS

        stale = ReleasePredicate.evaluate(
            persisted_policy,
            complete_evidence,
            current_commit="def456",
            environment_hash="env1",
        )
        assert stale.status is not EvaluationStatus.PASS
        assert set(stale.stale_evidence_ids) == {"ev_1", "ev_2"}
    finally:
        await engine.dispose()


def _evidence(
    evidence_id: str,
    run_id: str,
    requirement_id: str,
    gate_id: str,
    commit_sha: str,
    created_at: datetime,
) -> EvidenceRecord:
    return EvidenceRecord(
        evidence_id=evidence_id,
        run_id=run_id,
        requirement_id=requirement_id,
        gate_id=gate_id,
        result=EvidenceResult.PASS,
        commit_sha=commit_sha,
        environment_hash="env1",
        producer="pytest",
        verifier_version="1",
        created_at=created_at,
    )
