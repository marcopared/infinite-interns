# Stage 2 Task 6 report

Status: COMPLETE.

## RED evidence

The first Task 6 test commit exposed a pytest module-name collision because multiple un-packaged test directories contained `test_service.py`; no production behavior had been exercised. The new files were renamed to unique module names.

Valid RED run `32312004002` passed locked sync and Ruff, then failed unit collection specifically because `infinite_interns.scheduler.service` and `infinite_interns.recovery` did not exist.

## Implementation

### Deterministic scheduler

`Scheduler.tick(run_id, now)`:

- enforces `max_swe_workers` against active task count;
- considers only `PLANNED`/`READY` candidates;
- fails closed when a parent is absent or is not `DONE`/`VERIFIED`;
- avoids exclusive-resource conflicts with already active work and with tasks selected earlier in the same tick;
- orders by critical-path membership, blocks-count, risk, waiting age, then stable task ID;
- contains no model call or model-derived priority.

### Recovery

`RecoveryService` classifies progress snapshots deterministically:

1. heartbeat older than 90 seconds -> `EXPIRE_LEASE`;
2. semantic progress older than 20 minutes -> `STALLED`;
3. live heartbeat but agent-event silence older than 10 minutes -> `PROBE`;
4. otherwise `NONE`.

The service also exposes `expire_stale_leases(now)` against a typed recovery source.

### Fenced worker-result publication

`WorkerResultService` publishes task state through an epoch-guarded SQL update. A mismatched epoch changes no task row and emits durable `STALE_WORKER_WRITE_REJECTED` evidence with task/epoch/status context.

The graph scheduling node now routes through an optional deterministic `Scheduler` service while keeping SQL, Docker lifecycle, and model execution outside LangGraph node bodies.

### Permanent chaos gate

CI now executes `uv run pytest tests/chaos -q` after the integration suite.

## Harness repair

The first chaos execution failed before fencing logic because strict Pydantic records were instantiated positionally. The fixture was corrected to named fields; no production code was changed for that failure.

## Final GREEN evidence

Actions run `32312400342` passed:

```text
uv sync --dev --locked                      PASS
uv run ruff check .                         PASS
uv run pytest tests/unit -q                 PASS (51 tests)
uv run alembic upgrade head                 PASS
uv run pytest tests/integration -q          PASS (7 tests)
uv run pytest tests/chaos -q                PASS
uv run pyright                              PASS
docker compose ... config --quiet           PASS
docker compose ... build agent-server executor  PASS
Smoke LangGraph Agent Server                PASS
```
