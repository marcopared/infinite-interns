"""Deterministic Git worktree creation for isolated task attempts."""

import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class WorktreeHandle:
    branch: str
    path: Path


Runner = Callable[[list[str]], subprocess.CompletedProcess[str]]


def _default_runner(argv: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, check=True, text=True, capture_output=True)


class WorktreeManager:
    def __init__(self, factory_root: Path, *, runner: Runner = _default_runner) -> None:
        self._factory_root = factory_root.resolve()
        self._runner = runner

    def create(
        self,
        repo: Path,
        run_id: str,
        task_id: str,
        attempt_id: str,
        base_commit: str,
    ) -> WorktreeHandle:
        for identifier in (run_id, task_id, attempt_id):
            self._validate_identifier(identifier)
        if not base_commit or "\x00" in base_commit:
            raise ValueError("base_commit must be non-empty and contain no NUL")

        branch = f"factory/{run_id}/{task_id}/{attempt_id}"
        path = self._factory_root / "worktrees" / run_id / task_id / attempt_id
        path.parent.mkdir(parents=True, exist_ok=True)
        self._runner(
            [
                "git",
                "-C",
                str(repo),
                "worktree",
                "add",
                "-b",
                branch,
                str(path),
                base_commit,
            ]
        )
        return WorktreeHandle(branch=branch, path=path)

    @staticmethod
    def _validate_identifier(identifier: str) -> None:
        if (
            not identifier
            or "/" in identifier
            or "\\" in identifier
            or ".." in identifier
            or "\x00" in identifier
        ):
            raise ValueError("worktree identifiers may not contain path traversal characters")
