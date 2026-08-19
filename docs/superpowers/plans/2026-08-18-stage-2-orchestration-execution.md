# Stage 2 Orchestration and Execution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add durable LangGraph orchestration, deterministic DAG scheduling, leases/fencing, isolated Docker/worktree execution, serialized integration, and crash recovery using fake workers only.

**Architecture:** LangGraph Agent Server hosts the parent factory graph plus custom FastAPI routes. PostgreSQL remains authoritative for tasks/evidence/events. A separate executor daemon owns Docker operations. Workers are disposable and communicate through attempt/result records; the scheduler decides eligibility deterministically.

**Tech Stack:** Stage 1 stack plus LangGraph, LangGraph CLI/Agent Server, FastAPI custom routes, Redis 7, httpx, Git CLI, Docker Engine/Compose.

**Spec:** `docs/architecture/infinite-interns-design.md`

## Global Constraints

- The scheduler, not an LLM, owns task readiness and leases.
- No task execution holds a SQL transaction for its runtime.
- Every authoritative task mutation validates the current lease epoch.
- Worker/container duplication must be safe through idempotency keys.
- Integration is single-writer and anchored to `last_green_commit`.
- Worker loss cannot turn incomplete work into success.

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
tests/unit/scheduler/
tests/integration/orchestration/
tests/chaos/
```

### Task 1: Add LangGraph Agent Server shell and custom API

**Files:**
- Modify: `pyproject.toml`
- Create: `langgraph.json`
- Create: `src/infinite_interns/graph/state.py`
- Create: `src/infinite_interns/graph/factory.py`
- Create: `src/infinite_interns/api/app.py`
- Test: `tests/unit/graph/test_state.py`

**Interfaces:**
- Produces `FactoryState` with compact IDs/refs only.
- Produces compiled `graph` export required by `langgraph.json`.
- Produces custom `/api/runs/{run_id}` health/read route.

- [ ] **Step 1: Add dependencies**

Add compatible current LangGraph packages and FastAPI to `pyproject.toml`:

```toml
"fastapi>=0.116,<1",
"httpx>=0.28,<1",
"langgraph>=0.6,<1",
"langgraph-cli[inmem]>=0.4,<1",
```

Run `uv lock`.

- [ ] **Step 2: Write state-shape test**

```python
def test_factory_state_contains_refs_not_blobs():
    state = FactoryState(run_id="run_1", current_commit="abc")
    payload = state.model_dump()
    assert "logs" not in payload
    assert "source_code" not in payload
```

- [ ] **Step 3: Implement state model**

Include only run ID, spec version/ref, requirement IDs, ready/running/passed/failed/blocked task IDs, current commit, last green commit, failing gate IDs, convergence iteration, deployment ref, spend, elapsed seconds, and escalation level.

- [ ] **Step 4: Build minimal graph**

Create nodes `load_run -> schedule -> wait_or_finish`. Stage 2 uses a fake task execution adapter; graph nodes call typed services and never contain SQL/Docker logic inline.

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

- [ ] **Step 6: Verify local server**

```bash
uv run langgraph dev --no-browser
curl -f http://127.0.0.1:2024/ok
```

Expected: `{"ok":true}` from Agent Server.

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml uv.lock langgraph.json src/infinite_interns/graph src/infinite_interns/api tests/unit/graph
git commit -m "feat: add durable LangGraph factory shell"
```

### Task 2: Implement task DAG validation and readiness

**Files:**
- Create: `src/infinite_interns/scheduler/dag.py`
- Create: `tests/unit/scheduler/test_dag.py`

**Interfaces:**
- Produces `TaskDag(nodes, edges)`.
- Produces `validate_acyclic() -> None` raising `DagCycleError`.
- Produces `ready_tasks(status_by_task) -> tuple[str, ...]`.

- [ ] **Step 1: Write cycle/readiness tests**

