# SDD ledger — plan: docs/superpowers/plans/2026-08-18-stage-2-orchestration-execution.md

Branch: `impl/stage-2-orchestration-execution`
Base: `main` @ `4881309b9f932470caee084488abb134eed05592`

This tracked ledger is the portability fallback for the current controller, which has GitHub repository access but no durable local git worktree. GitHub Actions is the executable verification environment.

## Baseline

The Stage 2 branch was created directly from the Stage 1 merge commit. The branch starts from the exact Stage 1 tree that passed locked dependency sync, Ruff, unit tests, Alembic migration, integration tests, and Pyright in Actions run `32307572152` before merge.

## Pre-flight dependency/interface scan

| Producer task | Consumer task | Shared interface/file | Finding |
|---|---|---|---|
| 1 | 6 | `graph/nodes.py`, `FactoryState` | Task 6 intentionally expands the Task 1 graph shell; no conflict. Keep SQL/Docker logic out of graph nodes. |
| 2 | 6 | `TaskDag.ready_tasks`, task status semantics | Compatible. Stage 1 `TaskStatus` contains both `VERIFIED` and `DONE`, matching the plan. |
| 2 | 8 | dependency readiness | Compatible; Task 8 depends on deterministic readiness from Task 2. |
| 3 | 6 | task lease columns and fencing | Compatible; scheduler/recovery must use epoch-guarded authoritative writes. |
| 3 | 7 | PostgreSQL repositories/control-plane state | Compatible; integration locking and last-green persistence must remain DB-authoritative. |
| 4 | 5 | `ExecutionBackend`, executor API, worktree paths | Compatible; Task 5 supplies Docker as a backend without changing the contract. |
| 4 | 6 | execution handles / idempotency keys | Compatible; scheduler can request execution but executor owns Docker lifecycle. |
| 5 | 8 | fake worker result envelope | Compatible; acceptance test consumes the exact attempt/epoch/candidate result contract. |
| 6 | 8 | recovery and stale-write rejection | Compatible; acceptance scenario deliberately exercises the recovery path. |
| 7 | 8 | serialized integration / `last_green_commit` | Compatible; acceptance final state requires current and last-green to match. |

## Per-task self-consistency scan

| Task | Check | Result |
|---|---|---|
| 1 | compact state test vs declared fields; graph export vs `langgraph.json` | Consistent. |
| 2 | cycle/readiness tests vs Kahn implementation | Consistent. |
| 3 | lease interfaces vs migration and zombie-write test | Consistent. Short transaction requirement remains binding. |
| 4 | worktree naming/path rules vs Git argv; executor idempotency contract | Consistent. |
| 5 | Docker mounts/security requirements vs fake-worker integration test | Consistent. Docker socket belongs only to executor daemon. |
| 6 | scheduler priorities vs recovery thresholds/tests | Consistent. No model calls permitted. |
| 7 | integration rejection semantics vs last-green assertion | Consistent. |
| 8 | fixture DAG/crash injection/final-state assertions vs Stage 2 gate | Consistent. |

## Rulings

Ruling: use a dedicated GitHub feature branch as the isolation boundary because this controller cannot create or enter a local git worktree. GitHub Actions remains the executable test environment. Cost if wrong: less local iteration speed, but no weakening of repository isolation or verification authority.

Ruling: dependency versions use narrow compatible ranges and a committed regenerated `uv.lock`.

Ruling: LangGraph's incomplete Pyright stub surface is isolated to `graph/factory.py` with file-local diagnostics disabled only for missing stubs/unknown member types. Repository-wide strict Pyright remains active.

Ruling: CI runs feature branches on pull requests only and `main` on push, with `cancel-in-progress` per workflow/ref. Superseded runs are not evidence; only the latest complete green run is recorded.

Ruling: fake workers do not receive enough linked-worktree Git metadata to create candidate commits. Workers emit result material; the trusted executor validates the result envelope and materializes the candidate commit. This removes a privileged/shared mount from worker containers.

Ruling: long integration serialization uses a dedicated PostgreSQL advisory-lock connection. Ordinary persistence transactions remain short and are not held across regression command execution.

## Progress

### Task 1 — LangGraph shell and compact state

RED: Actions run `32308139332` failed during unit collection because `infinite_interns.graph` did not exist after locked sync and Ruff passed.

GREEN: Actions run `32309102027` passed locked sync, Ruff, unit tests, Alembic migration, integration tests, Pyright, and live `langgraph dev` `/api/health` smoke verification.

Review: PASS; no remaining Critical/Important findings.

Status: **COMPLETE**.

### Task 2 — deterministic task DAG

RED: cycle/readiness tests initially failed because `infinite_interns.scheduler` did not exist.

