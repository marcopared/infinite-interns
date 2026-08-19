# Stage 2 Orchestration and Execution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add durable LangGraph orchestration, deterministic DAG scheduling, leases/fencing, isolated Docker/worktree execution, serialized integration, and crash recovery using fake workers only.

**Architecture:** LangGraph Agent Server hosts the parent factory graph and custom FastAPI routes. PostgreSQL remains authoritative for tasks/evidence/events. A separate executor daemon owns Docker lifecycle operations and is the only service with the Docker socket. Workers are disposable and communicate through attempt/result records; the scheduler decides eligibility deterministically.

**Tech Stack:** Stage 1 stack plus LangGraph Agent Server, FastAPI custom routes, Redis 7, httpx, Git CLI, Docker Engine/Compose.

**Spec:** `docs/architecture/infinite-interns-design.md`

## Global Constraints

- The scheduler, not an LLM, owns readiness, claiming, concurrency, and resource conflicts.
- No task execution holds a SQL transaction for its runtime.
- Every authoritative task mutation validates the current lease epoch.
- Worker/container creation is idempotent by run/task/attempt/operation key.
- Integration is single-writer and anchored to `last_green_commit`.
- Worker loss cannot turn incomplete work into success.
- No SWE worker receives `/var/run/docker.sock`.

---

## File structure added by this stage

```text
langgraph.json
src/infinite_interns/
  api/app.py
  graph/state.py
  graph/factory.py
  graph/nodes.py
  scheduler/dag.py
  scheduler/leasing.py
  scheduler/service.py
  execution/base.py
  execution/client.py
  execution/worktrees.py
  integration/service.py
  recovery/service.py
executor/
  app.py
  docker_backend.py
  schemas.py
  Dockerfile
docker/
  worker/Dockerfile
  fake-worker/worker.py
docker-compose.workstation.yml
tests/unit/graph/
tests/unit/scheduler/
tests/unit/execution/
tests/integration/orchestration/
tests/chaos/
```

### Task 1: Add LangGraph Agent Server shell and compact state

**Files:**
- Modify: `pyproject.toml`
- Create: `langgraph.json`
- Create: `src/infinite_interns/graph/state.py`
- Create: `src/infinite_interns/graph/factory.py`
- Create: `src/infinite_interns/graph/nodes.py`
- Create: `src/infinite_interns/api/app.py`
- Test: `tests/unit/graph/test_state.py`

**Interfaces:**
- `FactoryState` stores IDs/refs and small status fields only.
- Compiled graph export is `src.infinite_interns.graph.factory:graph`.
- Custom API exposes `/api/health` and later run routes.

- [ ] **Step 1: Add Agent Server dependencies**

Add current compatible `fastapi`, `httpx`, `langgraph`, and `langgraph-cli[inmem]` dependencies to `pyproject.toml`, then run `uv lock`.

- [ ] **Step 2: Write compact-state test**

```python
from infinite_interns.graph.state import FactoryState


def test_factory_state_contains_refs_not_blobs() -> None:
    state = FactoryState(run_id="run_1", current_commit="abc", last_green_commit="abc")
    payload = state.model_dump()
    assert "logs" not in payload
    assert "source_code" not in payload
    assert payload["run_id"] == "run_1"
```

- [ ] **Step 3: Implement `FactoryState`**

```python
from pydantic import BaseModel, ConfigDict, Field


class FactoryState(BaseModel):
    model_config = ConfigDict(extra="forbid")
    run_id: str
    spec_version: str | None = None
    requirement_ids: list[str] = Field(default_factory=list)
    ready_task_ids: list[str] = Field(default_factory=list)
    running_task_ids: list[str] = Field(default_factory=list)
    passed_task_ids: list[str] = Field(default_factory=list)
    failed_task_ids: list[str] = Field(default_factory=list)
    blocked_task_ids: list[str] = Field(default_factory=list)
    current_commit: str
    last_green_commit: str
    failing_gate_ids: list[str] = Field(default_factory=list)
    convergence_iteration: int = 0
    deployment_ref: str | None = None
    spend_usd: float = 0.0
    elapsed_seconds: int = 0
    escalation_level: int = 0
```

- [ ] **Step 4: Build minimal graph shell**

Create async nodes `load_run`, `schedule`, and `wait_or_finish`; each delegates to typed services. Wire `START -> load_run -> schedule -> wait_or_finish -> END` for the initial shell. Stage 2 acceptance expands scheduler behavior without embedding SQL/Docker logic in graph nodes.

- [ ] **Step 5: Configure Agent Server**

