# Task 4 report

Status: complete.

## RED evidence

GitHub Actions run `32209888928` passed dependency sync, Ruff, and all unit tests, then failed the new PostgreSQL integration gate because `infinite_interns.db` did not exist.

## Implementation discovery

The first implementation run migrated PostgreSQL successfully but exposed a real transaction-ordering defect: evidence could flush before its requirement parent because the repository layer intentionally has no ORM relationship graph. Repository `add()` methods now flush their inserted row within the caller's transaction, preserving dependency order without committing.

## GREEN evidence

GitHub Actions run `32210185676`:

```text
uv sync --dev                         PASS
uv run ruff check .                   PASS
uv run pytest tests/unit -q           PASS
uv run alembic upgrade head           PASS
uv run pytest tests/integration/db -q PASS
uv run pyright                        PASS
```

## Deliverables

- PostgreSQL schema `ii`.
- Initial Alembic migration for runs, spec versions, requirements, tasks, task dependencies, attempts, evidence, review findings, events, deployments, and budgets.
- Async SQLAlchemy/psycopg engine and session factory.
- Domain-focused run, requirement, task, evidence, and event repositories.
- Evidence uniqueness constraint over run/requirement/gate/commit/environment/verifier identity.
- PostgreSQL-backed CI service and migration/integration gate.
