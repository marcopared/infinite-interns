"""Deterministic Git repository inspection for bootstrap."""

import subprocess
from pathlib import Path, PurePosixPath

from pydantic import Field

from infinite_interns.bootstrap.models import BootstrapModel, RepositoryKind


class RepositoryInspectionError(RuntimeError):
    """Base error for repository inputs that cannot be safely snapshotted."""


class DirtyRepositoryError(RepositoryInspectionError):
    """Raised when autonomous work would inherit an unsnapshotted brownfield tree."""


class NotGitRepositoryError(RepositoryInspectionError):
    """Raised for a non-empty directory without Git history."""


class RepositorySnapshot(BootstrapModel):
    path: Path
    repo_kind: RepositoryKind
    base_commit: str = Field(min_length=1)
    default_branch: str = Field(min_length=1)
    dirty: bool
    tracked_files: tuple[str, ...] = ()


_CONTROL_FILENAMES = {
    ".editorconfig",
    ".gitattributes",
    ".gitignore",
    ".pre-commit-config.yaml",
    "AGENTS.md",
    "CONTRIBUTING.md",
    "LICENSE",
    "LICENSE.md",
    "README.md",
}
_CONTROL_PREFIXES = (
    ".autofactory/",
    ".github/",
    ".infinite-interns/",
    "docs/",
)


def _run_git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        text=True,
        capture_output=True,
    )
    return completed.stdout.strip()


def _is_control_only(path: str) -> bool:
    normalized = PurePosixPath(path).as_posix()
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized in _CONTROL_FILENAMES or normalized.startswith(_CONTROL_PREFIXES)


def _status_paths(status: str) -> tuple[str, ...]:
    paths: list[str] = []
    for line in status.splitlines():
        if len(line) < 4:
            continue
        path = line[3:]
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        paths.append(path)
    return tuple(paths)


class RepositoryInspector:
    def inspect(self, path: Path, *, allow_dirty: bool = False) -> RepositorySnapshot:
        repo = path.resolve()
        if not repo.is_dir():
            raise RepositoryInspectionError(f"repository path is not a directory: {repo}")

        if not (repo / ".git").exists():
            if any(repo.iterdir()):
                raise NotGitRepositoryError("non-empty workload directories must already be Git repositories")
            self._initialize_empty_greenfield(repo)

        try:
            inside = _run_git(repo, "rev-parse", "--is-inside-work-tree")
        except subprocess.CalledProcessError as exc:
            raise NotGitRepositoryError("workload path is not a Git work tree") from exc
        if inside != "true":
            raise NotGitRepositoryError("workload path is not a Git work tree")

        self._ensure_head(repo)
        base_commit = _run_git(repo, "rev-parse", "HEAD")
        branch = _run_git(repo, "branch", "--show-current") or "detached"
        status = _run_git(repo, "status", "--porcelain=v1")
        dirty = bool(status)
        tracked_raw = _run_git(repo, "ls-files")
        tracked = tuple(sorted(line for line in tracked_raw.splitlines() if line))
        dirty_paths = _status_paths(status)

        product_content = any(not _is_control_only(item) for item in (*tracked, *dirty_paths))
        repo_kind = RepositoryKind.BROWNFIELD if product_content else RepositoryKind.GREENFIELD
        if dirty and repo_kind is RepositoryKind.BROWNFIELD and not allow_dirty:
            raise DirtyRepositoryError(
                "brownfield repository has uncommitted changes; configure an explicit dirty snapshot policy"
            )

        return RepositorySnapshot(
            path=repo,
            repo_kind=repo_kind,
            base_commit=base_commit,
            default_branch=branch,
            dirty=dirty,
            tracked_files=tracked,
        )

    @staticmethod
    def _initialize_empty_greenfield(repo: Path) -> None:
        _run_git(repo, "init", "-b", "main")
        RepositoryInspector._commit_empty_baseline(repo)

    @staticmethod
    def _ensure_head(repo: Path) -> None:
        try:
            _run_git(repo, "rev-parse", "--verify", "HEAD")
        except subprocess.CalledProcessError:
            RepositoryInspector._commit_empty_baseline(repo)

    @staticmethod
    def _commit_empty_baseline(repo: Path) -> None:
        _run_git(
            repo,
            "-c",
            "user.name=InfiniteInterns",
            "-c",
            "user.email=bootstrap@infinite-interns.invalid",
            "commit",
            "--allow-empty",
            "-m",
            "chore: initialize repository baseline",
        )
