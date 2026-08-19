# Task 6 report

Status: complete.

## RED evidence

GitHub Actions run `32210590610` passed Ruff and failed pytest collection because `EvaluationStatus`, `GateRequirement`, and the release-policy contracts did not exist.

## GREEN evidence

GitHub Actions run `32210665063`:

```text
uv sync --dev                         PASS
uv run ruff check .                   PASS
uv run pytest tests/unit -q           PASS
uv run alembic upgrade head           PASS
uv run pytest tests/integration/db -q PASS
uv run pyright                        PASS
```

## Deliverables

- Evaluation-specific `PASS/FAIL/BLOCKED/UNSTABLE` status separate from persisted run status.
- Immutable `GateRequirement`, `ReleasePolicy`, and `ReleaseEvaluation` models.
- Pure `ReleasePredicate.evaluate()` with no database writes.
- Missing/stale/bad mandatory evidence cannot produce PASS.
- Current FAIL + current PASS for one gate remains FAIL, preventing retry washing.
- `INFRA_ERROR` maps conservatively to BLOCKED.
- Requirement status derives exclusively from current mandatory evidence and never task state.
