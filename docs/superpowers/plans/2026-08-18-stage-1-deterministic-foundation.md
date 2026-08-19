# Stage 1 Deterministic Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create the deterministic core of InfiniteInterns: installable package, validated configuration, durable domain/database models, artifact storage, evidence evaluation, and a minimal operator CLI with no real model calls.

**Architecture:** The authority layer is built before any agents exist. Pydantic models define stable domain contracts, SQLAlchemy/Alembic provide durable state in PostgreSQL schema `ii`, large artifacts live outside the database, and the release predicate is a pure deterministic function over current provenance-aware evidence.

**Tech Stack:** Python 3.13, uv, Pydantic 2, pydantic-settings, SQLAlchemy 2.x async, psycopg 3, Alembic, Typer, Rich, pytest, pytest-asyncio, Ruff, Pyright, PostgreSQL 16.

**Spec:** `docs/architecture/infinite-interns-design.md`

## Global Constraints

- No model or ordinary caller can directly write `DONE`.
- Requirements are the unit of completion.
- Evidence must include run, requirement, gate, commit, environment hash, verifier version, timestamp, producer, and result.
- Raw artifact bodies do not live in PostgreSQL.
- `BLOCKED`, `FAIL`, `UNSTABLE`, and `INFRA_ERROR` remain distinct outcomes.
- Stage 1 has no live LLM/provider dependency.

---

## File structure locked by this stage

```text
pyproject.toml
.python-version
alembic.ini
migrations/
  env.py
  versions/0001_initial_control_plane.py
src/infinite_interns/
  __init__.py
  cli.py
  config.py
  doctor.py
  domain/
    __init__.py
    enums.py
    ids.py
    models.py
  db/
    __init__.py
    base.py
    engine.py
    models.py
    repositories.py
  artifacts/
    __init__.py
    base.py
    filesystem.py
  evidence/
    __init__.py
    models.py
    predicate.py
    service.py
tests/
  unit/
  integration/db/
docker-compose.dev.yml
.github/workflows/ci.yml
```

### Task 1: Bootstrap the Python project and quality gates

**Files:**
- Create: `pyproject.toml`
- Create: `.python-version`
- Create: `src/infinite_interns/__init__.py`
- Create: `tests/unit/test_package.py`
- Create: `.github/workflows/ci.yml`
- Create: `docker-compose.dev.yml`

**Interfaces:**
- Produces CLI entry point `interns`.
- Produces import package `infinite_interns`.

- [ ] **Step 1: Write the failing package smoke test**

```python
# tests/unit/test_package.py
from infinite_interns import __version__


def test_package_has_version() -> None:
    assert __version__ == "0.1.0"
```

- [ ] **Step 2: Add project metadata and dependencies**

```toml
# pyproject.toml
[project]
name = "infinite-interns"
version = "0.1.0"
description = "Evidence-gated autonomous software engineering factory"
readme = "README.md"
requires-python = ">=3.13,<3.14"
dependencies = [
  "alembic>=1.16,<2",
  "pydantic>=2.11,<3",
  "pydantic-settings>=2.10,<3",
  "psycopg[binary,pool]>=3.2,<4",
  "rich>=14,<15",
  "sqlalchemy>=2.0,<3",
  "typer>=0.16,<1",
]

[project.scripts]
interns = "infinite_interns.cli:app"

[dependency-groups]
dev = [
  "pyright>=1.1.400,<2",
  "pytest>=8.4,<9",
  "pytest-asyncio>=1.1,<2",
  "ruff>=0.12,<1",
]

[build-system]
requires = ["uv_build>=0.12,<0.13"]
build-backend = "uv_build"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.ruff]
target-version = "py313"
line-length = 100

[tool.pyright]
pythonVersion = "3.13"
typeCheckingMode = "strict"
include = ["src", "tests"]
```

```text
# .python-version
3.13
```

- [ ] **Step 3: Add the minimal package implementation**

```python
# src/infinite_interns/__init__.py
__version__ = "0.1.0"
```

- [ ] **Step 4: Add local PostgreSQL**

```yaml
# docker-compose.dev.yml
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: infinite_interns
      POSTGRES_USER: interns
      POSTGRES_PASSWORD: interns
    ports:
      - "54329:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U interns -d infinite_interns"]
      interval: 2s
      timeout: 2s
      retries: 20
```

- [ ] **Step 5: Sync and verify**

```bash
uv sync --dev
uv run pytest tests/unit/test_package.py -q
uv run ruff check .
uv run pyright
```

