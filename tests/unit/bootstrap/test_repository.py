import subprocess
from pathlib import Path

import pytest

from infinite_interns.bootstrap.models import RepositoryKind
from infinite_interns.bootstrap.repository import DirtyRepositoryError, RepositoryInspector


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        text=True,
        capture_output=True,
    ).stdout.strip()


def _committed_repo(tmp_path: Path, files: dict[str, str]) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    for name, content in files.items():
        path = repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    _git(repo, "add", ".")
    _git(
        repo,
        "-c",
        "user.name=InfiniteInterns Test",
        "-c",
        "user.email=test@example.invalid",
        "commit",
        "-m",
        "fixture",
    )
    return repo


def test_empty_directory_becomes_greenfield_git_baseline(tmp_path: Path) -> None:
    repo = tmp_path / "empty"
    repo.mkdir()

    snapshot = RepositoryInspector().inspect(repo)

    assert snapshot.repo_kind is RepositoryKind.GREENFIELD
    assert snapshot.default_branch == "main"
    assert snapshot.base_commit == _git(repo, "rev-parse", "HEAD")
    assert snapshot.dirty is False
    assert list(repo.iterdir()) == [repo / ".git"]


def test_repo_with_only_control_docs_is_greenfield(tmp_path: Path) -> None:
    repo = _committed_repo(
        tmp_path,
        {
            "README.md": "# product\n",
            "docs/spec.md": "goal\n",
            ".gitignore": ".venv/\n",
            ".github/workflows/ci.yml": "name: ci\n",
        },
    )

    snapshot = RepositoryInspector().inspect(repo)

    assert snapshot.repo_kind is RepositoryKind.GREENFIELD


def test_repo_with_application_source_is_brownfield(tmp_path: Path) -> None:
    repo = _committed_repo(tmp_path, {"src/app.py": "print('hello')\n"})
    expected = _git(repo, "rev-parse", "HEAD")

    snapshot = RepositoryInspector().inspect(repo)

    assert snapshot.repo_kind is RepositoryKind.BROWNFIELD
    assert snapshot.base_commit == expected


def test_dirty_brownfield_is_rejected_by_default(tmp_path: Path) -> None:
    repo = _committed_repo(tmp_path, {"src/app.py": "print('hello')\n"})
    (repo / "src/app.py").write_text("print('changed')\n")

    with pytest.raises(DirtyRepositoryError):
        RepositoryInspector().inspect(repo)


def test_explicit_dirty_policy_may_snapshot_without_modifying_files(tmp_path: Path) -> None:
    repo = _committed_repo(tmp_path, {"src/app.py": "print('hello')\n"})
    (repo / "src/app.py").write_text("print('changed')\n")

    snapshot = RepositoryInspector().inspect(repo, allow_dirty=True)

    assert snapshot.repo_kind is RepositoryKind.BROWNFIELD
    assert snapshot.dirty is True
    assert (repo / "src/app.py").read_text() == "print('changed')\n"
