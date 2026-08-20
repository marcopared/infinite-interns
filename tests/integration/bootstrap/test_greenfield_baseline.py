import subprocess
from pathlib import Path

from infinite_interns.artifacts.filesystem import FilesystemArtifactStore
from infinite_interns.bootstrap.models import RepositoryKind
from infinite_interns.bootstrap.service import BootstrapService
from infinite_interns.config import Settings


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        text=True,
        capture_output=True,
    ).stdout.strip()


def test_greenfield_bootstrap_creates_only_neutral_control_baseline(tmp_path: Path) -> None:
    repo = tmp_path / "new-product"
    repo.mkdir()
    store = FilesystemArtifactStore(tmp_path / "artifacts")

    summary = BootstrapService(store).run(repo, "run-greenfield", Settings())

    assert summary.repo_kind is RepositoryKind.GREENFIELD
    assert summary.default_branch == "main"
    assert summary.base_commit == _git(repo, "rev-parse", "HEAD")
    assert _git(repo, "log", "-1", "--pretty=%s") == "chore: initialize greenfield baseline"
    assert _git(repo, "status", "--porcelain=v1") == ""
    assert _git(repo, "ls-files") == ".gitignore"
    assert (repo / ".gitignore").read_text() == ".infinite-interns/\n"

    assert summary.commands == ()
    assert summary.failures == ()
    assert summary.languages == ()
    assert summary.package_managers == ()
    assert not (repo / "src").exists()
    assert not (repo / "package.json").exists()
    assert not (repo / "pyproject.toml").exists()
    assert not (repo / "migrations").exists()
