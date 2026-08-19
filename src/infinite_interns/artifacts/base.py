"""Provider-neutral artifact storage contract."""

from typing import Protocol


class ArtifactStore(Protocol):
    def put(self, run_id: str, kind: str, artifact_id: str, data: bytes) -> str: ...

    def get(self, uri: str) -> bytes: ...
