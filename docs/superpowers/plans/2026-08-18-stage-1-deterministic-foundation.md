# Stage 1 Deterministic Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create the deterministic core of InfiniteInterns: installable package, configuration, durable domain/database models, artifact storage, evidence evaluation, and a minimal operator CLI with no real model calls.

**Architecture:** The stage builds the authority layer before any agents exist. Pydantic models define stable domain contracts, SQLAlchemy/Alembic provide durable state in PostgreSQL schema `ii`, artifacts live outside the database, and the release predicate is a pure deterministic function over validated evidence.

**Tech Stack:** Python 3.13, uv, Pydantic 2, pydantic-settings, SQLAlchemy 2.x async, psycopg 3, Alembic, Typer, Rich, pytest, pytest-asyncio, Ruff, Pyright, PostgreSQL 16.

**Spec:** `docs/architecture/infinite-interns-design.md`

## Global Constraints

- No model or caller can directly write `DONE`; `ReleasePredicate.evaluate()` is the only completion authority.
- Requirements are the completion unit.
- Evidence must include run, requirement, commit, environment hash, verifier version, timestamp, producer, and result.
- Raw artifact bodies do not live in PostgreSQL.
- `BLOCKED`, `FAIL`, and `UNSTABLE` must remain distinguishable.
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
  doctor.py
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
- Produces CLI entry point name `interns` for later tasks.
- Produces Python import package `infinite_interns`.

- [ ] **Step 1: Create the failing package smoke test**

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
  "sqlalchemy[asyncio]>=2.0,<3",
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

- [ ] **Step 5: Sync and run the smoke test**

Run:

```bash
uv sync --dev
uv run pytest tests/unit/test_package.py -q
uv run ruff check .
uv run pyright
```

Expected: all commands pass.

- [ ] **Step 6: Add CI**

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

### Task 2: Define domain IDs, statuses, and immutable contracts

**Files:**
- Create: `src/infinite_interns/domain/enums.py`
- Create: `src/infinite_interns/domain/ids.py`
- Create: `src/infinite_interns/domain/models.py`
- Create: `tests/unit/domain/test_models.py`

**Interfaces:**
- Produces `RunId`, `RequirementId`, `TaskId`, `AttemptId`, `EvidenceId` string aliases.
- Produces `RunStatus`, `RequirementStatus`, `TaskStatus`, `EvidenceResult`, `FailureClass`, `RiskClass`.
- Produces `RunRecord`, `RequirementRecord`, `TaskRecord`, `EvidenceRecord` Pydantic models.

- [ ] **Step 1: Write model-validation tests**

```python
# tests/unit/domain/test_models.py
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from infinite_interns.domain.enums import EvidenceResult, RequirementStatus
from infinite_interns.domain.models import EvidenceRecord


def test_evidence_requires_commit_and_environment_hash() -> None:
    with pytest.raises(ValidationError):
        EvidenceRecord(
            evidence_id="ev_1",
            run_id="run_1",
            requirement_id="REQ-1",
            gate_id="ACC-1",
            result=EvidenceResult.PASS,
            producer="pytest",
            verifier_version="1",
            created_at=datetime.now(UTC),
        )


def test_requirement_status_has_no_done_value() -> None:
    assert set(RequirementStatus) == {
        RequirementStatus.UNVERIFIED,
        RequirementStatus.VERIFIED,
        RequirementStatus.FAILED,
        RequirementStatus.BLOCKED,
        RequirementStatus.UNSTABLE,
    }
```

- [ ] **Step 2: Implement enums**

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
    PASS = "pass"
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

- [ ] **Step 3: Implement typed records with `extra="forbid"`**

