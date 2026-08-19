# InfiniteInterns Implementation Roadmap

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build InfiniteInterns from the approved architecture into a self-hosted, evidence-gated autonomous SWE factory that can certify itself with InternBench before being trusted with JobBot.

**Architecture:** The implementation is split into five independently testable stages. Each stage lands a working increment, preserves deterministic authority over completion, and becomes the base for the next stage. LangGraph Agent Server provides durable orchestration, PostgreSQL stores application state, isolated Docker workers execute code, Codex is the primary SWE backend, Kimi/DeepSeek provide independent review, and a deterministic evidence engine owns `VERIFIED`, `PASS`, and `DONE`.

**Tech Stack:** Python 3.13, uv, LangGraph Agent Server, FastAPI custom routes, PostgreSQL 16, Redis 7, SQLAlchemy 2.x, Alembic, psycopg 3, Pydantic 2, Typer, Rich, pytest, Playwright, Docker/Compose, TypeScript `@openai/codex-sdk` bridge, OpenAI-compatible Kimi/DeepSeek adapters.

**Spec:** `docs/architecture/infinite-interns-design.md`

## Global Constraints

- Requirements, not tasks, are the unit of completion.
- No LLM may directly mark a requirement `VERIFIED`, a release `PASS`, or a run `DONE`.
- Acceptance/release oracles are protected from implementation workers.
- Runtime evidence outranks model judgment.
- Retries cannot convert instability into success.
- Evidence is commit-bound and provenance-aware.
- Reviewers start in fresh contexts and communicate through typed findings.
- Workers are disposable; Git/spec/evidence/control-plane state is durable.
- Integration is serialized and anchored to `last_green_commit`.
- Infrastructure failures and engineering failures use different recovery paths.
- Outbound worker network is denied by default.
- Secrets are brokered/scoped and never persisted in model-visible state.
- Destructive/high-impact actions are denied or explicitly pre-authorized.
- Self-optimization cannot weaken completion, oracle, security, provenance, or anti-gaming rules.
- False `PASS` is a P0 factory defect.
- InfiniteInterns must pass InternBench before serious autonomous full-product work.

---

## Concrete v1 implementation decisions

### Runtime shape

Use a **self-hosted LangGraph Agent Server in single-host mode** for v1 workstation execution. The graph and InfiniteInterns HTTP API live in the same Agent Server image using LangGraph custom FastAPI routes. PostgreSQL and Redis are separate Compose services. The graph server never launches LLM worker processes directly through the Docker socket; a dedicated executor daemon owns Docker lifecycle operations.

Development commands:

```bash
uv run langgraph dev --no-browser
uv run langgraph up --watch
```

Production-like workstation mode uses `langgraph up`/Compose with persistent PostgreSQL and Redis. Cloud/Kubernetes execution remains behind the same `ExecutionBackend` interface.

### Python/package layout

Use Python 3.13 with uv and a `src/` layout:

```text
src/infinite_interns/
  api/
  agents/
  artifacts/
  config/
  context/
  db/
  domain/
  evidence/
  execution/
  graph/
  integration/
  internbench/
  release/
  scheduler/
  security/
  verification/
```

The CLI entry point is `interns = infinite_interns.cli:app`.

### Database

Use PostgreSQL 16. LangGraph Agent Server owns its own persistence tables. InfiniteInterns application tables live in PostgreSQL schema `ii` and are managed by Alembic. SQLAlchemy async sessions use psycopg 3.

Core tables:

```text
ii.runs
ii.spec_versions
ii.requirements
ii.tasks
ii.task_dependencies
ii.attempts
ii.evidence
ii.review_findings
ii.events
ii.deployments
ii.budgets
```

Task leases live on `ii.tasks` as `lease_owner`, `lease_epoch`, and `lease_expires_at`. All authoritative write APIs require the current lease epoch where task ownership is relevant.

### Artifact storage

Use URI form:

