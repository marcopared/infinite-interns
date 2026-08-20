import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from infinite_interns.db.engine import create_engine, create_session_factory
from infinite_interns.db.repositories import RunRepository, TaskRepository
from infinite_interns.domain.enums import RiskClass, RunStatus, TaskStatus
from infinite_interns.domain.models import RunRecord, TaskRecord
from infinite_interns.scheduler.leasing import LeaseService
from infinite_interns.scheduler.results import WorkerResultService


async def _seed_ready_task(run_id: str, task_id: str) -> None:
    engine = create_engine(os.environ["INFINITE_INTERNS_DATABASE_URL"])
    sessions = create_session_factory(engine)
    try:
        async with sessions() as session:
            now = datetime.now(UTC)
            await RunRepository(session).add(
                RunRecord(
                    run_id=run_id,
                    repo="fixture",
                    base_commit="abc",
                    status=RunStatus.RUNNING,
                    started_at=now,
                )
            )
            await TaskRepository(session).add(
                TaskRecord(
                    run_id=run_id,
                    task_id=task_id,
                    title="authority test",
                    status=TaskStatus.READY,
                    risk=RiskClass.HIGH,
                )
            )
            await session.commit()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_expired_unreclaimed_lease_cannot_publish_candidate() -> None:
    run_id = f"run_{uuid4().hex}"
    task_id = "TASK-EXPIRED"
    await _seed_ready_task(run_id, task_id)
    engine = create_engine(os.environ["INFINITE_INTERNS_DATABASE_URL"])
    sessions = create_session_factory(engine)
    now = datetime.now(UTC)

    try:
        async with sessions() as session:
            lease = await LeaseService(
                session,
                run_id,
                lease_ttl=timedelta(seconds=90),
            ).claim_ready_task("worker-a", now)
            assert lease is not None

        async with sessions() as session:
            accepted = await WorkerResultService(session, run_id).accept(
                task_id,
                lease.epoch,
                "a" * 40,
                now + timedelta(seconds=91),
            )
            await session.commit()

        async with sessions() as session:
            task = await TaskRepository(session).get(run_id, task_id)

        assert not accepted
        assert task is not None and task.status is TaskStatus.CLAIMED
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_worker_publication_requires_full_candidate_commit() -> None:
    run_id = f"run_{uuid4().hex}"
    task_id = "TASK-COMMIT"
    await _seed_ready_task(run_id, task_id)
    engine = create_engine(os.environ["INFINITE_INTERNS_DATABASE_URL"])
    sessions = create_session_factory(engine)
    now = datetime.now(UTC)

    try:
        async with sessions() as session:
            lease = await LeaseService(session, run_id).claim_ready_task("worker-a", now)
            assert lease is not None

        async with sessions() as session:
            with pytest.raises(ValueError, match="candidate commit"):
                await WorkerResultService(session, run_id).accept(
                    task_id,
                    lease.epoch,
                    "done",
                    now + timedelta(seconds=1),
                )
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_active_worker_can_only_publish_candidate_state() -> None:
    run_id = f"run_{uuid4().hex}"
    task_id = "TASK-CANDIDATE"
    await _seed_ready_task(run_id, task_id)
    engine = create_engine(os.environ["INFINITE_INTERNS_DATABASE_URL"])
    sessions = create_session_factory(engine)
    now = datetime.now(UTC)

    try:
        async with sessions() as session:
            lease = await LeaseService(session, run_id).claim_ready_task("worker-a", now)
            assert lease is not None

        async with sessions() as session:
            accepted = await WorkerResultService(session, run_id).accept(
                task_id,
                lease.epoch,
                "b" * 40,
                now + timedelta(seconds=1),
            )
            await session.commit()

        async with sessions() as session:
            task = await TaskRepository(session).get(run_id, task_id)

        assert accepted
        assert task is not None and task.status is TaskStatus.CANDIDATE
    finally:
        await engine.dispose()
