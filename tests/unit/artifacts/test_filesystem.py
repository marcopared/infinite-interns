from pathlib import Path

import pytest

from infinite_interns.artifacts import filesystem


def _store(tmp_path: Path):
    store_type = getattr(filesystem, "FilesystemArtifactStore", None)
    assert store_type is not None
    return store_type(tmp_path)


def test_round_trip(tmp_path: Path) -> None:
    store = _store(tmp_path)
    uri = store.put("run_1", "logs", "a1", b"hello")
    assert uri == "artifact://runs/run_1/logs/a1"
    assert store.get(uri) == b"hello"


def test_existing_artifact_is_idempotent_but_immutable(tmp_path: Path) -> None:
    store = _store(tmp_path)
    uri = store.put("run_1", "logs", "a1", b"hello")
    assert store.put("run_1", "logs", "a1", b"hello") == uri
    with pytest.raises(FileExistsError):
        store.put("run_1", "logs", "a1", b"different")
    assert store.get(uri) == b"hello"


@pytest.mark.parametrize(
    ("run_id", "kind", "artifact_id"),
    [
        ("../escape", "logs", "a1"),
        ("run_1", "../escape", "a1"),
        ("run_1", "logs", "../escape"),
        ("/absolute", "logs", "a1"),
        ("run_1", "logs/subdir", "a1"),
    ],
)
def test_rejects_unsafe_segments(
    tmp_path: Path,
    run_id: str,
    kind: str,
    artifact_id: str,
) -> None:
    store = _store(tmp_path)
    with pytest.raises(ValueError):
        store.put(run_id, kind, artifact_id, b"x")


def test_rejects_malformed_uri(tmp_path: Path) -> None:
    store = _store(tmp_path)
    with pytest.raises(ValueError):
        store.get("https://runs/run_1/logs/a1")