Expected: all commands pass.

- [ ] **Step 6: Add baseline CI**

```yaml
# .github/workflows/ci.yml
name: ci
on:
  push:
  pull_request:

jobs:
  python:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v6
        with:
          python-version: "3.13"
      - run: uv sync --dev --locked
      - run: uv run ruff check .
      - run: uv run pyright
      - run: uv run pytest tests/unit -q
```

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml .python-version src tests .github docker-compose.dev.yml uv.lock
git commit -m "build: bootstrap InfiniteInterns Python project"
```

### Task 2: Define IDs, statuses, and immutable domain contracts

**Files:**
- Create: `src/infinite_interns/domain/__init__.py`
- Create: `src/infinite_interns/domain/ids.py`
- Create: `src/infinite_interns/domain/enums.py`
- Create: `src/infinite_interns/domain/models.py`
- Create: `tests/unit/domain/test_models.py`

**Interfaces:**
- Produces `RunId`, `RequirementId`, `TaskId`, `AttemptId`, `EvidenceId`.
- Produces `RunStatus`, `RequirementStatus`, `TaskStatus`, `EvidenceResult`, `FailureClass`, `RiskClass`.
- Produces `RunRecord`, `RequirementRecord`, `TaskRecord`, `EvidenceRecord`.

- [ ] **Step 1: Write domain validation tests**

```python
# tests/unit/domain/test_models.py
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from infinite_interns.domain.enums import EvidenceResult, RequirementStatus
from infinite_interns.domain.models import EvidenceRecord


def test_evidence_requires_commit_and_environment_hash() -> None:
    with pytest.raises(ValidationError):
        EvidenceRecord.model_validate(
            {
                "evidence_id": "ev_1",
                "run_id": "run_1",
                "requirement_id": "REQ-1",
                "gate_id": "ACC-1",
                "result": EvidenceResult.PASS,
                "producer": "pytest",
                "verifier_version": "1",
                "created_at": datetime.now(UTC),
            }
        )


def test_requirement_status_has_no_done_value() -> None:
    assert {status.value for status in RequirementStatus} == {
        "unverified",
        "verified",
        "failed",
        "blocked",
        "unstable",
    }
```

- [ ] **Step 2: Implement typed IDs**

```python
# src/infinite_interns/domain/ids.py
from typing import NewType

RunId = NewType("RunId", str)
RequirementId = NewType("RequirementId", str)
TaskId = NewType("TaskId", str)
AttemptId = NewType("AttemptId", str)
EvidenceId = NewType("EvidenceId", str)
```

- [ ] **Step 3: Implement statuses**

```python
# src/infinite_interns/domain/enums.py
from enum import StrEnum


class RunStatus(StrEnum):
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    FAILED = "failed"
    BLOCKED = "blocked"
    UNSTABLE = "unstable"
    DONE = "done"


class RequirementStatus(StrEnum):
    UNVERIFIED = "unverified"
    VERIFIED = "verified"
    FAILED = "failed"
    BLOCKED = "blocked"
    UNSTABLE = "unstable"


class TaskStatus(StrEnum):
    PLANNED = "planned"
    READY = "ready"
    CLAIMED = "claimed"
    RUNNING = "running"
    VERIFYING = "verifying"
    REVIEWING = "reviewing"
    REPAIR = "repair"
    CANDIDATE = "candidate"
    INTEGRATING = "integrating"
    VERIFIED = "verified"
    DONE = "done"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"
    SUPERSEDED = "superseded"