```python
def test_cycle_is_rejected():
    dag = TaskDag.from_edges([("A", "B"), ("B", "C"), ("C", "A")])
    with pytest.raises(DagCycleError):
        dag.validate_acyclic()


def test_only_dependency_complete_tasks_are_ready():
    dag = TaskDag.from_edges([("A", "C"), ("B", "C")])
    assert dag.ready_tasks({"A": "done", "B": "running", "C": "planned"}) == ()
    assert dag.ready_tasks({"A": "done", "B": "done", "C": "planned"}) == ("C",)
```

- [ ] **Step 2: Implement DAG with Kahn topological validation**

Keep it dependency-free. Deterministically sort task IDs before returning ready work.

- [ ] **Step 3: Run tests**

```bash
uv run pytest tests/unit/scheduler/test_dag.py -q
```

- [ ] **Step 4: Commit**

```bash
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
- Produces `TaskLease(task_id, owner, epoch, expires_at)`.
- Produces `claim_ready_task(worker_id, now) -> TaskLease | None` using `FOR UPDATE SKIP LOCKED`.
- Produces `renew(task_id, owner, epoch, now) -> TaskLease`.
- Produces `assert_epoch(task_id, epoch) -> None`.

- [ ] **Step 1: Write concurrent-claim test**

Start two async claims against one READY task and assert exactly one returns a lease.

- [ ] **Step 2: Write zombie-write test**

Claim epoch 1, expire/reclaim to epoch 2, then attempt an authoritative update with epoch 1. Expected: `StaleLeaseError`.

- [ ] **Step 3: Add lease columns/migration**

`lease_epoch` starts at `0` and increments atomically each successful new claim. Renewals keep the same epoch.

- [ ] **Step 4: Implement claim SQL**

Use a single transaction around select/update only. Never leave the transaction open while work executes.

- [ ] **Step 5: Run integration test**

```bash
uv run alembic upgrade head
uv run pytest tests/integration/orchestration/test_leases.py -q
```

- [ ] **Step 6: Commit**

```bash
git add migrations src/infinite_interns/db src/infinite_interns/scheduler tests/integration/orchestration/test_leases.py
git commit -m "feat: add leased task ownership with fencing"
```

### Task 4: Create worktree manager and executor daemon contract

**Files:**
- Create: `src/infinite_interns/execution/base.py`
- Create: `src/infinite_interns/execution/worktrees.py`
- Create: `executor/schemas.py`
- Create: `executor/app.py`
- Create: `tests/unit/execution/test_worktrees.py`
- Create: `tests/unit/execution/test_idempotency.py`

**Interfaces:**
- `ExecutionBackend.create(attempt) -> ExecutionHandle`.
- `ExecutionBackend.status(handle) -> ExecutionStatus`.
- `ExecutionBackend.terminate(handle) -> None`.
- `WorktreeManager.create(repo, run_id, task_id, attempt_id, base_commit) -> WorktreeHandle`.
- Executor requests require `operation_key = run_id:task_id:attempt_id:operation`.

- [ ] **Step 1: Write deterministic branch/path tests**

Expected task branch:

```text
factory/<run_id>/<task_id>/<attempt_id>
```

Expected worktree path under configured factory root; reject paths that escape it.

- [ ] **Step 2: Implement Git worktree operations via explicit argv**

Use `subprocess.run([...], check=True)` with no shell string interpolation. Record base commit and created branch.

- [ ] **Step 3: Write executor idempotency test**

Calling `POST /executions` twice with the same operation key returns the same execution ID and does not create two containers.

- [ ] **Step 4: Implement FastAPI executor contract with an in-memory fake backend first**

Routes:

```text
POST /executions
GET /executions/{id}
POST /executions/{id}/terminate
POST /executions/{id}/heartbeat
```

- [ ] **Step 5: Run tests and commit**

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
- Docker backend mounts exactly one task worktree and one artifact directory.
- Worker receives no Docker socket.
- Fake worker protocol writes `result.json` containing `attempt_id`, `lease_epoch`, `status`, and optional `candidate_commit`.

- [ ] **Step 1: Build a fake worker that creates a file and commit**

The worker accepts JSON input, writes `task-output.txt`, commits it, and emits structured result JSON.

- [ ] **Step 2: Implement Docker backend with argv-based Docker CLI calls**

For v1 executor daemon, Docker ownership lives only here. Use labels for `ii.run_id`, `ii.task_id`, `ii.attempt_id`, and `ii.operation_key` so existing containers can be discovered after daemon restart.

- [ ] **Step 3: Add workstation Compose services**

Include Postgres 16, Redis 7, executor daemon, and Agent Server image. Mount the Docker socket only into executor daemon.

- [ ] **Step 4: Write integration test**

Create fixture Git repo, worktree, launch fake worker, wait for completion, assert candidate commit exists and host integration checkout is unchanged.

- [ ] **Step 5: Run and commit**

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
- `Scheduler.tick(run_id, now) -> SchedulerDecision`.
- `RecoveryService.expire_stale_leases(now) -> list[RecoveryAction]`.
- `ProgressSnapshot(last_heartbeat, last_agent_event, last_semantic_progress)`.

- [ ] **Step 1: Write capacity/readiness tests**

Assert the scheduler never exceeds 4 SWE slots, never schedules an unmet dependency, and never schedules a globally conflicting task while its lock is held.

- [ ] **Step 2: Implement scheduler priority**

Order by critical-path flag, blocking count, criticality, age, then stable task ID. Keep coefficients/config in settings.

- [ ] **Step 3: Implement heartbeat expiry**

At >90 seconds without heartbeat, expire lease, preserve attempt record, and make task eligible for a new attempt according to failure policy.

- [ ] **Step 4: Write chaos test**

Launch fake worker, kill it before result, advance/wait beyond TTL, assert replacement gets a higher epoch and old result is rejected.

- [ ] **Step 5: Run and commit**

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
- `IntegrationService.integrate(run_id, candidate_commit, expected_last_green) -> IntegrationResult`.
- One integration lease per run.
- On success update `last_green_commit`; on regression restore it.

- [ ] **Step 1: Write green and regression fixtures**

Fixture A candidate adds a harmless file and passes test command. Fixture B changes test expectation and fails regression.

- [ ] **Step 2: Implement serialized integration**

Use a DB-backed integration lock/advisory lock. Verify expected last-green before merging. Run configured deterministic regression command after merge.

- [ ] **Step 3: Assert failed candidate does not move last green**

```python
assert result.status == IntegrationStatus.REJECTED
assert await runs.last_green(run_id) == old_green
```

- [ ] **Step 4: Run and commit**

```bash
uv run pytest tests/integration/orchestration/test_integration.py -q
git add src/infinite_interns/integration tests/integration/orchestration/test_integration.py
git commit -m "feat: serialize integration around last green"
```

### Task 8: Stage 2 end-to-end fake factory run

**Files:**
- Create: `tests/integration/orchestration/test_stage2_acceptance.py`
- Modify: `README.md`
- Modify: `AGENTS.md`

**Interfaces:**
- Uses all Stage 2 services with fake worker backend; no provider credentials.

- [ ] **Step 1: Build fixture DAG**

```text
A ─┐
   ├─> C
B ─┘
```

A and B must run concurrently. C starts only after both integrate.

- [ ] **Step 2: Inject one worker crash**

Kill B attempt 1. Verify B attempt 2 receives higher lease epoch and succeeds.

- [ ] **Step 3: Inject one stale zombie result**

Submit B attempt 1 result after attempt 2 owns the task. Expected: rejected and event recorded.

- [ ] **Step 4: Assert final Git state**

A, B2, and C changes exist in the integration branch, all fixture regressions pass, and `last_green_commit == current_commit`.

- [ ] **Step 5: Run full stage gate**

```bash
uv run ruff check .
uv run pyright
uv run pytest tests/unit -q
uv run pytest tests/integration/orchestration tests/chaos -q
```

- [ ] **Step 6: Update docs and commit**

```bash
git add tests README.md AGENTS.md
git commit -m "test: certify durable fake-worker orchestration"
```

## Stage 2 completion gate

Required evidence:

- concurrent dependency-safe scheduling works,
- one worker crash is recovered,
- stale epoch writes are rejected,
- duplicate create operations are idempotent,
- integration is serialized,
- regression failure leaves `last_green_commit` unchanged,
- no worker container has the Docker socket.
