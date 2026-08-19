"""Traversal-safe filesystem artifact backend."""

from pathlib import Path
from urllib.parse import quote, unquote, urlparse


class FilesystemArtifactStore:
    def __init__(self, root: Path) -> None:
        self._root = root.resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _validate_segment(value: str) -> str:
        if not value or value in {".", ".."}:
            raise ValueError("artifact path segment must be non-empty and non-relative")
        if "/" in value or "\\" in value or "\x00" in value:
            raise ValueError("artifact path segment may not contain path separators")
        return value

    def _path_for(self, run_id: str, kind: str, artifact_id: str) -> Path:
        safe_run_id = self._validate_segment(run_id)
        safe_kind = self._validate_segment(kind)
        safe_artifact_id = self._validate_segment(artifact_id)
        path = (self._root / "runs" / safe_run_id / safe_kind / safe_artifact_id).resolve()
        if not path.is_relative_to(self._root):
            raise ValueError("artifact path escapes configured root")
        return path

    @staticmethod
    def _uri(run_id: str, kind: str, artifact_id: str) -> str:
        return "artifact://runs/{}/{}/{}".format(
            quote(run_id, safe="._-"),
            quote(kind, safe="._-"),
            quote(artifact_id, safe="._-"),
        )

    def put(self, run_id: str, kind: str, artifact_id: str, data: bytes) -> str:
        path = self._path_for(run_id, kind, artifact_id)
        uri = self._uri(run_id, kind, artifact_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with path.open("xb") as handle:
                handle.write(data)
        except FileExistsError:
            if path.read_bytes() != data:
                raise
        return uri

    def get(self, uri: str) -> bytes:
        parsed = urlparse(uri)
        if parsed.scheme != "artifact" or parsed.netloc != "runs":
            raise ValueError("artifact URI must use artifact://runs")
        if parsed.params or parsed.query or parsed.fragment:
            raise ValueError("artifact URI may not contain params, query, or fragment")

        parts = [unquote(part) for part in parsed.path.split("/") if part]
        if len(parts) != 3:
            raise ValueError("artifact URI path must contain run, kind, and artifact ID")

        return self._path_for(parts[0], parts[1], parts[2]).read_bytes()
