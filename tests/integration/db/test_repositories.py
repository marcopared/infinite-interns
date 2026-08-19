import os
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from infinite_interns.db.engine import create_engine, create_session_factory
from infinite_interns.db.repositories import (
    EvidenceRepository,
    RequirementRepository,
    RunRepository,
)
from infinite_interns.domain.enums import EvidenceResult, RequirementStatus, RiskClass, RunStatus
from infinite_interns.domain.models import EvidenceRecord, RequirementRecord, RunRecord


@pytest.mark.asyncio
async def test_requirement_and_evidence_round_trip() -> None:
    database_url = os.environ["INFINITE_INTERNS_DATABASE_URL"]
    engine = create_engine(database_url)
    sessions = create_session_factory(engine)

    run_id = f"run_{uuid4().hex}"
    now = datetime.now(UTC)
    run = RunRecord(
        run_id=run_id,
        repo="fixture",
        base_commit="abc123",
        status=RunStatus.CREATED,
        started_at=now,
    )
    requirement = RequirementRecord(
        requirement_id="REQ-1",
        run_id=run_id,
        text="Persist evidence",
        criticality=RiskClass.HIGH,
        status=RequirementStatus.UNVERIFIED,
    )
    evidence = EvidenceRecord(
        evidence_id=f"ev_{uuid4().hex}",
        run_id=run_id,
        requirement_id="REQ-1",
        gate_id="ACC-1",
        result=EvidenceResult.PASS,
        commit_sha="abc123",
        environment_hash="env123",
        producer="pytest",
        verifier_version="1",
        created_at=now,
    )

    try:
        async with sessions() as session:
            await RunRepository(session).add(run)
            await RequirementRepository(session).add(requirement)
            await EvidenceRepository(session).add(evidence)
            await session.commit()

        async with sessions() as session:
            stored_run = await RunRepository(session).get(run_id)
            stored_requirement = await RequirementRepository(session).get(run_id, "REQ-1")
            stored_evidence = await EvidenceRepository(session).for_requirement(run_id, "REQ-1")

        assert stored_run == run
        assert stored_requirement == requirement
        assert stored_evidence == [evidence]
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_requirement_cannot_be_inserted_as_verified() -> None:
    database_url = os.environ["INFINITE_INTERNS_DATABASE_URL"]
    engine = create_engine(database_url)
    sessions = create_session_factory(engine)
    run_id = f"run_{uuid4().hex}"

    try:
        async with sessions() as session:
            await RunRepository(session).add(
                RunRecord(
                    run_id=run_id,
                    repo="fixture",
                    base_commit="abc123",
                    status=RunStatus.CREATED,
                    started_at=datetime.now(UTC),
                )
            )
            with pytest.raises(ValueError, match="UNVERIFIED"):
                await RequirementRepository(session).add(
                    RequirementRecord(
                        requirement_id="REQ-verified",
                        run_id=run_id,
                        text="Cannot self-verify",
                        criticality=RiskClass.CRITICAL,
                        status=RequirementStatus.VERIFIED,
                    )
                )
    finally:
        await engine.dispose()
