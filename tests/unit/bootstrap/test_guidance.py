import hashlib
import subprocess
from pathlib import Path

import pytest

from infinite_interns.context.guidance import GuidanceDiscoverer


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        text=True,
        capture_output=True,
    ).stdout.strip()


def _repo(tmp_path: Path) -> tuple[Path, str]:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    (repo / "AGENTS.md").write_text("# guidance\n")
    (repo / "CONTRIBUTING.md").write_text("# contributing\n")
    (repo / "pyproject.toml").write_text("[project]\nname='x'\n")
    (repo / "docs").mkdir()
    (repo / "docs" / "engineering.md").write_text("rules\n")
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
    return repo, _git(repo, "rev-parse", "HEAD")


def test_discovers_known_guidance_with_commit_and_content_hash(tmp_path: Path) -> None:
    repo, commit = _repo(tmp_path)

    refs = GuidanceDiscoverer().discover(repo, commit_sha=commit)
    by_path = {item.path: item for item in refs}

    assert {"AGENTS.md", "CONTRIBUTING.md", "pyproject.toml"} <= set(by_path)
    agents = by_path["AGENTS.md"]
    assert agents.commit_sha == commit
    assert agents.trust_label == "REPOSITORY_CONTENT"
    assert agents.content_sha256 == hashlib.sha256((repo / "AGENTS.md").read_bytes()).hexdigest()


def test_explicit_guidance_doc_is_included(tmp_path: Path) -> None:
    repo, commit = _repo(tmp_path)

    refs = GuidanceDiscoverer().discover(
        repo,
        commit_sha=commit,
        configured_docs=("docs/engineering.md",),
    )

    assert "docs/engineering.md" in {item.path for item in refs}


def test_configured_guidance_cannot_escape_repo(tmp_path: Path) -> None:
    repo, commit = _repo(tmp_path)

    with pytest.raises(ValueError):
        GuidanceDiscoverer().discover(repo, commit_sha=commit, configured_docs=("../secret.txt",))
