import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import update

from infinite_interns.db.engine import create_engine, create_session_factory
from infinite_interns.db.models import TaskRow
from infinite_interns.db.repositories import RunRepository, TaskRepository
from infinite_interns.domain.enums import RiskClass, RunStatus, TaskStatus
from infinite_interns.domain.models import RunRecord, TaskRecord
from infinite_interns.scheduler.leasing import LeaseService, StaleLeaseError


async def _seed_ready_task(run_id: str, task_id: str) -> None:
    engine = create_engine(os.environ["INFINITE_INTERNS_DATABASE_URL"])
    sessions = create_session_factory(engine)
    try:
        async with sessions() as session:
            await RunRepository(session).add(
                RunRecord(
                    run_id=run_id,
                    repo="fixture",
                    base_commit="abc",
                    status=RunStatus.RUNNING,
                    started_at=datetime.now(UTC),
                )
            )
            await TaskRepository(session).add(
                TaskRecord(
                    run_id=run_id,
                    task_id=task_id,
                    title="lease me",
                    status=TaskStatus.READY,
                    risk=RiskClass.MEDIUM,
                )
            )
            await session.commit()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_only_one_concurrent_claim_wins() -> None:
    run_id = f"run_{uuid4().hex}"
    await _seed_ready_task(run_id, "TASK-1")
    database_url = os.environ["INFINITE_INTERNS_DATABASE_URL"]
    engine = create_engine(database_url)
    sessions = create_session_factory(engine)
    now = datetime.now(UTC)

    try:
        async with sessions() as session_a, sessions() as session_b:
            service_a = LeaseService(session_a, run_id, lease_ttl=timedelta(seconds=90))
            service_b = LeaseService(session_b, run_id, lease_ttl=timedelta(seconds=90))
            lease_a = await service_a.claim_ready_task("worker-a", now)
            lease_b = await service_b.claim_ready_task("worker-b", now)

        assert lease_a is not None
        assert lease_a.task_id == "TASK-1"
        assert lease_a.epoch == 1
        assert lease_b is None
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_renew_keeps_epoch_and_extends_expiry() -> None:
    run_id = f"run_{uuid4().hex}"
    await _seed_ready_task(run_id, "TASK-1")
    engine = create_engine(os.environ["INFINITE_INTERNS_DATABASE_URL"])
    sessions = create_session_factory(engine)
    now = datetime.now(UTC)

    try:
        async with sessions() as session:
            service = LeaseService(session, run_id, lease_ttl=timedelta(seconds=90))
            lease = await service.claim_ready_task("worker-a", now)
            assert lease is not None
            renewed = await service.renew("TASK-1", "worker-a", lease.epoch, now + timedelta(seconds=30))

        assert renewed.epoch == lease.epoch
        assert renewed.expires_at > lease.expires_at
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_expired_lease_cannot_be_revived_by_backdating_renewal_timestamp() -> None:
    run_id = f"run_{uuid4().hex}"
    await _seed_ready_task(run_id, "TASK-1")
    engine = create_engine(os.environ["INFINITE_INTERNS_DATABASE_URL"])
    sessions = create_session_factory(engine)
    now = datetime.now(UTC)

    try:
        async with sessions() as session:
            service = LeaseService(session, run_id, lease_ttl=timedelta(seconds=90))
            lease = await service.claim_ready_task("worker-a", now)
            assert lease is not None
            await session.execute(
                update(TaskRow)
                .where(TaskRow.run_id == run_id, TaskRow.task_id == "TASK-1")
                .values(lease_expires_at=now - timedelta(seconds=1))
            )
            await session.commit()

        async with sessions() as session:
            service = LeaseService(session, run_id, lease_ttl=timedelta(seconds=90))
            with pytest.raises(StaleLeaseError):
                await service.renew(
                    "TASK-1",
                    "worker-a",
                    lease.epoch,
                    now - timedelta(minutes=5),
                )
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_expired_lease_reclaim_increments_epoch_and_fences_zombie() -> None:
    run_id = f"run_{uuid4().hex}"
    await _seed_ready_task(run_id, "TASK-1")
    engine = create_engine(os.environ["INFINITE_INTERNS_DATABASE_URL"])
    sessions = create_session_factory(engine)
    now = datetime.now(UTC)

    try:
        async with sessions() as session:
            service = LeaseService(session, run_id, lease_ttl=timedelta(seconds=90))
            first = await service.claim_ready_task("worker-a", now)
            assert first is not None
            second = await service.claim_ready_task("worker-b", now + timedelta(seconds=91))
            assert second is not None
            assert second.epoch == first.epoch + 1
            with pytest.raises(StaleLeaseError):
                await service.assert_epoch("TASK-1", first.epoch)
            await service.assert_epoch("TASK-1", second.epoch)
    finally:
        await engine.dispose()