class EvidenceResult(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    BLOCKED = "blocked"
    UNSTABLE = "unstable"
    INFRA_ERROR = "infra_error"


class FailureClass(StrEnum):
    INFRA_TRANSIENT = "infra_transient"
    ENGINEERING_FAILURE = "engineering_failure"
    EXTERNAL_BLOCKER = "external_blocker"
    CONTROL_PLANE_FAILURE = "control_plane_failure"


class RiskClass(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
```

- [ ] **Step 4: Implement immutable records**

```python
# src/infinite_interns/domain/models.py
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from .enums import EvidenceResult, RequirementStatus, RiskClass, RunStatus, TaskStatus
from .ids import EvidenceId, RequirementId, RunId, TaskId


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class EvidenceRecord(StrictModel):
    evidence_id: EvidenceId
    run_id: RunId
    requirement_id: RequirementId
    gate_id: str
    result: EvidenceResult
    commit_sha: str
    environment_hash: str
    producer: str
    verifier_version: str
    artifact_uri: str | None = None
    created_at: datetime


class RequirementRecord(StrictModel):
    requirement_id: RequirementId
    run_id: RunId
    text: str
    criticality: RiskClass
    status: RequirementStatus = RequirementStatus.UNVERIFIED


class TaskRecord(StrictModel):
    task_id: TaskId
    run_id: RunId
    title: str
    status: TaskStatus
    risk: RiskClass


class RunRecord(StrictModel):
    run_id: RunId
    repo: str
    base_commit: str
    current_commit: str
    last_green_commit: str
    status: RunStatus
    started_at: datetime
```

- [ ] **Step 5: Verify and commit**

```bash
uv run pytest tests/unit/domain/test_models.py -q
uv run pyright
git add src/infinite_interns/domain tests/unit/domain
git commit -m "feat: define deterministic domain contracts"
```

### Task 3: Add validated configuration profiles

**Files:**
- Create: `src/infinite_interns/config.py`
- Create: `tests/unit/test_config.py`

**Interfaces:**
- Produces `Settings`, `SchedulerSettings`, `BudgetSettings`, `SecuritySettings`, `ModelSettings`.
- Produces `load_settings(path: Path | None = None) -> Settings`.

- [ ] **Step 1: Write configuration tests**

```python
# tests/unit/test_config.py
import pytest

from infinite_interns.config import Settings


def test_overnight_defaults_match_architecture() -> None:
    settings = Settings()
    assert settings.scheduler.lease_ttl_seconds == 90
    assert settings.scheduler.heartbeat_seconds == 30
    assert settings.scheduler.max_swe_workers == 4
    assert settings.budget.deadline_hours == 8
    assert settings.budget.hard_model_usd == 300.0
    assert settings.security.profile == "overnight"
    assert settings.models.implementer == "codex"


def test_hard_budget_cannot_be_below_soft_budget() -> None:
    with pytest.raises(ValueError):
        Settings.model_validate(
            {"budget": {"soft_model_usd": 300.0, "hard_model_usd": 200.0}}
        )
```

- [ ] **Step 2: Implement the complete settings model**

```python
# src/infinite_interns/config.py
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, model_validator


class SchedulerSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    lease_ttl_seconds: int = 90
    heartbeat_seconds: int = 30
    max_swe_workers: int = 4
    max_browser_workers: int = 2
    max_heavy_test_workers: int = 2
    max_integrations: int = 1


class BudgetSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    deadline_hours: int = 8
    soft_model_usd: float = 200.0
    hard_model_usd: float = 300.0


class SecuritySettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    profile: Literal["locked", "overnight", "trusted-production"] = "overnight"


class ModelSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    implementer: str = "codex"
    reviewer: str = "codex"
    adversary: str = "kimi-k3"
    diagnostician: str = "deepseek-v4-pro"


class Settings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scheduler: SchedulerSettings = SchedulerSettings()
    budget: BudgetSettings = BudgetSettings()
    security: SecuritySettings = SecuritySettings()
    models: ModelSettings = ModelSettings()

    @model_validator(mode="after")
    def validate_relationships(self) -> "Settings":
        if self.budget.hard_model_usd < self.budget.soft_model_usd:
            raise ValueError("hard model budget must be >= soft model budget")
        if self.scheduler.lease_ttl_seconds <= self.scheduler.heartbeat_seconds * 2:
            raise ValueError("lease TTL must exceed two heartbeat intervals")
        return self


def load_settings(path: Path | None = None) -> Settings:
    if path is None:
        return Settings()
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return Settings.model_validate(data)
```

Add `pyyaml>=6.0,<7` to project dependencies and relock.

- [ ] **Step 3: Verify and commit**

```bash
uv lock
uv run pytest tests/unit/test_config.py -q
uv run pyright
git add pyproject.toml uv.lock src/infinite_interns/config.py tests/unit/test_config.py
git commit -m "feat: add validated factory configuration"
```

### Task 4: Create the PostgreSQL schema and repositories

**Files:**
- Create: `alembic.ini`
- Create: `migrations/env.py`
- Create: `migrations/versions/0001_initial_control_plane.py`
- Create: `src/infinite_interns/db/base.py`
- Create: `src/infinite_interns/db/engine.py`
- Create: `src/infinite_interns/db/models.py`
- Create: `src/infinite_interns/db/repositories.py`
- Create: `tests/integration/db/conftest.py`
- Create: `tests/integration/db/test_repositories.py`

**Interfaces:**
- Produces `create_async_engine_for(database_url: str) -> AsyncEngine`.
- Produces `RunRepository`, `RequirementRepository`, `TaskRepository`, `EvidenceRepository`, `EventRepository`.
- Database schema is exactly `ii`.

- [ ] **Step 1: Write a complete durable round-trip test**

```python
# tests/integration/db/test_repositories.py
from datetime import UTC, datetime

from infinite_interns.domain.enums import EvidenceResult, RequirementStatus, RiskClass
from infinite_interns.domain.ids import EvidenceId, RequirementId, RunId
from infinite_interns.domain.models import EvidenceRecord, RequirementRecord


async def test_requirement_and_evidence_round_trip(db_session) -> None:
    run_id = RunId("run_1")
    requirement = RequirementRecord(
        requirement_id=RequirementId("REQ-1"),
        run_id=run_id,
        text="User can save a job",
        criticality=RiskClass.HIGH,
        status=RequirementStatus.UNVERIFIED,
    )
    record = EvidenceRecord(
        evidence_id=EvidenceId("ev_1"),
        run_id=run_id,
        requirement_id=RequirementId("REQ-1"),
        gate_id="ACC-SAVE-1",
        result=EvidenceResult.PASS,
        commit_sha="abc123",
        environment_hash="env123",
        producer="pytest",
        verifier_version="1",
        created_at=datetime.now(UTC),
    )

    await RequirementRepository(db_session).add(requirement)
    await EvidenceRepository(db_session).add(record)
    await db_session.commit()

    loaded = await RequirementRepository(db_session).get(RequirementId("REQ-1"))
    evidence = await EvidenceRepository(db_session).for_requirement(run_id, RequirementId("REQ-1"))
    assert loaded == requirement
    assert evidence == [record]
```

- [ ] **Step 2: Implement database base/engine**

```python
# src/infinite_interns/db/base.py
from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

metadata = MetaData(schema="ii")


class Base(DeclarativeBase):
    metadata = metadata
```

```python
# src/infinite_interns/db/engine.py
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine


def create_async_engine_for(database_url: str) -> AsyncEngine:
    return create_async_engine(database_url, pool_pre_ping=True)
```

- [ ] **Step 3: Define the initial ORM schema**

Create explicit mapped classes for `runs`, `spec_versions`, `requirements`, `tasks`, `task_dependencies`, `attempts`, `evidence`, `review_findings`, `events`, `deployments`, and `budgets`. Use `String(64)` IDs, `DateTime(timezone=True)`, `JSONB` metadata, foreign keys within schema `ii`, and this evidence uniqueness constraint:

```python
UniqueConstraint(
    "run_id",
    "requirement_id",
    "gate_id",
    "commit_sha",
    "environment_hash",
    "verifier_version",
    name="uq_evidence_identity",
)
```

The `runs` row contains at least `id`, `repo`, `base_commit`, `current_commit`, `last_green_commit`, `status`, `started_at`, `updated_at`. The `requirements` row contains `id`, `run_id`, `text`, `criticality`, `status`. The `tasks` row contains `id`, `run_id`, `title`, `risk`, `status`. The `evidence` row contains every field from `EvidenceRecord` plus JSONB metadata.

- [ ] **Step 4: Create and apply Alembic migration**

```bash
docker compose -f docker-compose.dev.yml up -d postgres
uv run alembic upgrade head
```

Expected: schema `ii` and all declared tables exist.

- [ ] **Step 5: Implement repositories**

Repository methods accept/return domain records only. At minimum implement:

```text
RunRepository.add/get/update_status/update_commits
RequirementRepository.add/get/list_for_run/update_status
TaskRepository.add/get/list_for_run/update_status
EvidenceRepository.add/for_requirement/list_for_run
EventRepository.append/list_for_run
```

Every method explicitly maps ORM rows to Pydantic domain models; graph/CLI code never imports ORM classes.

- [ ] **Step 6: Verify and commit**

```bash
INFINITE_INTERNS_DATABASE_URL='postgresql+psycopg://interns:interns@127.0.0.1:54329/infinite_interns' \
  uv run pytest tests/integration/db -q
uv run pyright
git add alembic.ini migrations src/infinite_interns/db tests/integration/db
git commit -m "feat: add durable control-plane database"
```

### Task 5: Implement artifact URIs and filesystem storage

**Files:**
- Create: `src/infinite_interns/artifacts/base.py`
- Create: `src/infinite_interns/artifacts/filesystem.py`
- Create: `tests/unit/artifacts/test_filesystem.py`

**Interfaces:**
- `ArtifactStore.put(run_id: str, kind: str, artifact_id: str, data: bytes) -> str`.
- `ArtifactStore.get(uri: str) -> bytes`.
- URI format is exactly `artifact://runs/<run_id>/<kind>/<artifact_id>`.

- [ ] **Step 1: Write round-trip and traversal tests**

```python
# tests/unit/artifacts/test_filesystem.py
import pytest

from infinite_interns.artifacts.filesystem import FilesystemArtifactStore


def test_round_trip(tmp_path) -> None:
    store = FilesystemArtifactStore(tmp_path)
    uri = store.put("run_1", "logs", "a1", b"hello")
    assert uri == "artifact://runs/run_1/logs/a1"
    assert store.get(uri) == b"hello"


def test_rejects_path_traversal(tmp_path) -> None:
    store = FilesystemArtifactStore(tmp_path)
    with pytest.raises(ValueError):
        store.put("../escape", "logs", "a1", b"x")
```

- [ ] **Step 2: Implement the protocol and filesystem backend**

Use a `typing.Protocol` whose methods have concrete signatures and implement `FilesystemArtifactStore`. Validate `run_id`, `kind`, and `artifact_id` as single path segments; use `Path.resolve()` containment checks before every read/write. Compute SHA-256 and byte size in the calling evidence service for DB metadata.

- [ ] **Step 3: Verify and commit**

```bash
uv run pytest tests/unit/artifacts -q
git add src/infinite_interns/artifacts tests/unit/artifacts
git commit -m "feat: add provenance-safe artifact storage"
```

### Task 6: Implement deterministic evidence evaluation

**Files:**
- Create: `src/infinite_interns/evidence/models.py`
- Create: `src/infinite_interns/evidence/service.py`
- Create: `src/infinite_interns/evidence/predicate.py`
- Create: `tests/unit/evidence/test_predicate.py`
- Create: `tests/unit/evidence/test_service.py`

**Interfaces:**
- `GateRequirement(gate_id: str, mandatory: bool, requirement_id: RequirementId | None)`.
- `ReleaseEvaluation(status: EvidenceResult, failing_gate_ids: tuple[str, ...], stale_evidence_ids: tuple[EvidenceId, ...])`.
- `ReleasePredicate.evaluate(policy: ReleasePolicy, evidence: Sequence[EvidenceRecord], current_commit: str, environment_hash: str) -> ReleaseEvaluation`.
- `EvidenceService.requirement_status(requirement_id: RequirementId, gates: Sequence[GateRequirement], evidence: Sequence[EvidenceRecord], current_commit: str, environment_hash: str) -> RequirementStatus`.

- [ ] **Step 1: Write false-PASS prevention tests first**

```python
# tests/unit/evidence/test_predicate.py
import pytest

from infinite_interns.domain.enums import EvidenceResult


@pytest.mark.parametrize(
    "bad_result",
    [
        EvidenceResult.FAIL,
        EvidenceResult.BLOCKED,
        EvidenceResult.UNSTABLE,
        EvidenceResult.INFRA_ERROR,
    ],
)
def test_mandatory_gate_prevents_pass(bad_result: EvidenceResult) -> None:
    evaluation = release_fixture(one_gate_result=bad_result)
    assert evaluation.status is not EvidenceResult.PASS


def test_stale_commit_prevents_pass() -> None:
    evaluation = release_fixture(evidence_commit="abc", current_commit="def")
    assert evaluation.status is not EvidenceResult.PASS
    assert len(evaluation.stale_evidence_ids) == 1


def test_only_all_current_mandatory_gates_pass() -> None:
    evaluation = release_fixture()
    assert evaluation.status is EvidenceResult.PASS
```

Create a complete local `release_fixture()` helper in the same test module that builds two mandatory `GateRequirement` objects and full `EvidenceRecord` values; no external fixture magic.

- [ ] **Step 2: Implement pure evaluation logic**

The predicate performs no database writes. Apply this precedence:

```text
any mandatory FAIL          -> FAIL
else any mandatory BLOCKED  -> BLOCKED
else any mandatory UNSTABLE -> UNSTABLE
else any missing/stale/INFRA_ERROR mandatory gate -> FAIL
else all mandatory current PASS -> PASS
```

Optional gate failures remain visible in the evaluation but cannot by themselves turn a policy that marks them optional into failure.

- [ ] **Step 3: Implement requirement aggregation**

A requirement is `VERIFIED` only when every mandatory gate mapped to that requirement has current `PASS` evidence. Task status is never an input to this method.

- [ ] **Step 4: Verify and commit**

```bash
uv run pytest tests/unit/evidence -q
uv run pyright
git add src/infinite_interns/evidence tests/unit/evidence
git commit -m "feat: add deterministic evidence authority"
```

### Task 7: Add doctor/status CLI and Stage 1 acceptance test

**Files:**
- Create: `src/infinite_interns/doctor.py`
- Create: `src/infinite_interns/cli.py`
- Create: `tests/unit/test_doctor.py`
- Create: `tests/integration/test_stage1_acceptance.py`
- Modify: `AGENTS.md`
- Modify: `README.md`

**Interfaces:**
- Produces `interns doctor` and `interns status --run <id>`.
- `doctor` checks Python version, Git executable, Docker executable, DB connectivity, and artifact-root writability.

- [ ] **Step 1: Write doctor unit test with injected checks**

```python
# tests/unit/test_doctor.py
from infinite_interns.doctor import CheckResult, run_doctor


def test_doctor_reports_failed_dependency() -> None:
    report = run_doctor(checks=(lambda: CheckResult("git", False, "missing"),))
    assert report.ready is False
    assert report.results[0].name == "git"
```

- [ ] **Step 2: Implement concrete doctor models/service**

```python
# src/infinite_interns/doctor.py
from collections.abc import Callable, Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class CheckResult:
    name: str
    ok: bool
    detail: str


@dataclass(frozen=True)
class DoctorReport:
    results: tuple[CheckResult, ...]

    @property
    def ready(self) -> bool:
        return all(result.ok for result in self.results)


def run_doctor(checks: Sequence[Callable[[], CheckResult]]) -> DoctorReport:
    return DoctorReport(tuple(check() for check in checks))
```

Add concrete check functions using `sys.version_info`, `shutil.which("git")`, `shutil.which("docker")`, an async DB probe wrapper, and a temporary write/delete under artifact root.

- [ ] **Step 3: Implement Typer/Rich CLI**

```python
# src/infinite_interns/cli.py
from typing import Annotated

import typer
from rich.console import Console

app = typer.Typer(no_args_is_help=True)
console = Console()


@app.command()
def doctor() -> None:
    report = build_default_doctor_report()
    for result in report.results:
        console.print(f"{result.name}: {'PASS' if result.ok else 'FAIL'} - {result.detail}")
    if not report.ready:
        raise typer.Exit(code=1)


@app.command()
def status(run: Annotated[str, typer.Option("--run")]) -> None:
    record = load_run_status(run)
    console.print(f"{record.run_id}: {record.status.value}")
```

`build_default_doctor_report()` and `load_run_status()` are thin functions in the same module/service wiring layer that construct settings/repositories and delegate to typed services; tests inject fakes rather than patching database internals.

- [ ] **Step 4: Write the Stage 1 acceptance test**

The integration test must:

1. create a run and two requirements,
2. create a release policy with mandatory gates for both,
3. persist current green evidence for all but one gate,
4. assert release is not `PASS`,
5. add the final current-commit evidence,
6. assert release is `PASS`,
7. advance `current_commit` without new evidence,
8. assert the same release is no longer `PASS` because evidence is stale.

- [ ] **Step 5: Run full Stage 1 gate**

```bash
uv run ruff check .
uv run pyright
uv run pytest tests/unit -q
INFINITE_INTERNS_DATABASE_URL='postgresql+psycopg://interns:interns@127.0.0.1:54329/infinite_interns' \
  uv run pytest tests/integration -q
```

Expected: all PASS.

- [ ] **Step 6: Update repo navigation and commit**

Update `AGENTS.md` to link the roadmap/Stage 1 plan and verification commands. Update `README.md` status to `Stage 1 implementation ready` and document `uv sync`, PostgreSQL startup, and `interns doctor`.

```bash
git add src/infinite_interns/cli.py src/infinite_interns/doctor.py tests README.md AGENTS.md
git commit -m "feat: complete deterministic foundation"
```

## Stage 1 completion gate

Do not start Stage 2 until all of these are green on the integration branch:

```bash
uv run ruff check .
uv run pyright
uv run pytest tests/unit -q
uv run pytest tests/integration -q
```

Search production Python code for `RunStatus.DONE`. Stage 1 must contain **zero writes** to `RunStatus.DONE`; at this stage the predicate may return `EvidenceResult.PASS`, but the sole run-completion transition is intentionally added and tested in Stage 4.
