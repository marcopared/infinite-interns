# Stage 2 Task 3 report

Status: COMPLETE.

## RED evidence

Actions run `32309818530` passed locked sync, Ruff, unit tests, and the existing `0001` migration, then integration collection failed because `infinite_interns.scheduler.leasing` did not exist.

## Implementation

- migration `0002_task_leases` adds `lease_owner`, monotonic `lease_epoch`, timezone-aware `lease_expires_at`, and a claimability index;
- `LeaseService` is run-scoped because task IDs are only unique within a run;
- claim uses deterministic task ordering and `FOR UPDATE SKIP LOCKED`;
- a claim increments the epoch, writes owner/expiry, marks the task `CLAIMED`, flushes, and commits before returning;
- expired `CLAIMED`/`RUNNING` tasks may be reclaimed with a higher epoch;
- renew requires the exact owner/epoch and a still-live lease;
- `assert_epoch` rejects zombie attempts after a replacement worker acquires a newer epoch.

## GREEN evidence

Actions run `32309971390` passed:

```text
uv sync --dev --locked                 PASS
uv run ruff check .                    PASS
uv run pytest tests/unit -q            PASS
uv run alembic upgrade head            PASS (0001 -> 0002)
uv run pytest tests/integration -q     PASS
uv run pyright                         PASS
Smoke LangGraph Agent Server           PASS
```

No database lock is held while an engineering task executes; each lease operation completes its own short transaction.
