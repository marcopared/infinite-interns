"""Repository bootstrap service and bounded baseline execution."""

import json
import subprocess
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

from infinite_interns.artifacts.filesystem import FilesystemArtifactStore
from infinite_interns.bootstrap.commands import CommandDetector
from infinite_interns.bootstrap.models import (
    BaselineFailure,
    BaselineSummary,
    CommandKind,
    DetectedCommand,
    RepositoryKind,
)
from infinite_interns.bootstrap.repository import (
    RepositoryInspector,
    RepositorySnapshot,
)
from infinite_interns.config import Settings
from infinite_interns.context.guidance import GuidanceDiscoverer

_BASELINE_EXECUTABLE_KINDS = {
    CommandKind.INSTALL,
    CommandKind.BUILD,
    CommandKind.TYPECHECK,
    CommandKind.LINT,
    CommandKind.UNIT,
    CommandKind.INTEGRATION,
}


class BootstrapService:
    def __init__(
        self,
        artifact_store: FilesystemArtifactStore,
        *,
        inspector: RepositoryInspector | None = None,
        command_detector: CommandDetector | None = None,
        guidance_discoverer: GuidanceDiscoverer | None = None,
    ) -> None:
        self._artifacts = artifact_store
        self._inspector = inspector or RepositoryInspector()
        self._commands = command_detector or CommandDetector()
        self._guidance = guidance_discoverer or GuidanceDiscoverer()

    def run(self, repo: Path, run_id: str, settings: Settings) -> BaselineSummary:
        snapshot = self._inspector.inspect(repo, allow_dirty=settings.bootstrap.allow_dirty)
        commands = self._commands.detect(snapshot.path, settings.bootstrap)
        guidance = self._guidance.discover(
            snapshot.path,
            commit_sha=snapshot.base_commit,
            configured_docs=settings.bootstrap.configured_guidance_docs,
        )
        failures: list[BaselineFailure] = []

        if snapshot.repo_kind is RepositoryKind.BROWNFIELD:
            for command in commands:
                if command.kind not in _BASELINE_EXECUTABLE_KINDS:
                    continue
                failure = self._run_command(
                    snapshot,
                    run_id,
                    command,
                    settings.bootstrap.command_timeout_seconds,
                )
                if failure is not None:
                    failures.append(failure)

        languages, package_managers = self._environment_hints(snapshot)
        return BaselineSummary(
            repo_kind=snapshot.repo_kind,
            base_commit=snapshot.base_commit,
            default_branch=snapshot.default_branch,
            languages=languages,
            package_managers=package_managers,
            guidance_refs=guidance,
            commands=commands,
            failures=tuple(failures),
            generated_at=datetime.now(UTC),
        )

    def persist_summary(self, run_id: str, summary: BaselineSummary) -> str:
        artifact_id = f"summary-{summary.base_commit[:20]}"
        payload = summary.model_dump_json(indent=2).encode()
        return self._artifacts.put(run_id, "baseline", artifact_id, payload)

    def _run_command(
        self,
        snapshot: RepositorySnapshot,
        run_id: str,
        command: DetectedCommand,
        timeout_seconds: int,
    ) -> BaselineFailure | None:
        try:
            completed = subprocess.run(
                list(command.argv),
                cwd=snapshot.path,
                check=False,
                text=True,
                capture_output=True,
                timeout=timeout_seconds,
            )
            exit_code = completed.returncode
            stdout = completed.stdout
            stderr = completed.stderr
        except subprocess.TimeoutExpired as exc:
            exit_code = 124
            stdout = self._timeout_text(exc.stdout)
            stderr = self._timeout_text(exc.stderr) + "\ncommand timed out"

        normalized_argv = tuple(self._normalize(token, snapshot.path) for token in command.argv)
        normalized_stdout = self._normalize(stdout, snapshot.path)
        normalized_stderr = self._normalize(stderr, snapshot.path)
        payload = {
            "argv": normalized_argv,
            "command_kind": command.kind.value,
            "exit_code": exit_code,
            "stderr": normalized_stderr,
            "stdout": normalized_stdout,
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        digest = sha256(snapshot.base_commit.encode() + b"\0" + encoded).hexdigest()
        artifact_uri = self._artifacts.put(
            run_id,
            "baseline",
            f"{command.kind.value}-{digest[:20]}",
            encoded,
        )

        if exit_code == 0:
            return None

        signature_source = "\n".join(
            (
                snapshot.base_commit,
                command.kind.value,
                str(exit_code),
                normalized_stdout,
                normalized_stderr,
            )
        )
        failure_digest = sha256(signature_source.encode()).hexdigest()[:20]
        return BaselineFailure(
            failure_id=f"{command.kind.value}:{failure_digest}",
            command_kind=command.kind,
            exit_code=exit_code,
            summary=self._failure_summary(normalized_stdout, normalized_stderr, exit_code),
            artifact_uri=artifact_uri,
            base_commit=snapshot.base_commit,
            pre_existing=True,
        )

    @staticmethod
    def _timeout_text(value: str | bytes | None) -> str:
        if value is None:
            return ""
        return value.decode(errors="replace") if isinstance(value, bytes) else value

    @staticmethod
    def _normalize(value: str, repo: Path) -> str:
        return value.replace(str(repo), "<repo>").replace("\r\n", "\n")

    @staticmethod
    def _failure_summary(stdout: str, stderr: str, exit_code: int) -> str:
        text = stderr.strip() or stdout.strip() or f"command exited {exit_code}"
        compact = " ".join(text.split())
        return compact[:500]

    @staticmethod
    def _environment_hints(snapshot: RepositorySnapshot) -> tuple[tuple[str, ...], tuple[str, ...]]:
        files = snapshot.tracked_files
        languages: set[str] = set()
        managers: set[str] = set()
        if "pyproject.toml" in files or any(path.endswith(".py") for path in files):
            languages.add("python")
        if "package.json" in files or any(
            path.endswith((".js", ".jsx", ".ts", ".tsx")) for path in files
        ):
            languages.add("javascript/typescript")
        if "uv.lock" in files:
            managers.add("uv")
        if "pnpm-lock.yaml" in files:
            managers.add("pnpm")
        return tuple(sorted(languages)), tuple(sorted(managers))
