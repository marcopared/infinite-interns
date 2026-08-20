"""Repository guidance discovery with explicit trust and provenance."""

from hashlib import sha256
from pathlib import Path, PurePosixPath

from ..bootstrap.models import GuidanceRef


_KNOWN_GUIDANCE = (
    "AGENTS.md",
    "CONTRIBUTING.md",
    "pyproject.toml",
    "package.json",
    "pnpm-workspace.yaml",
    "pytest.ini",
    "tox.ini",
    "tsconfig.json",
)


class GuidanceDiscoverer:
    def discover(
        self,
        repo: Path,
        *,
        commit_sha: str,
        configured_docs: tuple[str, ...] = (),
    ) -> tuple[GuidanceRef, ...]:
        root = repo.resolve()
        candidates: set[str] = set(_KNOWN_GUIDANCE)
        candidates.update(configured_docs)
        refs: list[GuidanceRef] = []

        for relative in sorted(candidates):
            pure = PurePosixPath(relative)
            if pure.is_absolute() or ".." in pure.parts:
                raise ValueError(f"guidance path must stay inside repository: {relative}")
            candidate = (root / pure.as_posix()).resolve()
            if not candidate.is_relative_to(root):
                raise ValueError(f"guidance path escapes repository: {relative}")
            if not candidate.is_file():
                continue
            data = candidate.read_bytes()
            refs.append(
                GuidanceRef(
                    path=pure.as_posix(),
                    commit_sha=commit_sha,
                    content_sha256=sha256(data).hexdigest(),
                )
            )
        return tuple(refs)