```python
# src/infinite_interns/domain/models.py
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from .enums import EvidenceResult, RequirementStatus, RiskClass, RunStatus, TaskStatus


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class EvidenceRecord(StrictModel):
    evidence_id: str
    run_id: str
    requirement_id: str
    gate_id: str
    result: EvidenceResult
    commit_sha: str
    environment_hash: str
    producer: str
    verifier_version: str
    artifact_uri: str | None = None
    created_at: datetime


class RequirementRecord(StrictModel):
    requirement_id: str
    run_id: str
    text: str
    criticality: RiskClass
    status: RequirementStatus = RequirementStatus.UNVERIFIED


class TaskRecord(StrictModel):
    task_id: str
    run_id: str
    title: str
    status: TaskStatus
    risk: RiskClass


class RunRecord(StrictModel):
    run_id: str
    repo: str
    base_commit: str
    status: RunStatus
    started_at: datetime
```

- [ ] **Step 4: Run tests and typecheck**

```bash
uv run pytest tests/unit/domain/test_models.py -q
uv run pyright
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/infinite_interns/domain tests/unit/domain
git commit -m "feat: define deterministic domain contracts"
```

### Task 3: Add configuration profiles and validation

**Files:**
- Create: `src/infinite_interns/config.py`
- Create: `tests/unit/test_config.py`

**Interfaces:**
- Produces `Settings`, `SchedulerSettings`, `BudgetSettings`, `SecuritySettings`, `ModelSettings`.
- Produces `load_settings(path: Path | None) -> Settings`.

- [ ] **Step 1: Write configuration tests**

```python
# tests/unit/test_config.py
from infinite_interns.config import Settings


def test_overnight_defaults_match_architecture() -> None:
    settings = Settings()
    assert settings.scheduler.lease_ttl_seconds == 90
    assert settings.scheduler.heartbeat_seconds == 30
    assert settings.scheduler.max_swe_workers == 4
    assert settings.budget.deadline_hours == 8
    assert settings.budget.hard_model_usd == 300


def test_hard_budget_cannot_be_below_soft_budget() -> None:
    try:
        Settings(budget={"soft_model_usd": 300, "hard_model_usd": 200})
    except ValueError:
        return
    raise AssertionError("invalid budget accepted")
```

- [ ] **Step 2: Implement Pydantic settings**

Use nested models with defaults from the roadmap and a model validator that requires `hard_model_usd >= soft_model_usd` and `lease_ttl_seconds > heartbeat_seconds * 2`.

```python
class SchedulerSettings(BaseModel):
    lease_ttl_seconds: int = 90
    heartbeat_seconds: int = 30
    max_swe_workers: int = 4
    max_browser_workers: int = 2
    max_heavy_test_workers: int = 2
    max_integrations: int = 1


class BudgetSettings(BaseModel):
    deadline_hours: int = 8
    soft_model_usd: float = 200.0
    hard_model_usd: float = 300.0
```

- [ ] **Step 3: Run tests**

```bash
uv run pytest tests/unit/test_config.py -q
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add src/infinite_interns/config.py tests/unit/test_config.py
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
- Test: `tests/integration/db/test_repositories.py`

**Interfaces:**
- Produces `create_engine(database_url) -> AsyncEngine`.
- Produces `RunRepository`, `RequirementRepository`, `TaskRepository`, `EvidenceRepository`, `EventRepository`.
- Database schema name is exactly `ii`.

- [ ] **Step 1: Write an integration test for durable round-trip**

```python
@pytest.mark.asyncio
async def test_requirement_and_evidence_round_trip(db_session):
    reqs = RequirementRepository(db_session)
    evidence = EvidenceRepository(db_session)
    await reqs.add(...)
    await evidence.add(...)
    await db_session.commit()
    assert (await reqs.get("REQ-1")).requirement_id == "REQ-1"
    assert len(await evidence.for_requirement("run_1", "REQ-1")) == 1
