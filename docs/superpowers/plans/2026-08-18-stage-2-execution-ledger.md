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

## Progress

Task 1 RED: Actions run `32308139332` failed during unit collection because `infinite_interns.graph` did not exist after locked sync and Ruff passed.

Task 1 implementation: added locked LangGraph/FastAPI runtime, compact `FactoryState`, thin graph service/node shell, `langgraph.json`, custom FastAPI health route, and live Agent Server smoke gate.

Task 1 GREEN: Actions run `32309102027` passed locked sync, Ruff, unit tests, Alembic migration, integration tests, Pyright, and `langgraph dev` `/api/health` smoke verification.

Task 1 review: PASS; no Critical or Important findings. Minor: graph service methods remain intentionally non-authoritative placeholders until Task 6.

Task 1: COMPLETE.

Task 2: starting.
