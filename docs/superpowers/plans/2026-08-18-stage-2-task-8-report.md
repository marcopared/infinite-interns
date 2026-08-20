# Stage 2 Task 8 report

## Objective

Certify the Stage 2 fake-worker factory end to end. This stage must prove orchestration authority, crash recovery, fencing, idempotent execution creation, isolated Docker/worktree execution, serialized regression-gated integration, and preservation of the durable last-green anchor without using any model provider credentials.

## Acceptance scenario

`tests/integration/orchestration/test_stage2_acceptance.py` constructs the dependency graph:

```text
A --\
     > C
B --/
```

The test proves:

1. A and B are simultaneously dependency-ready and can be claimed independently.
2. C is not dependency-ready while A/B are only claimed.
3. A executes in its own worktree/container and integrates successfully.
4. B attempt 1 is deliberately terminated before completion.
5. After the original B lease expires, B attempt 2 is claimed at a strictly higher fencing epoch.
6. A stale result submitted with B attempt 1's epoch is rejected and emits `STALE_WORKER_WRITE_REJECTED`.
7. B attempt 2 executes and integrates successfully.
8. Only after both A and B are `DONE` does C become dependency-ready.
9. C executes from the new integrated green anchor and integrates successfully.
10. Final durable integration state has `current_commit == last_green_commit`.
11. The integration checkout points at that durable last-green SHA and its regression command passes.
12. All A/B/C task records are `DONE` and only successful A/B2/C worker changes appear in the integrated checkout.

## Supporting completion-gate evidence

The Stage 2 completion gate is broader than the single acceptance test. Permanent regression tests also prove:

- `TaskDag` rejects cycles, waits for every dependency, and exposes immutable graph structure.
- concurrent lease claims use one database-authoritative winner and monotonic fencing epochs;
- stale lease epochs cannot perform authoritative worker-result state changes;
- repeated executor `POST /executions` requests with the same operation key return the same execution and do not duplicate backend creation;
- Docker execution recovers existing containers by operation-key labels after executor restart;
- workstation Compose mounts `/var/run/docker.sock` only into the executor service;
- worker execution receives task worktree/artifact mounts rather than the integration checkout;
- scheduler capacity, dependency, priority, and exclusive-resource-lock decisions are deterministic;
- heartbeat loss/stall recovery does not treat worker disappearance as success;
- integration is serialized per run and regression failure cannot advance durable `last_green_commit`.

## Executable verification

GitHub Actions run `32313309044` on Stage 2 head `e272daaa74b8a360225f34c34b6555cad7831d0e` completed successfully.

The successful job executed all of the following gates:

```text
uv sync --dev --locked                          PASS
uv run ruff check .                             PASS
uv run pytest tests/unit -q                     PASS — 51 tests
uv run alembic upgrade head                     PASS — migrations 0001 → 0002 → 0003
uv run pytest tests/integration -q              PASS — 10 tests
uv run pytest tests/chaos -q                    PASS — 1 test
uv run pyright                                  PASS — 0 errors / warnings
docker compose ... config --quiet               PASS
docker compose ... build agent-server executor PASS
live langgraph dev /api/health                  PASS
```

The integration suite includes the Docker-backed Stage 2 acceptance scenario. No model/provider credential is required by the test.

## Architecture deviations discovered during implementation

Two implementation details intentionally differ from the initial task-plan sketch without weakening the approved architecture:

1. **Candidate commit materialization occurs in the trusted executor, not inside the worker container.** A linked Git worktree's metadata lives outside the task directory; exposing enough Git metadata for the worker to commit would have introduced an additional privileged/shared mount. The worker therefore writes result material, while the executor validates the result envelope and creates the candidate commit.
2. **Long integration serialization uses a dedicated PostgreSQL advisory-lock connection.** A normal persistence transaction is not held while regression commands execute. Durable anchor writes remain short transactions.

Both changes strengthen the core boundaries: the disposable worker receives less authority, and long-running verification does not hold ordinary database row locks.

## Remaining non-blocking observations

- Integration's auxiliary Git ref and PostgreSQL anchor cannot be updated atomically. PostgreSQL remains authoritative and detected drift fails closed; a later recovery-hardening pass should reconcile the auxiliary ref automatically.
- The Stage 2 graph service adapter is configured process-wide at startup. It must remain configuration wiring rather than mutable per-run authority.

Neither observation permits false success or invalidates the Stage 2 completion gate.

## Result

Task 8 behavioral certification: **PASS** on run `32313309044`.

Documentation and branch-head verification are completed separately before the Stage 2 PR is made ready for integration.
