"""Environment readiness checks for InfiniteInterns."""

import os
import shutil
import sys
import tempfile
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

import psycopg


@dataclass(frozen=True)
class CheckResult:
    name: str
    ok: bool
    detail: str


@dataclass(frozen=True)
class DoctorReport:
    ready: bool
    results: tuple[CheckResult, ...]


DoctorCheck = Callable[[], CheckResult]


def run_doctor(checks: Iterable[DoctorCheck] | None = None) -> DoctorReport:
    selected = tuple(checks) if checks is not None else default_checks()
    results = tuple(check() for check in selected)
    return DoctorReport(ready=all(result.ok for result in results), results=results)


def default_checks() -> tuple[DoctorCheck, ...]:
    return (
        _check_python,
        lambda: _check_executable("git"),
        lambda: _check_executable("docker"),
        _check_database,
        _check_artifact_root,
    )


def _check_python() -> CheckResult:
    version = sys.version_info
    ok = version.major == 3 and version.minor == 13
    return CheckResult(
        name="python",
        ok=ok,
        detail=f"{version.major}.{version.minor}.{version.micro}",
    )


def _check_executable(name: str) -> CheckResult:
    path = shutil.which(name)
    if path is None:
        return CheckResult(name=name, ok=False, detail="not found")
    return CheckResult(name=name, ok=True, detail=path)


def _check_database() -> CheckResult:
    database_url = os.environ.get("INFINITE_INTERNS_DATABASE_URL")
    if not database_url:
        return CheckResult(
            name="database",
            ok=False,
            detail="INFINITE_INTERNS_DATABASE_URL not set",
        )

    dsn = database_url.replace("postgresql+psycopg://", "postgresql://", 1)
    try:
        with (
            psycopg.connect(dsn, connect_timeout=3) as connection,
            connection.cursor() as cursor,
        ):
            cursor.execute("SELECT 1")
            row = cursor.fetchone()
    except psycopg.Error as exc:
        return CheckResult(name="database", ok=False, detail=exc.__class__.__name__)

    ok = row == (1,)
    return CheckResult(name="database", ok=ok, detail="connected" if ok else "probe failed")


def _check_artifact_root() -> CheckResult:
    root = Path(os.environ.get("INFINITE_INTERNS_ARTIFACT_ROOT", ".infinite-interns/artifacts"))
    try:
        root.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=root, prefix="doctor-", delete=True):
            pass
    except OSError as exc:
        return CheckResult(name="artifact-root", ok=False, detail=exc.__class__.__name__)
    return CheckResult(name="artifact-root", ok=True, detail=str(root.resolve()))
