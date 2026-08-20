"""Host-side Docker execution backend with label-based idempotency."""

import asyncio
import json
import os
import re
import subprocess
from pathlib import Path

from infinite_interns.execution.base import ExecutionHandle, ExecutionRequest, ExecutionStatus

_ENV_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class DockerExecutionBackend:
    """Run disposable workers without exposing Docker authority to the worker."""

    def __init__(self) -> None:
        self._requests: dict[str, ExecutionRequest] = {}

    async def create(self, request: ExecutionRequest) -> ExecutionHandle:
        worktree = Path(request.worktree_path).resolve()
        artifacts = Path(request.artifact_path).resolve()
        if not worktree.is_dir():
            raise ValueError("worktree_path must be an existing directory")
        artifacts.mkdir(parents=True, exist_ok=True)
        await asyncio.to_thread(self._write_input, artifacts, request)

        existing = await asyncio.to_thread(self._find_by_operation_key, request.operation_key)
        if existing is not None:
            self._requests[existing] = request
            return ExecutionHandle(
                execution_id=existing,
                operation_key=request.operation_key,
                status=await self._status_for_id(existing),
            )

        for name in request.environment_names:
            if _ENV_NAME.fullmatch(name) is None:
                raise ValueError(f"invalid environment variable name: {name}")

        argv = [
            "docker",
            "run",
            "--detach",
            "--label",
            f"ii.run_id={request.run_id}",
            "--label",
            f"ii.task_id={request.task_id}",
            "--label",
            f"ii.attempt_id={request.attempt_id}",
            "--label",
            f"ii.operation_key={request.operation_key}",
            "--label",
            f"ii.lease_epoch={request.lease_epoch}",
            "--user",
            f"{os.getuid()}:{os.getgid()}",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--cpus",
            str(request.cpu_limit),
            "--memory",
            f"{request.memory_limit_mb}m",
            "--network",
            request.network_profile,
            "--mount",
            f"type=bind,src={worktree},dst=/workspace",
            "--mount",
            f"type=bind,src={artifacts},dst=/artifacts",
        ]
        for name in request.environment_names:
            argv.extend(("--env", name))
        argv.extend((request.image, *request.argv))

        container_id = (await asyncio.to_thread(self._run, argv)).stdout.strip()
        if not container_id:
            raise RuntimeError("docker run returned no container ID")
        self._requests[container_id] = request
        return ExecutionHandle(
            execution_id=container_id,
            operation_key=request.operation_key,
            status=ExecutionStatus.RUNNING,
        )

    async def status(self, handle: ExecutionHandle) -> ExecutionStatus:
        status = await self._status_for_id(handle.execution_id)
        if status is ExecutionStatus.SUCCEEDED:
            request = self._requests.get(handle.execution_id)
            if request is not None:
                await asyncio.to_thread(self._materialize_candidate, request)
        return status

    async def terminate(self, handle: ExecutionHandle) -> None:
        current = await self._status_for_id(handle.execution_id)
        if current is ExecutionStatus.RUNNING:
            await asyncio.to_thread(self._run, ["docker", "stop", handle.execution_id])

    async def _status_for_id(self, container_id: str) -> ExecutionStatus:
        state = (
            await asyncio.to_thread(
                self._run,
                ["docker", "inspect", container_id, "--format", "{{.State.Status}}"],
            )
        ).stdout.strip()
        if state in {"created", "restarting"}:
            return ExecutionStatus.CREATED
        if state in {"running", "paused"}:
            return ExecutionStatus.RUNNING
        if state == "exited":
            exit_code = (
                await asyncio.to_thread(
                    self._run,
                    ["docker", "inspect", container_id, "--format", "{{.State.ExitCode}}"],
                )
            ).stdout.strip()
            return ExecutionStatus.SUCCEEDED if exit_code == "0" else ExecutionStatus.FAILED
        if state in {"dead", "removing"}:
            return ExecutionStatus.FAILED
        raise RuntimeError(f"unsupported Docker container state: {state}")

    def _find_by_operation_key(self, operation_key: str) -> str | None:
        result = self._run(
            [
                "docker",
                "ps",
                "--all",
                "--no-trunc",
                "--filter",
                f"label=ii.operation_key={operation_key}",
                "--format",
                "{{.ID}}",
            ]
        ).stdout.splitlines()
        ids = [item.strip() for item in result if item.strip()]
        if len(ids) > 1:
            raise RuntimeError("operation key maps to more than one Docker container")
        return ids[0] if ids else None

    @staticmethod
    def _write_input(artifact_dir: Path, request: ExecutionRequest) -> None:
        payload = {
            "run_id": request.run_id,
            "task_id": request.task_id,
            "attempt_id": request.attempt_id,
            "lease_epoch": request.lease_epoch,
        }
        target = artifact_dir / "input.json"
        temporary = artifact_dir / "input.json.tmp"
        temporary.write_text(json.dumps(payload, sort_keys=True))
        temporary.replace(target)

    @staticmethod
    def _materialize_candidate(request: ExecutionRequest) -> None:
        artifacts = Path(request.artifact_path).resolve()
        worker_result = artifacts / "worker-result.json"
        final_result = artifacts / "result.json"
        if final_result.exists():
            return
        if not worker_result.exists():
            raise RuntimeError("successful worker exited without worker-result.json")
        payload = json.loads(worker_result.read_text())
        if (
            payload.get("attempt_id") != request.attempt_id
            or payload.get("lease_epoch") != request.lease_epoch
            or payload.get("status") != "succeeded"
        ):
            raise RuntimeError("worker result does not match execution request")

        worktree = Path(request.worktree_path).resolve()
        DockerExecutionBackend._run(["git", "-C", str(worktree), "add", "-A"])
        DockerExecutionBackend._run(
            [
                "git",
                "-C",
                str(worktree),
                "-c",
                "user.name=InfiniteInterns",
                "-c",
                "user.email=interns@example.invalid",
                "commit",
                "--allow-empty",
                "-m",
                f"factory: candidate {request.attempt_id}",
            ]
        )
        candidate = DockerExecutionBackend._run(
            ["git", "-C", str(worktree), "rev-parse", "HEAD"]
        ).stdout.strip()
        result = {
            "attempt_id": request.attempt_id,
            "lease_epoch": request.lease_epoch,
            "status": "succeeded",
            "candidate_commit": candidate,
        }
        temporary = artifacts / "result.json.tmp"
        temporary.write_text(json.dumps(result, sort_keys=True))
        temporary.replace(final_result)

    @staticmethod
    def _run(argv: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(argv, check=True, text=True, capture_output=True)
