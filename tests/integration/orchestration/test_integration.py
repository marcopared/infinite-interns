import asyncio
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from infinite_interns.db.engine import create_engine, create_session_factory
from infinite_interns.db.models import TaskRow
from infinite_interns.db.repositories import EventRepository, RunRepository, TaskRepository
from infinite_interns.domain.enums import RiskClass, RunStatus, TaskStatus
from infinite_interns.domain.models import RunRecord, TaskRecord
from infinite_interns.integration.service import IntegrationService, IntegrationStatus


def _run(argv: list[str], cwd: Path) -> str:
    return subprocess.run(argv, cwd=cwd, check=True, text=True, capture_output=True).stdout.strip()


def _fixture_repo(tmp_path: Path) -> tuple[Path, Path, str, str, str]:
    repo = tmp_path / "repo"
    repo.mkdir()
    _run(["git", "init", "-b", "main"], repo)
    _run(["git", "config", "user.name", "Infinite Interns Test"], repo)
    _run(["git", "config", "user.email", "test@example.invalid"], repo)
    (repo / "behavior.txt").write_text("ok\n")
    (repo / "regression.py").write_text(
        "from pathlib import Path\n"
        "import sys\n"
        "sys.exit(0 if Path('behavior.txt').read_text().strip() == 'ok' else 1)\n"
    )
    _run(["git", "add", "."], repo)
    _run(["git", "commit", "-m", "base"], repo)
    base = _run(["git", "rev-parse", "HEAD"], repo)

    _run(["git", "switch", "-c", "candidate-a"], repo)
    (repo / "harmless.txt").write_text("candidate a\n")
    _run(["git", "add", "harmless.txt"], repo)
    _run(["git", "commit", "-m", "candidate a"], repo)
    candidate_a = _run(["git", "rev-parse", "HEAD"], repo)

    _run(["git", "switch", "-c", "candidate-b", base], repo)
    (repo / "behavior.txt").write_text("broken\n")
    _run(["git", "add", "behavior.txt"], repo)
    _run(["git", "commit", "-m", "candidate b"], repo)
    candidate_b = _run(["git", "rev-parse", "HEAD"], repo)

    checkout = tmp_path / "integration"
    _run(["git", "worktree", "add", "-b", "integration", str(checkout), base], repo)
    return repo, checkout, base, candidate_a, candidate_b


async def _seed_run(
    run_id: str,
    base: str,
) -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    engine = create_engine(os.environ["INFINITE_INTERNS_DATABASE_URL"])
    sessions = create_session_factory(engine)
    async with sessions() as session:
        await RunRepository(session).add(
            RunRecord(
                run_id=run_id,
                repo="fixture",
                base_commit=base,
                status=RunStatus.RUNNING,
                started_at=datetime.now(UTC),
            )
        )
        await session.commit()
    return engine, sessions


@pytest.mark.asyncio
async def test_regression_failure_restores_checkout_and_preserves_last_green(tmp_path: Path) -> None:
    _, checkout, base, candidate_a, candidate_b = _fixture_repo(tmp_path)
    run_id = f"run_{uuid4().hex}"
    engine, sessions = await _seed_run(run_id, base)
    service = IntegrationService(engine, sessions, checkout, ("python", "regression.py"))

    try:
        await service.initialize(run_id, base, datetime.now(UTC))
        accepted = await service.integrate(run_id, candidate_a, base)
        assert accepted.status is IntegrationStatus.ACCEPTED
        green_after_a = accepted.last_green_commit
        assert green_after_a != base

        rejected = await service.integrate(run_id, candidate_b, green_after_a)
        assert rejected.status is IntegrationStatus.REJECTED
        state = await service.state(run_id)
        assert state.last_green_commit == green_after_a
        assert state.current_commit == green_after_a
        assert _run(["git", "rev-parse", "HEAD"], checkout) == green_after_a

        async with sessions() as session:
            events = await EventRepository(session).for_run(run_id)
        assert any(event.event_type == "INTEGRATION_REJECTED" for event in events)
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_failed_task_completion_restores_checkout_and_durable_anchor(tmp_path: Path) -> None:
    _, checkout, base, candidate_a, _ = _fixture_repo(tmp_path)
    run_id = f"run_{uuid4().hex}"
    engine, sessions = await _seed_run(run_id, base)
    service = IntegrationService(engine, sessions, checkout, ("python", "regression.py"))

    try:
        async with sessions() as session:
            await TaskRepository(session).add(
                TaskRecord(
                    task_id="TASK-1",
                    run_id=run_id,
                    title="candidate",
                    status=TaskStatus.CANDIDATE,
                    risk=RiskClass.HIGH,
                )
            )
            await session.execute(
                update(TaskRow)
                .where(TaskRow.run_id == run_id, TaskRow.task_id == "TASK-1")
                .values(lease_epoch=1)
            )
            await session.commit()

        await service.initialize(run_id, base, datetime.now(UTC))
        with pytest.raises(RuntimeError, match="integration-eligible candidate"):
            await service.integrate(
                run_id,
                candidate_a,
                base,
                task_id="TASK-1",
                lease_epoch=2,
            )

        state = await service.state(run_id)
        assert state.current_commit == base
        assert state.last_green_commit == base
        assert _run(["git", "rev-parse", "HEAD"], checkout) == base
        async with sessions() as session:
            task = await TaskRepository(session).get(run_id, "TASK-1")
        assert task is not None and task.status is TaskStatus.CANDIDATE
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_same_run_integration_is_serialized(tmp_path: Path) -> None:
    repo, checkout, base, candidate_a, _ = _fixture_repo(tmp_path)
    _run(["git", "switch", "-c", "candidate-c", base], repo)
    (repo / "other.txt").write_text("candidate c\n")
    _run(["git", "add", "other.txt"], repo)
    _run(["git", "commit", "-m", "candidate c"], repo)
    candidate_c = _run(["git", "rev-parse", "HEAD"], repo)

    # Force the first integration to hold the application lock long enough for overlap.
    (checkout / "regression.py").write_text(
        "from pathlib import Path\n"
        "import sys, time\n"
        "time.sleep(0.25)\n"
        "sys.exit(0 if Path('behavior.txt').read_text().strip() == 'ok' else 1)\n"
    )
    _run(["git", "add", "regression.py"], checkout)
    _run(["git", "commit", "-m", "slow regression"], checkout)
    serialized_base = _run(["git", "rev-parse", "HEAD"], checkout)

    run_id = f"run_{uuid4().hex}"
    engine, sessions = await _seed_run(run_id, serialized_base)
    service_a = IntegrationService(engine, sessions, checkout, ("python", "regression.py"))
    service_b = IntegrationService(engine, sessions, checkout, ("python", "regression.py"))
    try:
        await service_a.initialize(run_id, serialized_base, datetime.now(UTC))
        result_a, result_b = await asyncio.gather(
            service_a.integrate(run_id, candidate_a, serialized_base),
            service_b.integrate(run_id, candidate_c, serialized_base),
        )
        assert {result_a.status, result_b.status} == {
            IntegrationStatus.ACCEPTED,
            IntegrationStatus.CONFLICT,
        }
    finally:
        await engine.dispose()
