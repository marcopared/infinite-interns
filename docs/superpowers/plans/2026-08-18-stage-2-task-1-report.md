# Stage 2 Task 1 report

Status: COMPLETE.

## RED evidence

GitHub Actions run `32308139332` reached the unit suite after a successful locked dependency sync and Ruff check, then failed during collection with:

```text
ModuleNotFoundError: No module named 'infinite_interns.graph'
```

The failure was caused by the missing Stage 2 graph boundary before implementation.

## Implementation discoveries

- The current locked dependency set resolves LangGraph `1.2.11`, LangGraph CLI `0.4.31`, FastAPI `0.141.1`, and HTTPX `0.28.1`.
- LangGraph's public graph module does not expose a complete Pyright stub surface under this strict configuration. The exception is isolated to `graph/factory.py`; state and factory services remain strictly typed.
- Ruff's pinned import fixer removed an extra blank line that manual formatting had repeatedly missed. The temporary autofix workflow was deleted afterward.
- CI was changed to run feature branches on pull requests only, run `main` on push, and cancel superseded runs in the same workflow/ref group. This removes duplicate executions without weakening any gate.

## GREEN evidence

GitHub Actions run `32309102027` passed every Task 1 gate:

```text
uv sync --dev --locked                 PASS
uv run ruff check .                    PASS
uv run pytest tests/unit -q            PASS
uv run alembic upgrade head            PASS
uv run pytest tests/integration -q     PASS
uv run pyright                         PASS
Smoke LangGraph Agent Server           PASS
```

The smoke step starts `uv run langgraph dev --no-browser`, polls `http://127.0.0.1:2024/api/health`, parses the response as JSON, and requires exactly `{"status": "ok"}`.

## Deliverables

- Stage 2 dependency graph and regenerated `uv.lock`.
- Compact `FactoryState` containing IDs/references/control values rather than logs or source blobs.
- Thin typed node-service boundary and compiled parent graph shell.
- `langgraph.json` graph/HTTP configuration.
- Custom FastAPI health route.
- Unit coverage for compact state and route registration/behavior.
- Permanent Agent Server smoke gate in CI.
