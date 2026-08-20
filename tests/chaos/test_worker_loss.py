import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from infinite_interns.db.engine import create_engine, create_session_factory
from infinite_interns.db.repositories import EventRepository, RunRepository, TaskRepository
from infinite_interns.domain.enums import RiskClass, RunStatus, TaskStatus
from infinite_interns.domain.models import RunRecord, TaskRecord
from infinite_interns.scheduler.leasing import LeaseService
from infinite_interns.scheduler.results import WorkerResultService


@pytest.mark.asyncio
async def test_replacement_epoch_rejects_crashed_workers_late_result() -> None:
    engine = create_engine(os.environ["INFINITE_INTERNS_DATABASE_URL"])
    sessions = create_session_factory(engine)
    run_id = f"run_{uuid4().hex}"
    now = datetime.now(UTC)
    try:
        async with sessions() as session:
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
                    task_id="TASK-1",
                    run_id=run_id,
                    title="recover me",
                    status=TaskStatus.READY,
                    risk=RiskClass.HIGH,
                )
            )
            await session.commit()

        async with sessions() as session:
            leases = LeaseService(session, run_id, lease_ttl=timedelta(seconds=90))
            first = await leases.claim_ready_task("worker-a", now)
            assert first is not None
            second = await leases.claim_ready_task("worker-b", now + timedelta(seconds=91))
            assert second is not None
            assert second.epoch > first.epoch

        async with sessions() as session:
            results = WorkerResultService(session, run_id)
            accepted_old = await results.accept(
                "TASK-1",
                first.epoch,
                TaskStatus.CANDIDATE,
                now + timedelta(seconds=92),
            )
            accepted_new = await results.accept(
                "TASK-1",
                second.epoch,
                TaskStatus.CANDIDATE,
                now + timedelta(seconds=92),
            )
            await session.commit()

        async with sessions() as session:
            task = await TaskRepository(session).get(run_id, "TASK-1")
            events = await EventRepository(session).for_run(run_id)

        assert not accepted_old
        assert accepted_new
        assert task is not None and task.status is TaskStatus.CANDIDATE
        assert any(event.event_type == "STALE_WORKER_WRITE_REJECTED" for event in events)
    finally:
        await engine.dispose()