```text
artifact://runs/<run_id>/<kind>/<artifact_id>
```

Local backend root:

```text
.infinite-interns/artifacts/
```

The database stores artifact metadata and URI only. Raw logs, Playwright traces, screenshots, reports, patches, and large evidence blobs stay in the artifact backend.

### Model backends

Primary SWE backend: Codex.

Use the official TypeScript `@openai/codex-sdk` behind a small JSONL stdio bridge under `bridge/codex/`. Python owns the stable `AgentBackend` interface and launches the bridge in the isolated task environment. The bridge exposes `start`, `resume`, `run`, and `close` operations and returns typed `AgentResult` envelopes.

Independent reviewers use direct OpenAI-compatible HTTP adapters through a model gateway:

```text
Kimi default:      k3-256k
Kimi large audit:  k3
DeepSeek default:  deepseek-v4-pro
```

Kimi base URL: `https://api.kimi.com/coding/v1`.
DeepSeek base URL: `https://api.deepseek.com`.

Provider-specific responses are normalized into Pydantic schemas before the control plane uses them.

### Model gateway and secrets

Workers never receive master provider credentials. A `ModelGateway` service owns provider credentials and issues short-lived per-attempt capability tokens bound to:

```text
run_id
task_id
attempt_id
lease_epoch
provider
model
expires_at
```

Workers may see the scoped gateway token; compromise of that token does not grant access to GitHub, cloud, databases, or other runs. The gateway is the only component with real provider API keys.

Secret references use `secret://<provider>/<name>` in persisted state. Secret values are resolved only inside privileged services and are never written to events, evidence, checkpoints, prompts, or reports.

### Worker sandbox

Workstation v1 uses Docker + Git worktrees.

Each task receives:

```text
one worktree
one task branch
one app port range
one test database
one browser profile
one artifact namespace
one lease epoch
```

Worker containers run non-root, do not mount the host Docker socket, do not mount the integration checkout, and attach to an internal Docker network. Internet egress passes through an allowlist proxy; default worker egress is denied.

### Scheduler defaults

```text
lease TTL:                    90 seconds
heartbeat interval:           30 seconds
worker-health timeout:        90 seconds
agent no-event probe:         10 minutes
semantic-stall threshold:     20 minutes
ordinary task budget:         45 minutes
large task budget:            90 minutes
critical task budget:        120 minutes
max SWE workers:               4
max browser workers:           2
max heavy-test workers:        2
max concurrent integration:    1
```

Run defaults for `max-quality/overnight`:

```text
deadline: 8 hours
soft model budget: $200
hard model budget: $300
```

All values are configuration, not constants baked into graph logic.

### CLI/operator surface

Use Typer for commands and Rich for output/live status. Do not add a separate TUI framework in v1.

Commands delivered by certification:

```text
interns init
interns doctor
interns run
interns status
interns watch
interns inspect
interns pause
interns resume
interns stop
interns report
```

### Release backend

The first concrete deployment adapter is `DockerPreviewDeployment`. It creates a clean image/container from a fresh clone, returns a stable preview URL on an isolated local Docker network, and runs deployed E2E against that URL. The interface is intentionally compatible with externally hosted preview adapters without making an external cloud vendor mandatory for v1 certification.

### Observability

LangSmith tracing is optional and off by default. InfiniteInterns always writes structured application events and OpenTelemetry-compatible logs locally. Enabling LangSmith must not change correctness or completion semantics.

### InternBench v1 products

Certification uses three greenfield mini-products plus one brownfield workload:

1. `issue-tracker` — auth, projects, issues, comments, filtering, persistence.
2. `inventory` — products, stock movements, roles, audit history, persistence.
3. `booking` — accounts, availability, conflict prevention, cancellation, persistence.
4. `brownfield-shop` — an existing small full-stack app requiring a cross-stack feature without regressions.

Hidden evaluator suites live outside the candidate workload workspace and are mounted only into the evaluator container after the factory has produced its release candidate.