```

Use factory helpers that construct complete `RequirementRecord`/`EvidenceRecord` values; do not omit provenance fields.

- [ ] **Step 2: Define SQLAlchemy models**

At minimum create tables for `runs`, `spec_versions`, `requirements`, `tasks`, `task_dependencies`, `attempts`, `evidence`, `review_findings`, `events`, `deployments`, and `budgets`. Use UUID/ULID-compatible `String(64)` identifiers, timezone-aware timestamps, JSONB for typed metadata, and unique constraints preventing duplicate evidence identity `(run_id, requirement_id, gate_id, commit_sha, environment_hash, verifier_version)`.

- [ ] **Step 3: Create Alembic migration and apply it**

```bash
docker compose -f docker-compose.dev.yml up -d postgres
uv run alembic upgrade head
```

Expected: schema `ii` and all tables exist.

- [ ] **Step 4: Implement repositories returning domain records rather than ORM instances**

Repository methods must explicitly translate SQLAlchemy rows to Pydantic domain models. No graph or CLI code may depend on ORM classes.

- [ ] **Step 5: Run integration tests**

```bash
INFINITE_INTERNS_DATABASE_URL='postgresql+psycopg://interns:interns@127.0.0.1:54329/infinite_interns' \
  uv run pytest tests/integration/db -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add alembic.ini migrations src/infinite_interns/db tests/integration/db
git commit -m "feat: add durable control-plane database"
```

### Task 5: Implement artifact URIs and filesystem storage

**Files:**
- Create: `src/infinite_interns/artifacts/base.py`
- Create: `src/infinite_interns/artifacts/filesystem.py`
- Create: `tests/unit/artifacts/test_filesystem.py`

**Interfaces:**
- Produces protocol `ArtifactStore.put(run_id, kind, artifact_id, data) -> str`.
- Produces `ArtifactStore.get(uri) -> bytes`.
- URI format is exactly `artifact://runs/<run_id>/<kind>/<artifact_id>`.

- [ ] **Step 1: Write round-trip and traversal tests**

```python
def test_round_trip(tmp_path):
    store = FilesystemArtifactStore(tmp_path)
    uri = store.put("run_1", "logs", "a1", b"hello")
    assert uri == "artifact://runs/run_1/logs/a1"
    assert store.get(uri) == b"hello"


def test_rejects_path_traversal(tmp_path):
    store = FilesystemArtifactStore(tmp_path)
    with pytest.raises(ValueError):
        store.put("../escape", "logs", "a1", b"x")
```

- [ ] **Step 2: Implement the protocol and filesystem backend**

Use `pathlib.Path.resolve()` containment checks before every write/read. Store metadata such as SHA-256 and byte size alongside artifact database metadata in the calling service, not in sidecar files.

- [ ] **Step 3: Run tests**

```bash
uv run pytest tests/unit/artifacts -q
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add src/infinite_interns/artifacts tests/unit/artifacts
git commit -m "feat: add provenance-safe artifact storage"
```

### Task 6: Implement deterministic evidence evaluation and release predicate

**Files:**
- Create: `src/infinite_interns/evidence/models.py`
- Create: `src/infinite_interns/evidence/service.py`
- Create: `src/infinite_interns/evidence/predicate.py`
- Create: `tests/unit/evidence/test_predicate.py`
- Create: `tests/unit/evidence/test_service.py`

**Interfaces:**
- Produces `GateRequirement(gate_id: str, mandatory: bool, requirement_id: str | None)`.
- Produces `ReleaseEvaluation(status, failing_gate_ids, stale_evidence_ids)`.
- Produces `ReleasePredicate.evaluate(policy, evidence, current_commit, environment_hash) -> ReleaseEvaluation`.
- Produces `EvidenceService.requirement_status(...) -> RequirementStatus`.

- [ ] **Step 1: Write the false-DONE prevention tests first**

