# InfiniteInterns Agent Map

This file is a navigation map, not the full project specification.

## Canonical architecture

- `docs/architecture/README.md` — architecture index
- `docs/architecture/infinite-interns-design.md` — approved system design

## Implementation plans

Start with:

- `docs/superpowers/plans/2026-08-18-infinite-interns-implementation-roadmap.md` — master roadmap and v1 decisions
- `docs/superpowers/plans/2026-08-18-plan-self-review.md` — coverage review and required execution order

Required execution order:

1. `2026-08-18-stage-1-deterministic-foundation.md`
2. `2026-08-18-stage-2-orchestration-execution.md`
3. `2026-08-18-stage-2b-repository-bootstrap.md`
4. `2026-08-18-stage-3a-specification-planning.md`
5. `2026-08-18-stage-3-agent-context-review.md` (Stage 3B)
6. `2026-08-18-stage-4-verification-security-release.md`
7. `2026-08-18-stage-4a-oracle-amendment-release-policy.md` (mandatory Stage 4 companion)
8. `2026-08-18-stage-5-operator-internbench.md`

All files are under `docs/superpowers/plans/`.

## Core invariant

Agents may propose that work is complete. Only executable evidence may prove that it is complete.

No agent may directly mark a requirement verified, a release passed, or a run `DONE`.

## Current phase

Stages 1 and 2 are integrated on `main`: the deterministic authority foundation plus durable LangGraph orchestration, PostgreSQL task ownership/leases/fencing, isolated worktrees and Docker workers, crash recovery, stale-worker rejection, and serialized regression-gated integration around `last_green_commit`.

Stage 2B repository bootstrap is implemented on `impl/stage-2b-repository-bootstrap` and is in final certification/merge review. It adds deterministic brownfield/greenfield classification, bounded provenance-aware guidance and command discovery, isolated brownfield baseline execution, neutral greenfield initialization, immutable baseline artifacts, crash-safe baseline reference recovery, and mandatory `bootstrap -> specification_pending` graph ordering.

After Stage 2B is integrated, the next implementation stage is **Stage 3A — specification/planning**. Do not enter specification/planning without a persisted `baseline_ref`, and do not start Stage 3A implementation until the Stage 2B acceptance gate is green and Stage 2B is integrated.

Stage execution evidence and per-task review records are under `docs/superpowers/plans/2026-08-18-stage-1-*`, `docs/superpowers/plans/2026-08-18-stage-2-*`, and `docs/superpowers/plans/2026-08-20-stage-2b-*`.

## Current verification gate

```bash
uv sync --dev --locked
uv run ruff check .
uv run pytest tests/unit -q
uv run alembic upgrade head
uv run pytest tests/integration -q
uv run pytest tests/chaos -q
uv run pyright
docker compose -f docker-compose.workstation.yml config --quiet
docker compose -f docker-compose.workstation.yml build agent-server executor
```

The CI gate additionally launches `langgraph dev` and requires `/api/health` to return `{"status":"ok"}`.

Local PostgreSQL for non-CI work:

```bash
docker compose -f docker-compose.dev.yml up -d postgres
export INFINITE_INTERNS_DATABASE_URL='postgresql+psycopg://interns:interns@127.0.0.1:54329/infinite_interns'
uv run alembic upgrade head
```

Runtime bootstrap also uses `INFINITE_INTERNS_ARTIFACT_ROOT` when set; otherwise artifacts are rooted at `.infinite-interns/artifacts`.

## Authority boundaries

- PostgreSQL is authoritative for task ownership, leases/fencing, durable task state, events, integration anchors, and each run's `baseline_ref`.
- LangGraph graph state contains refs/status summaries only; graph nodes do not become an alternate database.
- Repository bootstrap records a base commit before implementation work and cannot enter specification without a durable baseline artifact reference.
- Brownfield baseline commands execute in a disposable detached worktree pinned to the recorded base commit; they do not run in the workload checkout.
- Greenfield bootstrap may create only neutral repository/control metadata; it may not invent product architecture before specification.
- Repository guidance remains `REPOSITORY_CONTENT`, never factory policy, and detected commands come only from bounded rules or explicit tokenized overrides.
- Scheduler readiness/capacity/resource conflicts are deterministic and model-free.
- A worker result is authoritative only when its lease epoch is still current.
- Workers never receive `/var/run/docker.sock`; only the executor daemon may own Docker lifecycle authority.
- Integration is single-writer per run and cannot advance `last_green_commit` unless regression verification passes.
- A killed or stale worker cannot convert incomplete work into success.

## Working rules

- Follow the current stage plan task-by-task with test-first implementation and focused commits.
- Do not begin a later stage until the current stage acceptance gate is green on the integration branch.
- Preserve deterministic authority over scheduling, verification, integration, security policy, convergence, and release.
- Treat Git, specifications, evidence, and durable events as authoritative state; agent conversation state is disposable.
- Keep reviewers in fresh contexts and communicate through typed artifacts.
- Protect acceptance/release oracles from implementation workers; use the independent amendment flow for legitimate oracle changes.
- Prefer small, explicit modules and mechanically enforced boundaries over giant prompts.
- Any implementation discovery that would weaken an approved architecture invariant requires an explicit architecture amendment rather than an ad hoc workaround.