```json
{
  "dependencies": ["."],
  "graphs": {
    "factory": "./src/infinite_interns/graph/factory.py:graph"
  },
  "http": {
    "app": "./src/infinite_interns/api/app.py:app"
  },
  "env": ".env"
}
```

- [ ] **Step 6: Verify local server and commit**

```bash
uv run langgraph dev --no-browser
curl -f http://127.0.0.1:2024/api/health
git add pyproject.toml uv.lock langgraph.json src/infinite_interns/graph src/infinite_interns/api tests/unit/graph
git commit -m "feat: add durable LangGraph factory shell"
```

Expected health body: `{"status":"ok"}`.

### Task 2: Implement task DAG validation and readiness

**Files:**
- Create: `src/infinite_interns/scheduler/dag.py`
- Create: `tests/unit/scheduler/test_dag.py`

**Interfaces:**
- `TaskDag.from_edges(edges: Sequence[tuple[str, str]]) -> TaskDag`.
- `TaskDag.validate_acyclic() -> None`, raising `DagCycleError`.
- `TaskDag.ready_tasks(status_by_task: Mapping[str, TaskStatus]) -> tuple[str, ...]`.

- [ ] **Step 1: Write cycle/readiness tests**

```python
import pytest

from infinite_interns.domain.enums import TaskStatus
from infinite_interns.scheduler.dag import DagCycleError, TaskDag


def test_cycle_is_rejected() -> None:
    dag = TaskDag.from_edges((("A", "B"), ("B", "C"), ("C", "A")))
    with pytest.raises(DagCycleError):
        dag.validate_acyclic()


def test_only_dependency_complete_task_is_ready() -> None:
    dag = TaskDag.from_edges((("A", "C"), ("B", "C")))
    blocked = {"A": TaskStatus.DONE, "B": TaskStatus.RUNNING, "C": TaskStatus.PLANNED}
    ready = {"A": TaskStatus.DONE, "B": TaskStatus.DONE, "C": TaskStatus.PLANNED}
    assert dag.ready_tasks(blocked) == ()
    assert dag.ready_tasks(ready) == ("C",)
```

- [ ] **Step 2: Implement Kahn topological validation**

Use deterministic lexical task-ID ordering for equal-priority nodes. `ready_tasks` treats only `DONE`/`VERIFIED` upstream dependencies as satisfied and never changes database state.

- [ ] **Step 3: Verify and commit**

```bash
uv run pytest tests/unit/scheduler/test_dag.py -q
git add src/infinite_interns/scheduler/dag.py tests/unit/scheduler/test_dag.py
git commit -m "feat: add deterministic task DAG"
```

### Task 3: Add PostgreSQL leases, fencing, and task claims

**Files:**
- Modify: `src/infinite_interns/db/models.py`
- Modify: `src/infinite_interns/db/repositories.py`
- Create: `migrations/versions/0002_task_leases.py`
- Create: `src/infinite_interns/scheduler/leasing.py`
- Test: `tests/integration/orchestration/test_leases.py`

**Interfaces:**
- `TaskLease(task_id: str, owner: str, epoch: int, expires_at: datetime)`.
- `LeaseService.claim_ready_task(worker_id: str, now: datetime) -> TaskLease | None`.
- `LeaseService.renew(task_id: str, owner: str, epoch: int, now: datetime) -> TaskLease`.
- `LeaseService.assert_epoch(task_id: str, epoch: int) -> None`.

- [ ] **Step 1: Write concurrent claim test**

Create one READY task, execute two claim coroutines concurrently with different worker IDs, and assert exactly one returns a lease while the other returns `None`.

- [ ] **Step 2: Write zombie-write test**

Claim epoch 1; expire it; reclaim same task as epoch 2; call an authoritative mutation guarded by epoch 1. Expected: `StaleLeaseError` and no row change.

- [ ] **Step 3: Add lease migration**

Add nullable `lease_owner`, non-null `lease_epoch` default `0`, and nullable timezone-aware `lease_expires_at` to `ii.tasks`.

- [ ] **Step 4: Implement atomic claim with `FOR UPDATE SKIP LOCKED`**

Inside one short transaction: select the highest-priority READY task whose lease is absent/expired, lock it with `SKIP LOCKED`, increment epoch, set owner/expiry, commit, then return `TaskLease`. Renewals keep the same epoch and require matching owner/epoch.

- [ ] **Step 5: Verify and commit**

```bash
uv run alembic upgrade head
uv run pytest tests/integration/orchestration/test_leases.py -q
git add migrations src/infinite_interns/db src/infinite_interns/scheduler tests/integration/orchestration/test_leases.py
git commit -m "feat: add leased task ownership with fencing"
```

### Task 4: Create worktree manager and executor daemon contract

