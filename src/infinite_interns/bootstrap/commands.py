"""Deterministic command detection from supported project manifests."""

import json
from pathlib import Path
from typing import Any, cast

from infinite_interns.bootstrap.models import CommandKind, DetectedCommand
from infinite_interns.config import BootstrapSettings


class CommandDetector:
    def detect(self, repo: Path, config: BootstrapSettings) -> tuple[DetectedCommand, ...]:
        detected: list[DetectedCommand] = []
        detected.extend(self._detect_python(repo))
        detected.extend(self._detect_node(repo))

        overrides = {CommandKind(kind): argv for kind, argv in config.command_overrides.items()}
        if overrides:
            detected = [command for command in detected if command.kind not in overrides]
            detected.extend(
                DetectedCommand(kind=kind, argv=argv, source="config", confidence=1.0)
                for kind, argv in overrides.items()
            )

        order = {kind: index for index, kind in enumerate(CommandKind)}
        return tuple(sorted(detected, key=lambda command: (order[command.kind], command.argv)))

    @staticmethod
    def _detect_python(repo: Path) -> list[DetectedCommand]:
        manifest = repo / "pyproject.toml"
        if not manifest.is_file():
            return []

        text = manifest.read_text(encoding="utf-8").lower()
        commands: list[DetectedCommand] = []
        if (repo / "uv.lock").is_file():
            commands.append(
                DetectedCommand(
                    kind=CommandKind.INSTALL,
                    argv=("uv", "sync", "--frozen"),
                    source="pyproject.toml+uv.lock",
                    confidence=1.0,
                )
            )
        if "pytest" in text or (repo / "pytest.ini").is_file():
            commands.append(
                DetectedCommand(
                    kind=CommandKind.UNIT,
                    argv=("uv", "run", "pytest"),
                    source="pyproject.toml",
                    confidence=0.95,
                )
            )
        if "ruff" in text:
            commands.append(
                DetectedCommand(
                    kind=CommandKind.LINT,
                    argv=("uv", "run", "ruff", "check", "."),
                    source="pyproject.toml",
                    confidence=0.95,
                )
            )
        if "pyright" in text:
            commands.append(
                DetectedCommand(
                    kind=CommandKind.TYPECHECK,
                    argv=("uv", "run", "pyright"),
                    source="pyproject.toml",
                    confidence=0.95,
                )
            )
        return commands

    @staticmethod
    def _detect_node(repo: Path) -> list[DetectedCommand]:
        manifest = repo / "package.json"
        if not manifest.is_file():
            return []

        raw = cast(dict[str, Any], json.loads(manifest.read_text(encoding="utf-8")))
        scripts_raw = raw.get("scripts", {})
        scripts = cast(dict[str, Any], scripts_raw) if isinstance(scripts_raw, dict) else {}
        commands: list[DetectedCommand] = []
        if (repo / "pnpm-lock.yaml").is_file():
            commands.append(
                DetectedCommand(
                    kind=CommandKind.INSTALL,
                    argv=("pnpm", "install", "--frozen-lockfile"),
                    source="package.json+pnpm-lock.yaml",
                    confidence=1.0,
                )
            )

        script_map = (
            ("build", CommandKind.BUILD, ("pnpm", "run", "build")),
            ("typecheck", CommandKind.TYPECHECK, ("pnpm", "run", "typecheck")),
            ("lint", CommandKind.LINT, ("pnpm", "run", "lint")),
            ("test", CommandKind.UNIT, ("pnpm", "test")),
            ("integration", CommandKind.INTEGRATION, ("pnpm", "run", "integration")),
            ("start", CommandKind.START, ("pnpm", "run", "start")),
        )
        for script_name, kind, argv in script_map:
            if script_name in scripts:
                commands.append(
                    DetectedCommand(
                        kind=kind,
                        argv=argv,
                        source="package.json",
                        confidence=0.95,
                    )
                )
        return commands