---

## Stage sequence

### Stage 1 — Deterministic foundation

Plan: `docs/superpowers/plans/2026-08-18-stage-1-deterministic-foundation.md`

Deliverable: installable `interns` package, typed domain/config models, PostgreSQL schema, event/evidence repositories, artifact URI backend, deterministic requirement status and release predicate, and `interns doctor`/`interns status` skeletons. No real model calls.

Acceptance gate:

```bash
uv run pytest tests/unit tests/integration/db -q
uv run ruff check .
uv run pyright
```

A test must prove that no code path can produce `DONE` when any mandatory release gate is false.

### Stage 2 — Durable orchestration and isolated execution

Plan: `docs/superpowers/plans/2026-08-18-stage-2-orchestration-execution.md`

Deliverable: LangGraph parent graph, task DAG, cycle detection, scheduler, leases/fencing, executor daemon, Docker worktrees, heartbeat/stall handling, serialized integration, `last_green_commit`, crash recovery, and a deterministic fake-worker end-to-end run.

Acceptance gate: a fixture repository with three dependency-safe tasks must execute two tasks concurrently, serialize integration, survive one killed worker, reject a zombie worker write, and finish on the expected green commit.

### Stage 3 — Agent, context, and review pipeline

Plan: `docs/superpowers/plans/2026-08-18-stage-3-agent-context-review.md`

Deliverable: `AgentBackend`, Codex SDK bridge, model gateway, Kimi/DeepSeek adapters, context packets, fresh-review contexts, typed findings, reproduction routing, task-local Codex repair loop, and model-routing policy.

Acceptance gate: a seeded defect repository must be repaired by the primary backend, reviewed from a fresh context, and reject at least one synthetic false-positive reviewer finding through deterministic reproduction.

### Stage 4 — Verification, security, and release

Plan: `docs/superpowers/plans/2026-08-18-stage-4-verification-security-release.md`

Deliverable: protected oracle handling, evidence invalidation, structural/unit/integration/browser/whole-product verification, Playwright failure packages, flaky classification, security capabilities, default-deny egress, secret refs, clean-room build, Docker preview deployment, deployed E2E, and deterministic release evaluation.

Acceptance gate: the same release candidate must fail when a protected E2E is broken, when evidence is stale, when a critical test is flaky, or when an unauthorized action is attempted; it passes only after all required evidence is regenerated for the current commit.

### Stage 5 — Operator UX and InternBench certification

Plan: `docs/superpowers/plans/2026-08-18-stage-5-operator-internbench.md`

Deliverable: full CLI/API surface, dry-run/readiness, run reports, budgets/deadlines, provider degradation, InternBench deterministic/security/chaos suites, mini-product harness, hidden evaluator, champion/challenger metadata, and certification report.

Acceptance gate: deterministic/safety suites have zero violations, full-product certification has zero false factory `PASS` results, and the configured product-building threshold from the architecture is met.

---

## Build-order rule

Do not begin Stage N+1 until Stage N's acceptance gate is green on the integration branch. Stage plans may be refined only to resolve implementation discoveries; any change that weakens architecture invariants requires an explicit architecture amendment.

## Commit policy

Each task in the stage plans ends with a focused commit. Use conventional prefixes:

```text
build:
feat:
fix:
test:
docs:
refactor:
chore:
```

Do not combine unrelated stage tasks in one commit.

## CI progression

Stage 1 introduces baseline Python CI. Each stage adds its own required gates to the same workflow. By Stage 5, required CI includes:

```text
format/lint
typecheck
unit
postgres integration
scheduler/lease tests
executor sandbox tests
provider-contract tests with fakes
verification/oracle tests
security-policy tests
chaos tests
InternBench deterministic subset
```

Live paid-provider tests are explicit opt-in jobs and never required for ordinary pull requests. Release certification runs them under a configured provider budget.
