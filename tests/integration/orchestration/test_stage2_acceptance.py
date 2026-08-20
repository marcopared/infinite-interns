import asyncio
import json
import os
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import update

from infinite_interns.db.engine import create_engine, create_session_factory
from infinite_interns.db.models import TaskDependencyRow, TaskRow
from infinite_interns.db.repositories import EventRepository, RunRepository, TaskRepository
from infinite_interns.domain.enums import RiskClass, RunStatus, TaskStatus
from infinite_interns.domain.models import RunRecord, TaskRecord
from infinite_interns.execution.base import ExecutionRequest, ExecutionStatus
from infinite_interns.execution.worktrees import WorktreeManager
from infinite_interns.executor.docker_backend import DockerExecutionBackend
from infinite_interns.integration.service import IntegrationService, IntegrationStatus
from infinite_interns.scheduler.dag import TaskDag
from infinite_interns.scheduler.leasing import LeaseService
from infinite_interns.scheduler.results import WorkerResultService


def _run(argv: list[str], *, cwd: Path | None = None) -> str:
    return subprocess.run(argv, cwd=cwd, check=True, text=True, capture_output=True).stdout.strip()


def _fixture_repo(tmp_path: Path) -> tuple[Path, Path, str]:
    repo = tmp_path / "repo"
    repo.mkdir()
    _run(["git", "init", "-b", "main"], cwd=repo)
    _run(["git", "config", "user.name", "Infinite Interns Test"], cwd=repo)
    _run(["git", "config", "user.email", "test@example.invalid"], cwd=repo)
    (repo / "base.txt").write_text("base\n")
    (repo / "regression.py").write_text("raise SystemExit(0)\n")
    _run(["git", "add", "."], cwd=repo)
    _run(["git", "commit", "-m", "base"], cwd=repo)
    base = _run(["git", "rev-parse", "HEAD"], cwd=repo)
    checkout = tmp_path / "integration"
    _run(["git", "worktree", "add", "-b", "integration", str(checkout), base], cwd=repo)
    return repo, checkout, base


async def _wait_for_success(
    backend: DockerExecutionBackend,
    handle_id: str,
    operation_key: str,
) -> str:
    from infinite_interns.execution.base import ExecutionHandle

    handle = ExecutionHandle(
        execution_id=handle_id,
        operation_key=operation_key,
        status=ExecutionStatus.RUNNING,
    )
    status = ExecutionStatus.RUNNING
    for _ in range(80):
        status = await backend.status(handle)
        if status in {ExecutionStatus.SUCCEEDED, ExecutionStatus.FAILED}:
            break
        await asyncio.sleep(0.25)
    assert status is ExecutionStatus.SUCCEEDED
    return handle.execution_id


