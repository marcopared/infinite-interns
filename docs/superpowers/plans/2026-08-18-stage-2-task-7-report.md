# Stage 2 Task 7 report

Status: COMPLETE.

## RED evidence

Actions run `32312587366` passed the complete pre-existing Stage 2 gate through migration and then failed integration collection because `infinite_interns.integration` did not exist.

## Implementation

- migration `0003_integration_state` adds durable per-run `current_commit` and `last_green_commit` anchors;
- `IntegrationService` acquires a PostgreSQL session-level advisory lock on a dedicated connection for the full integration operation;
- database state writes still happen in separate short transactions while that application lock is held;
- the service re-reads the durable green anchor after acquiring the lock and returns `CONFLICT` if the caller's expected SHA is stale;
- candidates are applied on detached HEAD with `git cherry-pick`;
- regression executes as configured argv in the integration checkout;
- failed cherry-pick/regression switches the checkout back to the prior green SHA and emits durable `INTEGRATION_REJECTED` without moving the DB anchor;
- successful integration advances a run-specific durable Git ref and then compare-updates the DB anchor from expected old SHA to the new green SHA;
- successful concurrent submissions against the same expected green SHA serialize: one advances the anchor; the next sees a stale expectation and returns `CONFLICT`.

No destructive hard reset is used for rejected candidates.

## GREEN evidence

Actions run `32312848545` passed every repository gate:

```text
uv sync --dev --locked                      PASS
uv run ruff check .                         PASS
uv run pytest tests/unit -q                 PASS
uv run alembic upgrade head                 PASS (0001 -> 0002 -> 0003)
uv run pytest tests/integration -q          PASS
uv run pytest tests/chaos -q                PASS
uv run pyright                              PASS
docker compose ... config --quiet           PASS
docker compose ... build agent-server executor  PASS
Smoke LangGraph Agent Server                PASS
```
