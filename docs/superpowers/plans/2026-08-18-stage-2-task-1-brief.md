# Stage 2 Task 1 brief — Agent Server shell and compact state

Implement Task 1 from `2026-08-18-stage-2-orchestration-execution.md`.

Required outcomes:

- add the Stage 2 orchestration/runtime dependencies and commit the regenerated `uv.lock`;
- expose a compact typed `FactoryState` that carries IDs/references/decisions, not logs or source blobs;
- compile a thin LangGraph parent shell with `load_run -> schedule -> wait_or_finish`;
- expose the graph through `langgraph.json`;
- mount a custom FastAPI `/api/health` route;
- prove `uv run langgraph dev --no-browser` serves that route;
- keep SQL, Docker lifecycle, and authoritative scheduler logic outside LangGraph node bodies.

Stage 2 remains deterministic: no live SWE/model execution is introduced by this task.
