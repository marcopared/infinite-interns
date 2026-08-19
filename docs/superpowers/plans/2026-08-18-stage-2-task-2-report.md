# Stage 2 Task 2 report

Status: COMPLETE.

## RED evidence

Actions run `32309275134` passed locked dependency sync and Ruff, then failed during unit collection because `infinite_interns.scheduler` did not exist.

## Initial GREEN evidence

Actions run `32309429428` passed the full repository gate after implementing deterministic Kahn validation and dependency-safe readiness.

## Review finding and regression RED

Review found that `@dataclass(frozen=True)` did not protect the internal dictionary objects from mutation. The advertised immutable graph could therefore be changed after validation.

A regression test was added first. Actions run `32309529457` failed exactly because mutation of `parents_by_task` did not raise.

The internal maps were then wrapped with `MappingProxyType` while adjacency sets remain `frozenset` values.

## Final GREEN evidence

Actions run `32309673697` passed:

```text
uv sync --dev --locked                 PASS
uv run ruff check .                    PASS
uv run pytest tests/unit -q            PASS
uv run alembic upgrade head            PASS
uv run pytest tests/integration -q     PASS
uv run pyright                         PASS
Smoke LangGraph Agent Server           PASS
```

## Deliverables

- side-effect-free immutable `TaskDag`;
- deterministic cycle rejection;
- lexical root/downstream readiness;
- readiness restricted to `DONE`/`VERIFIED` dependencies;
- explicit rejection of missing status entries;
- regression coverage for deep immutability.