```python
@pytest.mark.parametrize("bad_result", ["fail", "blocked", "unstable", "infra_error"])
def test_mandatory_gate_prevents_pass(bad_result):
    evaluation = evaluate_fixture_with_one_bad_mandatory_gate(bad_result)
    assert evaluation.status != "pass"


def test_stale_commit_prevents_pass():
    evaluation = evaluate_fixture(evidence_commit="abc", current_commit="def")
    assert evaluation.status != "pass"
    assert evaluation.stale_evidence_ids


def test_only_all_current_mandatory_gates_pass():
    evaluation = evaluate_fully_green_fixture()
    assert evaluation.status == "pass"
```

- [ ] **Step 2: Implement pure evaluation logic**

The predicate must not write the database. It receives immutable inputs and returns immutable output. Rules:

```text
missing mandatory evidence -> FAIL
mandatory FAIL -> FAIL
mandatory BLOCKED -> BLOCKED unless another mandatory FAIL exists
mandatory UNSTABLE -> UNSTABLE unless FAIL/BLOCKED dominates by policy
INFRA_ERROR -> not PASS
wrong commit/environment -> stale, not PASS
all mandatory current PASS -> PASS
```

- [ ] **Step 3: Implement requirement-level status aggregation**

A requirement is `VERIFIED` only when every mandatory gate mapped to that requirement has current `PASS` evidence. Do not derive `VERIFIED` from task state.

- [ ] **Step 4: Run evidence tests**

```bash
uv run pytest tests/unit/evidence -q
```

Expected: PASS, including zero false-pass fixtures.

- [ ] **Step 5: Commit**

```bash
git add src/infinite_interns/evidence tests/unit/evidence
git commit -m "feat: add deterministic evidence authority"
```

### Task 7: Add doctor/status CLI and stage acceptance test

**Files:**
- Create: `src/infinite_interns/doctor.py`
- Create: `src/infinite_interns/cli.py`
- Create: `tests/unit/test_doctor.py`
- Create: `tests/integration/test_stage1_acceptance.py`
- Modify: `AGENTS.md`
- Modify: `README.md`

**Interfaces:**
- Produces commands `interns doctor` and `interns status --run <id>`.
- `doctor` checks Python version, Git executable, Docker executable, DB connectivity, artifact root writability.

- [ ] **Step 1: Write a doctor unit test using injected checks**

```python
def test_doctor_reports_failed_dependency():
    report = run_doctor(checks=[lambda: CheckResult("git", False, "missing")])
    assert report.ready is False
    assert report.results[0].name == "git"
```

- [ ] **Step 2: Implement Typer/Rich CLI**

```python
import typer

app = typer.Typer(no_args_is_help=True)


@app.command()
def doctor() -> None:
    ...


@app.command()
def status(run: str = typer.Option(..., "--run")) -> None:
    ...
```

The command implementation may format data, but readiness/status decisions come from typed services.

- [ ] **Step 3: Write the Stage 1 acceptance test**

The integration test must:

1. create a run and two requirements,
2. persist mandatory gate policy,
3. add green evidence for all but one gate,
4. prove release is not `PASS`,
5. add final current-commit evidence,
6. prove release becomes `PASS`,
7. add newer commit identity without new evidence,
8. prove release becomes non-pass again.

- [ ] **Step 4: Run full Stage 1 gate**

```bash
uv run ruff check .
uv run pyright
uv run pytest tests/unit -q
INFINITE_INTERNS_DATABASE_URL='postgresql+psycopg://interns:interns@127.0.0.1:54329/infinite_interns' \
  uv run pytest tests/integration -q
```

Expected: all PASS.

- [ ] **Step 5: Update repo navigation**

Update `AGENTS.md` so the implementation plan and test commands are discoverable. Update `README.md` status to `Stage 1 implementation ready` and document `uv sync`, PostgreSQL startup, and `interns doctor`.

- [ ] **Step 6: Commit**

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

Manual inspection requirement: search for writes of `RunStatus.DONE`. Stage 1 implementation must contain no such write outside the release-transition service added in a later stage; the predicate may return `PASS`, but nothing yet transitions a run to `DONE`.