**Files:**
- Create: `src/infinite_interns/execution/base.py`
- Create: `src/infinite_interns/execution/worktrees.py`
- Create: `src/infinite_interns/execution/client.py`
- Create: `executor/schemas.py`
- Create: `executor/app.py`
- Create: `tests/unit/execution/test_worktrees.py`
- Create: `tests/unit/execution/test_idempotency.py`

**Interfaces:**
- `ExecutionBackend.create(request: ExecutionRequest) -> ExecutionHandle`.
- `ExecutionBackend.status(handle: ExecutionHandle) -> ExecutionStatus`.
- `ExecutionBackend.terminate(handle: ExecutionHandle) -> None`.
- `WorktreeManager.create(repo: Path, run_id: str, task_id: str, attempt_id: str, base_commit: str) -> WorktreeHandle`.
- `operation_key = "<run_id>:<task_id>:<attempt_id>:<operation>"`.

- [ ] **Step 1: Write worktree branch/path tests**

Expected branch is `factory/<run_id>/<task_id>/<attempt_id>`. Expected directory is `<factory-root>/worktrees/<run_id>/<task_id>/<attempt_id>`. Reject identifiers containing `/`, `..`, NUL, or platform path separators before invoking Git.

- [ ] **Step 2: Implement concrete Git commands with argv**

```python
subprocess.run(
    ["git", "-C", str(repo), "worktree", "add", "-b", branch, str(path), base_commit],
    check=True,
    text=True,
    capture_output=True,
)
```

Removal uses `git -C <repo> worktree remove --force <path>` only after artifacts/candidate refs are persisted.

- [ ] **Step 3: Write executor idempotency test**

POST the exact same `ExecutionRequest` twice. Assert both responses contain the same execution ID and backend create count remains one.

- [ ] **Step 4: Implement FastAPI executor with in-memory backend first**

Routes:

```text
POST /executions
GET /executions/{execution_id}
POST /executions/{execution_id}/terminate
POST /executions/{execution_id}/heartbeat
```

`ExecutionRequest` includes operation key, run/task/attempt IDs, lease epoch, worktree path, image, argv, artifact path, environment names (not secret values), CPU/memory limits, and network profile.

- [ ] **Step 5: Verify and commit**

```bash
uv run pytest tests/unit/execution -q
git add src/infinite_interns/execution executor tests/unit/execution
git commit -m "feat: add isolated execution contract"
```

### Task 5: Add Docker backend and fake worker image

**Files:**
- Create: `executor/docker_backend.py`
- Create: `executor/Dockerfile`
- Create: `docker/worker/Dockerfile`
- Create: `docker/fake-worker/worker.py`
- Create: `docker-compose.workstation.yml`
- Test: `tests/integration/orchestration/test_docker_execution.py`

**Interfaces:**
- Docker backend mounts exactly one task worktree RW and one artifact directory RW.
- Worker receives no Docker socket and no integration checkout.
- Fake worker writes `result.json` with `attempt_id`, `lease_epoch`, `status`, and `candidate_commit` when successful.

- [ ] **Step 1: Implement deterministic fake worker**

Worker parses an input JSON file, writes `task-output.txt`, runs `git add task-output.txt`, commits with a deterministic message, resolves `git rev-parse HEAD`, and writes the result envelope atomically to the artifact directory.

- [ ] **Step 2: Implement Docker backend**

Use `docker run` argv from the executor daemon. Apply labels `ii.run_id`, `ii.task_id`, `ii.attempt_id`, `ii.operation_key`; set a non-root UID/GID; mount only approved task paths; apply CPU/memory limits; attach only configured network. On executor restart, query containers by `ii.operation_key` before creating a new one.

- [ ] **Step 3: Add workstation Compose**

Services: PostgreSQL 16, Redis 7, Agent Server, executor daemon. Mount Docker socket only into executor daemon. Agent Server reaches executor over a private service network.

- [ ] **Step 4: Write integration test**

Create a fixture Git repository and worktree, launch fake worker, wait for result, assert candidate commit exists and contains `task-output.txt`, and assert host integration checkout remains unchanged.

- [ ] **Step 5: Verify and commit**

```bash
docker compose -f docker-compose.workstation.yml build
uv run pytest tests/integration/orchestration/test_docker_execution.py -q
git add executor docker docker-compose.workstation.yml tests/integration/orchestration/test_docker_execution.py
git commit -m "feat: execute tasks in isolated Docker workers"
```

### Task 6: Add scheduler loop, heartbeat recovery, and stall classification

**Files:**
- Create: `src/infinite_interns/scheduler/service.py`
- Create: `src/infinite_interns/recovery/service.py`
- Modify: `src/infinite_interns/graph/nodes.py`
- Test: `tests/unit/scheduler/test_service.py`
- Test: `tests/chaos/test_worker_loss.py`

