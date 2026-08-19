import asyncio
import json
import os
import subprocess
from pathlib import Path

import pytest

from infinite_interns.execution.base import ExecutionRequest, ExecutionStatus
from infinite_interns.execution.worktrees import WorktreeManager
from infinite_interns.executor.docker_backend import DockerExecutionBackend


def _run(argv: list[str], *, cwd: Path | None = None) -> str:
    return subprocess.run(
        argv,
        cwd=cwd,
        check=True,
        text=True,
        capture_output=True,
    ).stdout.strip()


@pytest.mark.skipif(os.environ.get("CI") != "true", reason="Docker integration runs in CI")
@pytest.mark.asyncio
async def test_fake_worker_commits_only_inside_task_worktree(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _run(["git", "init", "-b", "main"], cwd=repo)
    _run(["git", "config", "user.name", "Infinite Interns Test"], cwd=repo)
    _run(["git", "config", "user.email", "test@example.invalid"], cwd=repo)
    (repo / "base.txt").write_text("base\n")
    _run(["git", "add", "base.txt"], cwd=repo)
    _run(["git", "commit", "-m", "base"], cwd=repo)
    base_commit = _run(["git", "rev-parse", "HEAD"], cwd=repo)

    manager = WorktreeManager(tmp_path / "factory")
    worktree = manager.create(repo, "run1", "task1", "attempt1", base_commit)
    artifact_dir = tmp_path / "artifacts" / "run1" / "task1" / "attempt1"
    artifact_dir.mkdir(parents=True)

    image = "infinite-interns-fake-worker:test"
    _run(["docker", "build", "-t", image, "-f", "docker/fake-worker/Dockerfile", "."])

    backend = DockerExecutionBackend()
    request = ExecutionRequest(
        operation_key="run1:task1:attempt1:execute",
        run_id="run1",
        task_id="task1",
        attempt_id="attempt1",
        lease_epoch=1,
        worktree_path=str(worktree.path),
        image=image,
        argv=("python", "/worker.py", "/artifacts/input.json", "/workspace", "/artifacts"),
        artifact_path=str(artifact_dir),
        environment_names=(),
        cpu_limit=1.0,
        memory_limit_mb=256,
        network_profile="none",
    )

    handle = await backend.create(request)
    try:
        restarted_backend = DockerExecutionBackend()
        recovered = await restarted_backend.create(request)
        assert recovered.execution_id == handle.execution_id

        status = ExecutionStatus.CREATED
        for _ in range(60):
            status = await backend.status(handle)
            if status in {ExecutionStatus.SUCCEEDED, ExecutionStatus.FAILED}:
                break
            await asyncio.sleep(0.25)
        assert status is ExecutionStatus.SUCCEEDED

        result = json.loads((artifact_dir / "result.json").read_text())
        assert result["attempt_id"] == "attempt1"
        assert result["lease_epoch"] == 1
        assert result["status"] == "succeeded"
        candidate = result["candidate_commit"]
        assert _run(["git", "-C", str(worktree.path), "show", f"{candidate}:task-output.txt"])
        assert not (repo / "task-output.txt").exists()
        assert _run(["git", "rev-parse", "HEAD"], cwd=repo) == base_commit

        mounts = json.loads(
            _run(["docker", "inspect", handle.execution_id, "--format", "{{json .Mounts}}"])
        )
        sources = {mount["Source"] for mount in mounts}
        assert "/var/run/docker.sock" not in sources
        assert sources == {str(worktree.path.resolve()), str(artifact_dir.resolve())}
    finally:
        await backend.terminate(handle)
