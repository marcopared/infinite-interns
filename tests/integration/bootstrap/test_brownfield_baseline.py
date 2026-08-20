import json
import subprocess
import sys
from pathlib import Path

from infinite_interns.artifacts.filesystem import FilesystemArtifactStore
from infinite_interns.bootstrap.models import CommandKind, RepositoryKind
from infinite_interns.bootstrap.service import BootstrapService
from infinite_interns.config import BootstrapSettings, Settings


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        text=True,
        capture_output=True,
    ).stdout.strip()


def _brownfield_repo(tmp_path: Path) -> tuple[Path, str]:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    (repo / "src").mkdir()
    (repo / "src" / "app.py").write_text("VALUE = 1\n")
    _git(repo, "add", ".")
    _git(
        repo,
        "-c",
        "user.name=InfiniteInterns Test",
        "-c",
        "user.email=test@example.invalid",
        "commit",
        "-m",
        "brownfield fixture",
    )
    return repo, _git(repo, "rev-parse", "HEAD")


def test_brownfield_baseline_captures_preexisting_failure_and_continues(tmp_path: Path) -> None:
    repo, base_commit = _brownfield_repo(tmp_path)
    artifact_root = tmp_path / "artifacts"
    store = FilesystemArtifactStore(artifact_root)
    settings = Settings(
        bootstrap=BootstrapSettings(
            command_overrides={
                "lint": (sys.executable, "-c", "import sys; print('LINT_FAIL'); sys.exit(3)"),
                "unit": (sys.executable, "-c", "print('UNIT_AFTER_FAILURE')"),
            }
        )
    )

    summary = BootstrapService(store).run(repo, "run-brownfield", settings)

    assert summary.repo_kind is RepositoryKind.BROWNFIELD
    assert summary.base_commit == base_commit
    assert len(summary.failures) == 1
    failure = summary.failures[0]
    assert failure.command_kind is CommandKind.LINT
    assert failure.exit_code == 3
    assert failure.base_commit == base_commit
    assert failure.pre_existing is True
    assert failure.failure_id.startswith("lint:")

    failed_payload = json.loads(store.get(failure.artifact_uri))
    assert failed_payload["argv"][-1].endswith("sys.exit(3)")
    assert failed_payload["exit_code"] == 3
    assert "LINT_FAIL" in failed_payload["stdout"]

    artifacts = list((artifact_root / "runs" / "run-brownfield" / "baseline").iterdir())
    assert len(artifacts) == 2
    payloads = [json.loads(path.read_text()) for path in artifacts]
    assert any("UNIT_AFTER_FAILURE" in payload["stdout"] for payload in payloads)


def test_baseline_output_replaces_absolute_repo_path_before_persistence(tmp_path: Path) -> None:
    repo, _ = _brownfield_repo(tmp_path)
    store = FilesystemArtifactStore(tmp_path / "artifacts")
    settings = Settings(
        bootstrap=BootstrapSettings(
            command_overrides={
                "lint": (
                    sys.executable,
                    "-c",
                    f"import sys; print({str(repo)!r}); sys.exit(2)",
                )
            }
        )
    )

    summary = BootstrapService(store).run(repo, "run-redaction", settings)

    payload = store.get(summary.failures[0].artifact_uri).decode()
    assert str(repo) not in payload
    assert "<repo>" in payload


def test_brownfield_baseline_cannot_modify_workload_checkout(tmp_path: Path) -> None:
    repo, base_commit = _brownfield_repo(tmp_path)
    store = FilesystemArtifactStore(tmp_path / "artifacts")
    settings = Settings(
        bootstrap=BootstrapSettings(
            command_overrides={
                "lint": (
                    sys.executable,
                    "-c",
                    "from pathlib import Path; Path('src/app.py').write_text('MUTATED\\n')",
                )
            }
        )
    )

    summary = BootstrapService(store).run(repo, "run-isolated", settings)

    assert summary.base_commit == base_commit
    assert (repo / "src" / "app.py").read_text() == "VALUE = 1\n"
    assert _git(repo, "status", "--porcelain=v1") == ""