**Interfaces:**
- `Scheduler.tick(run_id: str, now: datetime) -> SchedulerDecision`.
- `RecoveryService.expire_stale_leases(now: datetime) -> list[RecoveryAction]`.
- `ProgressSnapshot(last_heartbeat, last_agent_event, last_semantic_progress)`.

- [ ] **Step 1: Write capacity/readiness tests**

Assert scheduler never exceeds configured SWE slots, never claims unmet dependencies, and never claims a task whose declared exclusive resource lock conflicts with a running task.

- [ ] **Step 2: Implement deterministic priority**

Sort by critical-path flag descending, blocks-count descending, risk descending, waiting age descending, then stable task ID. Read limits/weights from `Settings`; do not call a model.

- [ ] **Step 3: Implement heartbeat/stall decisions**

At >90 seconds without worker heartbeat, expire lease and create recovery action. A live worker with no agent event for 10 minutes gets a probe; no semantic progress for 20 minutes produces `STALLED` and routes to escalation rather than blind same-strategy retry.

- [ ] **Step 4: Write worker-loss chaos test**

Launch fake worker, terminate it before result, wait/advance past TTL, assert replacement attempt has higher epoch, then submit stale old result and assert rejection.

- [ ] **Step 5: Verify and commit**

```bash
uv run pytest tests/unit/scheduler tests/chaos/test_worker_loss.py -q
git add src/infinite_interns/scheduler src/infinite_interns/recovery src/infinite_interns/graph tests
git commit -m "feat: add scheduling and crash recovery"
```

### Task 7: Serialize integration and preserve last-green commit

**Files:**
- Create: `src/infinite_interns/integration/service.py`
- Create: `tests/integration/orchestration/test_integration.py`

**Interfaces:**
- `IntegrationService.integrate(run_id: str, candidate_commit: str, expected_last_green: str) -> IntegrationResult`.
- One integration lease/advisory lock per run.
- Regression success updates `current_commit` and `last_green_commit`; regression failure restores integration checkout and preserves the prior last-green SHA.

- [ ] **Step 1: Write green and regression fixtures**

Candidate A adds a harmless file and leaves fixture regression command green. Candidate B changes expected behavior so regression command exits nonzero.

- [ ] **Step 2: Implement integration lock and regression gate**

Acquire a DB advisory/application lock for run integration, re-read expected last-green, rebase/cherry-pick candidate into integration worktree, run configured regression argv, and only then persist new `last_green_commit`. On failure reset integration worktree to old SHA and emit `INTEGRATION_REJECTED`.

- [ ] **Step 3: Assert rejected candidate cannot move green anchor**

```python
assert result.status is IntegrationStatus.REJECTED
assert await run_repository.last_green(run_id) == old_green
```

- [ ] **Step 4: Verify and commit**

```bash
uv run pytest tests/integration/orchestration/test_integration.py -q
git add src/infinite_interns/integration tests/integration/orchestration/test_integration.py
git commit -m "feat: serialize integration around last green"
```

### Task 8: Run Stage 2 end-to-end fake factory acceptance

**Files:**
- Create: `tests/integration/orchestration/test_stage2_acceptance.py`
- Modify: `README.md`
- Modify: `AGENTS.md`

**Interfaces:**
- Uses Stage 2 services with fake worker backend only; no provider credentials.

- [ ] **Step 1: Create fixture DAG**

```text
A --\
     > C
B --/
```

A and B must become claimed/running without waiting for each other. C remains blocked until both A and B are integrated and DONE.

- [ ] **Step 2: Inject worker crash and stale result**

Terminate B attempt 1 before completion. After lease expiry, B attempt 2 claims a higher epoch and succeeds. Submit attempt 1 result afterward; assert rejection and `STALE_WORKER_WRITE_REJECTED` event.

- [ ] **Step 3: Assert final state**

A, B2, and C changes are present in the integration branch, regression command passes, all tasks are DONE, and `current_commit == last_green_commit`.

- [ ] **Step 4: Run full Stage 2 gate and commit docs**

```bash
uv run ruff check .
uv run pyright
uv run pytest tests/unit -q
uv run pytest tests/integration/orchestration tests/chaos -q
git add tests README.md AGENTS.md
git commit -m "test: certify durable fake-worker orchestration"
```

## Stage 2 completion gate

Required evidence:

- dependency-safe tasks execute concurrently,
- one killed worker is recovered,
- stale lease-epoch writes are rejected,
- repeated create requests are idempotent,
- integration is serialized,
- regression failure leaves `last_green_commit` unchanged,
- no worker container has Docker socket access.