@pytest.mark.skipif(os.environ.get("CI") != "true", reason="Docker acceptance runs in CI")
@pytest.mark.asyncio
async def test_stage2_fake_factory_recovers_worker_and_converges(tmp_path: Path) -> None:
    repo, checkout, base = _fixture_repo(tmp_path)
    database_url = os.environ["INFINITE_INTERNS_DATABASE_URL"]
    engine = create_engine(database_url)
    sessions = create_session_factory(engine)
    run_id = f"run_{uuid4().hex}"
    now = datetime.now(UTC)
    dag = TaskDag.from_edges((("A", "C"), ("B", "C")))

    try:
        async with sessions() as session:
            await RunRepository(session).add(
                RunRecord(
                    run_id=run_id,
                    repo=str(repo),
                    base_commit=base,
                    status=RunStatus.RUNNING,
                    started_at=now,
                )
            )
            for task_id, status in (
                ("A", TaskStatus.READY),
                ("B", TaskStatus.READY),
                ("C", TaskStatus.PLANNED),
            ):
                await TaskRepository(session).add(
                    TaskRecord(
                        task_id=task_id,
                        run_id=run_id,
                        title=f"task {task_id}",
                        status=status,
                        risk=RiskClass.HIGH,
                    )
                )
            session.add_all(
                [
                    TaskDependencyRow(run_id=run_id, upstream_task_id="A", downstream_task_id="C"),
                    TaskDependencyRow(run_id=run_id, upstream_task_id="B", downstream_task_id="C"),
                ]
            )
            await session.commit()

        statuses = {"A": TaskStatus.READY, "B": TaskStatus.READY, "C": TaskStatus.PLANNED}
        assert dag.ready_tasks(statuses) == ("A", "B")

        async with sessions() as session:
            leases = LeaseService(session, run_id, lease_ttl=timedelta(seconds=90))
            lease_a = await leases.claim_ready_task("worker-a", now)
            lease_b1 = await leases.claim_ready_task("worker-b1", now)
        assert lease_a is not None and lease_a.task_id == "A"
        assert lease_b1 is not None and lease_b1.task_id == "B"
        assert dag.ready_tasks(
            {"A": TaskStatus.CLAIMED, "B": TaskStatus.CLAIMED, "C": TaskStatus.PLANNED}
        ) == ()

        manager = WorktreeManager(tmp_path / "factory")
        worktree_a = manager.create(repo, run_id, "A", "a1", base)
        worktree_b1 = manager.create(repo, run_id, "B", "b1", base)
        artifact_root = tmp_path / "artifacts"
        artifact_a = artifact_root / "A" / "a1"
        artifact_b1 = artifact_root / "B" / "b1"
        artifact_a.mkdir(parents=True)
        artifact_b1.mkdir(parents=True)

        image = "infinite-interns-fake-worker:stage2-acceptance"
        _run(["docker", "build", "-t", image, "-f", "docker/fake-worker/Dockerfile", "."])
        backend = DockerExecutionBackend()

        request_a = ExecutionRequest(
            operation_key=f"{run_id}:A:a1:execute",
            run_id=run_id,
            task_id="A",
            attempt_id="a1",
            lease_epoch=lease_a.epoch,
            worktree_path=str(worktree_a.path),
            image=image,
            argv=("python", "/worker.py", "/artifacts/input.json", "/workspace", "/artifacts"),
            artifact_path=str(artifact_a),
            cpu_limit=1.0,
            memory_limit_mb=256,
            network_profile="none",
        )
        request_b1 = ExecutionRequest(
            operation_key=f"{run_id}:B:b1:execute",
            run_id=run_id,
            task_id="B",
            attempt_id="b1",
            lease_epoch=lease_b1.epoch,
            worktree_path=str(worktree_b1.path),
            image=image,
            argv=("python", "-c", "import time; time.sleep(30)"),
            artifact_path=str(artifact_b1),
            cpu_limit=1.0,
            memory_limit_mb=256,
            network_profile="none",
        )

        handle_a, handle_b1 = await asyncio.gather(
            backend.create(request_a),
            backend.create(request_b1),
        )
        await backend.terminate(handle_b1)
        await _wait_for_success(backend, handle_a.execution_id, request_a.operation_key)

        result_a = json.loads((artifact_a / "result.json").read_text())
        async with sessions() as session:
            assert await WorkerResultService(session, run_id).accept(
                "A", lease_a.epoch, TaskStatus.CANDIDATE, now + timedelta(seconds=30)
            )
            await session.commit()

        integration = IntegrationService(engine, sessions, checkout, ("python", "regression.py"))
        await integration.initialize(run_id, base, now)
        integrated_a = await integration.integrate(
            run_id,
            result_a["candidate_commit"],
            base,
            task_id="A",
            lease_epoch=lease_a.epoch,
        )
        assert integrated_a.status is IntegrationStatus.ACCEPTED

        async with sessions() as session:
            lease_b2 = await LeaseService(
                session, run_id, lease_ttl=timedelta(seconds=90)
            ).claim_ready_task("worker-b2", now + timedelta(seconds=91))
        assert lease_b2 is not None and lease_b2.task_id == "B"
        assert lease_b2.epoch > lease_b1.epoch

        async with sessions() as session:
            stale_accepted = await WorkerResultService(session, run_id).accept(
                "B", lease_b1.epoch, TaskStatus.CANDIDATE, now + timedelta(seconds=92)
            )
            await session.commit()
        assert not stale_accepted

        worktree_b2 = manager.create(repo, run_id, "B", "b2", base)
        artifact_b2 = artifact_root / "B" / "b2"
        artifact_b2.mkdir(parents=True)
        request_b2 = ExecutionRequest(
            operation_key=f"{run_id}:B:b2:execute",
            run_id=run_id,
            task_id="B",
            attempt_id="b2",
            lease_epoch=lease_b2.epoch,
            worktree_path=str(worktree_b2.path),
            image=image,
            argv=("python", "/worker.py", "/artifacts/input.json", "/workspace", "/artifacts"),
            artifact_path=str(artifact_b2),
            cpu_limit=1.0,
            memory_limit_mb=256,
            network_profile="none",
        )
        handle_b2 = await backend.create(request_b2)
        await _wait_for_success(backend, handle_b2.execution_id, request_b2.operation_key)
        result_b2 = json.loads((artifact_b2 / "result.json").read_text())
        async with sessions() as session:
            assert await WorkerResultService(session, run_id).accept(
                "B", lease_b2.epoch, TaskStatus.CANDIDATE, now + timedelta(seconds=93)
            )
            await session.commit()
        integrated_b = await integration.integrate(
            run_id,
            result_b2["candidate_commit"],
            integrated_a.last_green_commit,
            task_id="B",
            lease_epoch=lease_b2.epoch,
        )
        assert integrated_b.status is IntegrationStatus.ACCEPTED

        async with sessions() as session:
            a = await TaskRepository(session).get(run_id, "A")
            b = await TaskRepository(session).get(run_id, "B")
            c = await TaskRepository(session).get(run_id, "C")
        assert a is not None and b is not None and c is not None
        assert dag.ready_tasks({"A": a.status, "B": b.status, "C": c.status}) == ("C",)

        async with sessions() as session:
            await session.execute(
                update(TaskRow)
                .where(
                    TaskRow.run_id == run_id,
                    TaskRow.task_id == "C",
                    TaskRow.status == TaskStatus.PLANNED.value,
                )
                .values(status=TaskStatus.READY.value)
            )
            await session.commit()
            lease_c = await LeaseService(session, run_id).claim_ready_task(
                "worker-c", now + timedelta(seconds=93)
            )
        assert lease_c is not None and lease_c.task_id == "C"

        worktree_c = manager.create(repo, run_id, "C", "c1", integrated_b.last_green_commit)
        artifact_c = artifact_root / "C" / "c1"
        artifact_c.mkdir(parents=True)
        request_c = ExecutionRequest(
            operation_key=f"{run_id}:C:c1:execute",
            run_id=run_id,
            task_id="C",
            attempt_id="c1",
            lease_epoch=lease_c.epoch,
            worktree_path=str(worktree_c.path),
            image=image,
            argv=("python", "/worker.py", "/artifacts/input.json", "/workspace", "/artifacts"),
            artifact_path=str(artifact_c),
            cpu_limit=1.0,
            memory_limit_mb=256,
            network_profile="none",
        )
        handle_c = await backend.create(request_c)
        await _wait_for_success(backend, handle_c.execution_id, request_c.operation_key)
        result_c = json.loads((artifact_c / "result.json").read_text())
        async with sessions() as session:
            assert await WorkerResultService(session, run_id).accept(
                "C", lease_c.epoch, TaskStatus.CANDIDATE, now + timedelta(seconds=94)
            )
            await session.commit()
        integrated_c = await integration.integrate(
            run_id,
            result_c["candidate_commit"],
            integrated_b.last_green_commit,
            task_id="C",
            lease_epoch=lease_c.epoch,
        )
        assert integrated_c.status is IntegrationStatus.ACCEPTED

        final_state = await integration.state(run_id)
        assert final_state.current_commit == final_state.last_green_commit
        assert _run(["python", "regression.py"], cwd=checkout) == ""
        assert _run(["git", "rev-parse", "HEAD"], cwd=checkout) == final_state.last_green_commit

        async with sessions() as session:
            final_tasks = [await TaskRepository(session).get(run_id, task) for task in ("A", "B", "C")]
            events = await EventRepository(session).for_run(run_id)
        assert all(task is not None and task.status is TaskStatus.DONE for task in final_tasks)
        assert any(event.event_type == "STALE_WORKER_WRITE_REJECTED" for event in events)

        integrated_files = {path.name for path in checkout.glob("task-output*.txt")}
        assert integrated_files == {"task-output-a1.txt", "task-output-b2.txt", "task-output-c1.txt"}
        assert (
            request_a.environment_names
            == request_b1.environment_names
            == request_b2.environment_names
            == request_c.environment_names
            == ()
        )
    finally:
        await engine.dispose()