GREEN: deterministic Kahn validation and lexical readiness passed the full branch gate.

Review found one Important integrity defect: the frozen dataclass exposed mutable adjacency dictionaries. The defect was reproduced by regression test and fixed with immutable mapping/frozenset structure.

Review: PASS after repair; no remaining Critical/Important findings.

Status: **COMPLETE**.

### Task 3 — PostgreSQL leases and fencing

RED: Actions run `32309818530` reached integration collection and failed specifically because `infinite_interns.scheduler.leasing` did not yet exist. Unit tests and migration 0001 were green before the expected RED failure.

Implementation added migration `0002_task_leases`, run-scoped claims with `FOR UPDATE SKIP LOCKED`, renewable leases, monotonic epochs, expiry/reclaim, and fail-closed epoch assertions.

Review: PASS. Lease timestamps/TTL/owner validity are enforced; stale workers cannot retain authority after reclamation.

Status: **COMPLETE**.

### Task 4 — worktrees and executor contract

Implementation added validated deterministic worktree identities, argv-only Git process invocation, typed executor request/handle/status contracts, and idempotent execution creation.

Review found one Important packaging defect: the executor daemon was initially outside the installable package. Canonical code moved under `src/infinite_interns/executor`; duplicate root Python package was removed.

Review: PASS after repair; no remaining Critical/Important findings.

Status: **COMPLETE**.

### Task 5 — Docker backend and fake workers

Implementation added Docker execution, fake-worker image, workstation Compose, label-based restart recovery, isolated task worktree/artifact mounts, explicit resource/network policy, and candidate materialization in the trusted executor.

Review repaired two Important findings: linked-worktree Git metadata would have required an extra privileged mount if the worker committed directly, and restart recovery initially returned short Docker IDs. Both are regression-covered.

Review: PASS after repair; no remaining Critical/Important findings.

Status: **COMPLETE**.

### Task 6 — scheduler, recovery, stale-result authority

Implementation added deterministic scheduler snapshots/priority/capacity/resource-lock handling, heartbeat/stall recovery classification, graph-node service wiring, and epoch-guarded worker-result acceptance with durable stale-write events.

Chaos coverage proves a killed worker can be replaced at a higher epoch and the stale old result cannot publish authoritative state.

Review: PASS; no remaining Critical/Important findings.

Status: **COMPLETE**.

### Task 7 — serialized integration and last-green preservation

Implementation added durable integration state migration `0003_integration_state`, per-run advisory-lock serialization, regression-gated candidate integration, compare-on-expected-anchor DB advancement, and failure restoration to the prior green SHA.

Review: PASS. Two non-blocking recovery observations remain around auxiliary Git-ref/DB atomicity; PostgreSQL stays authoritative and drift fails closed.

Status: **COMPLETE**.

### Task 8 — Stage 2 fake-factory certification

`tests/integration/orchestration/test_stage2_acceptance.py` executes A/B concurrently-ready work, kills B attempt 1, reclaims B at a higher epoch, rejects the zombie result, integrates A/B2/C serially, verifies C stays blocked until both parents are done, and ends with all tasks `DONE` plus `current_commit == last_green_commit`.

Supporting permanent tests prove executor-create idempotency, regression rejection preserving last-green, deterministic scheduler conflict/capacity behavior, Docker restart recovery, and that only the executor service receives `/var/run/docker.sock`.

Behavioral certification run: GitHub Actions `32313309044` at head `e272daaa74b8a360225f34c34b6555cad7831d0e`.

Evidence:

```text
locked dependency sync                         PASS
ruff                                           PASS
unit tests                                     PASS — 51
alembic 0001 -> 0002 -> 0003                  PASS
integration tests                              PASS — 10
chaos tests                                    PASS — 1
pyright                                        PASS — 0 errors/warnings
workstation Compose validation                 PASS
agent-server + executor image builds           PASS
live LangGraph /api/health                     PASS
```

Review: PASS; no remaining Critical/Important findings. The acceptance/report/review documentation and stale ledger were reconciled after the behavioral run.

Status: **BEHAVIOR CERTIFIED; FINAL BRANCH-HEAD CI PENDING AFTER DOC RECONCILIATION**.

## Stage 2 completion gate

| Required evidence | Result |
|---|---|
| dependency-safe tasks execute concurrently | PASS |
| one killed worker is recovered | PASS |
| stale lease-epoch writes are rejected | PASS |
| repeated create requests are idempotent | PASS |
| integration is serialized | PASS |
| regression failure leaves `last_green_commit` unchanged | PASS |
| no worker container has Docker socket access | PASS |

The only remaining step before Stage 2 is merge-ready is a fresh full CI pass on the documentation-reconciled branch head.
