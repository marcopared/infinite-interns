from pathlib import Path
from subprocess import CompletedProcess

import pytest

from infinite_interns.execution.worktrees import WorktreeManager


def test_create_uses_expected_branch_path_and_git_argv(tmp_path: Path) -> None:
    calls: list[list[str]] = []

    def runner(argv: list[str]) -> CompletedProcess[str]:
        calls.append(argv)
        return CompletedProcess(argv, 0, "", "")

    repo = tmp_path / "repo"
    repo.mkdir()
    manager = WorktreeManager(tmp_path / "factory", runner=runner)
    handle = manager.create(repo, "run1", "task1", "attempt1", "abc123")

    assert handle.branch == "factory/run1/task1/attempt1"
    assert handle.path == tmp_path / "factory" / "worktrees" / "run1" / "task1" / "attempt1"
    assert calls == [[
        "git",
        "-C",
        str(repo),
        "worktree",
        "add",
        "-b",
        "factory/run1/task1/attempt1",
        str(handle.path),
        "abc123",
    ]]


@pytest.mark.parametrize("identifier", ["a/b", "a\\b", "..", "a..b", "bad\x00id"])
def test_unsafe_identifiers_are_rejected_before_git(tmp_path: Path, identifier: str) -> None:
    called = False

    def runner(argv: list[str]) -> CompletedProcess[str]:
        nonlocal called
        called = True
        return CompletedProcess(argv, 0, "", "")

    manager = WorktreeManager(tmp_path / "factory", runner=runner)
    with pytest.raises(ValueError):
        manager.create(tmp_path / "repo", identifier, "task", "attempt", "abc")
    assert not called
