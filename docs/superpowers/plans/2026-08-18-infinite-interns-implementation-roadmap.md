# InfiniteInterns Implementation Roadmap

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build InfiniteInterns from the approved architecture into a self-hosted, evidence-gated autonomous SWE factory that can certify itself with InternBench before being trusted with JobBot.

**Architecture:** Implementation is split into six independently testable increments: deterministic authority, durable orchestration/execution, specification/planning, agent/context/review, verification/security/release, and operator/InternBench. LangGraph Agent Server provides durable orchestration, PostgreSQL stores application state, isolated Docker workers execute code, Codex is the primary SWE backend, Kimi/DeepSeek provide independent review, and deterministic evidence code owns `VERIFIED`, release `PASS`, and the only `DONE` transition.

**Tech Stack:** Python 3.13, uv, LangGraph Agent Server, FastAPI custom routes, PostgreSQL 16, Redis 7, SQLAlchemy 2.x, Alembic, psycopg 3, Pydantic 2, Typer, Rich, pytest, Playwright, Docker/Compose, TypeScript `@openai/codex-sdk` bridge, OpenAI-compatible Kimi/DeepSeek adapters.

**Spec:** `docs/architecture/infinite-interns-design.md`

## Global Constraints

- Requirements, not tasks, are the unit of completion.
- No LLM may directly mark a requirement `VERIFIED`, a release `PASS`, or a run `DONE`.
- Acceptance/release oracles are produced before implementation and protected from implementation workers.
- Runtime evidence outranks model judgment.
- Retries cannot convert instability into success.
- Evidence is commit-bound, environment-bound, verifier-version-bound, and provenance-aware.
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

Use a **self-hosted LangGraph Agent Server in single-host workstation mode** for v1. The graph and InfiniteInterns HTTP API run in the Agent Server image using custom FastAPI routes. PostgreSQL and Redis are separate services. The Agent Server never owns the Docker socket; a dedicated executor daemon owns Docker lifecycle operations.

Development:

```bash
uv run langgraph dev --no-browser
```

Production-like workstation mode uses the Agent Server/Docker stack with persistent PostgreSQL and Redis. Future Kubernetes execution remains behind `ExecutionBackend`.

### Python/package layout

Use Python 3.13 with uv and a `src/` layout:

```text
src/infinite_interns/
  api/
  agents/
  artifacts/
  budget/
  config/
  context/
  convergence/
  db/
  domain/
  evidence/
  execution/
  gateway/
  graph/
  integration/
  internbench/
  oracles/
  planning/
  release/
  review/
  scheduler/
  security/
  specification/
  verification/
```

CLI entry point:

```toml
[project.scripts]
interns = "infinite_interns.cli:app"
```

### Database

Use PostgreSQL 16. LangGraph owns its persistence tables. InfiniteInterns application tables live in schema `ii`, managed by Alembic via SQLAlchemy async + psycopg 3.

Core tables:

```text
ii.runs
ii.product_inputs
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

Task leases use `lease_owner`, `lease_epoch`, and `lease_expires_at`. Authoritative task writes validate current epoch.

### Artifact storage

URI:

```text
artifact://runs/<run_id>/<kind>/<artifact_id>
```

Local backend root:

```text
.infinite-interns/artifacts/
```

PostgreSQL stores artifact metadata/URI, not large bodies.

### Model backends and gateway

Primary SWE backend: Codex through the official TypeScript `@openai/codex-sdk` in `bridge/codex/`.

The bridge is configured with:

```text
baseUrl = InfiniteInterns ModelGateway OpenAI-compatible /v1 endpoint
apiKey  = short-lived attempt capability token
```

The worker therefore does not receive the master OpenAI credential. The gateway validates the token's run/task/attempt/lease epoch/provider/model scope, then forwards the request with the real provider credential. The gateway must support the OpenAI Responses API surface used by Codex, not only Chat Completions.

Independent reviewers also use the gateway:

```text
Kimi default:      k3-256k
Kimi large audit:  k3
DeepSeek default:  deepseek-v4-pro
```

Provider-specific responses are normalized into strict Pydantic schemas before control-plane routing.

### Secret model

Persist references such as:

```text
secret://providers/openai
secret://providers/kimi
secret://providers/deepseek
```

Secret values resolve only in privileged services and never enter events, evidence, checkpoints, reports, or persisted prompts. Worker-visible capability tokens are short-lived and scoped, not master credentials.

### Worker sandbox

Workstation v1 uses Docker + Git worktrees. Each task receives one worktree, branch, isolated test DB, browser profile, artifact namespace, port range, and lease epoch.

Workers run non-root, do not mount the host Docker socket or integration checkout, attach to an internal Docker network, and use an allowlist proxy for approved outbound traffic.

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

Default `max-quality/overnight` run:

```text
deadline: 8 hours
soft model budget: $200
hard model budget: $300
```

These are configuration defaults, not graph constants.

### Operator surface

Use Typer + Rich. No separate TUI framework in v1.

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

First deployment adapter: `DockerPreviewDeployment`. It builds from a fresh clone at exact candidate SHA, creates a fresh DB, runs migrations/build/start, returns an isolated preview URL, and runs deployed E2E. The `DeploymentBackend` interface allows future hosted preview adapters.

### Observability

LangSmith is optional and off by default. Structured application events and local OpenTelemetry-compatible logs are always present. Turning tracing on/off cannot alter correctness semantics.

### InternBench v1 workloads

1. `issue-tracker` — auth, projects, issues, comments, filtering, authorization, persistence.
2. `inventory` — products, stock ledger, roles, audit history, invariants, persistence.
3. `booking` — accounts, availability, concurrency conflict prevention, cancellation, authorization, persistence.
4. `brownfield-shop` — an existing full-stack app requiring a cross-stack feature without regressions.

Hidden evaluators are inaccessible to candidate workers and mounted only after the factory produces a terminal candidate result.

---

## Build sequence

### Stage 1 — Deterministic foundation

Plan: `docs/superpowers/plans/2026-08-18-stage-1-deterministic-foundation.md`

Deliverable: package/config/domain contracts, PostgreSQL schema/repositories, artifact backend, deterministic requirement/release evaluation, doctor/status skeleton. No real model calls and no `DONE` transition yet.

Gate: false release `PASS` is impossible with missing/stale/failing mandatory evidence.

### Stage 2 — Durable orchestration and isolated execution

Plan: `docs/superpowers/plans/2026-08-18-stage-2-orchestration-execution.md`

Deliverable: LangGraph shell, task DAG engine, leases/fencing, executor daemon, Docker worktrees, heartbeats/stall recovery, serialized integration, `last_green_commit`, fake-worker end-to-end run.

Gate: dependency-safe parallel tasks execute, one killed worker is recovered, zombie writes are rejected, integration remains green.

### Stage 3A — Specification and planning

Plan: `docs/superpowers/plans/2026-08-18-stage-3a-specification-planning.md`

Deliverable: immutable product input/spec versions, assumptions policy, Spec Compiler, independent Test Architect oracle draft, Architect artifact, Task Planner, traceability graph, cross-artifact audit, and planning-readiness gate.

Gate: no implementation task becomes READY until required requirements have acceptance coverage, architecture mapping, justified task coverage, an acyclic DAG, and a clean cross-artifact audit.

### Stage 3B — Agent, context, and review pipeline

Plan: `docs/superpowers/plans/2026-08-18-stage-3-agent-context-review.md`

Deliverable: `AgentBackend`, Codex SDK bridge through the scoped model gateway, Kimi/DeepSeek adapters, context packets, fresh-review contexts, typed findings, reproduction routing, task-local repair loop, and deterministic model-routing tiers.

Gate: seeded defect is repaired, reviewer context is cold, false-positive finding is rejected by reproduction, confirmed finding becomes repair work.

### Stage 4 — Verification, convergence, security, and release

Plan: `docs/superpowers/plans/2026-08-18-stage-4-verification-security-release.md`

Deliverable: protected oracles, evidence invalidation, E0-E5 verification, Playwright failure packages, stability/flaky classification, application-security gates, worker security policy, clean-room preview deployment, convergence gap loop, deployed E2E, and the sole deterministic `DONE` transition.

Gate: release is denied independently by stale evidence, failed/unstable critical journeys, open reproduced convergence gaps, security failures, clean-bootstrap failure, or deployed-E2E failure; exactly one valid completion path exists.

### Stage 5 — Operator UX and InternBench certification

Plan: `docs/superpowers/plans/2026-08-18-stage-5-operator-internbench.md`

Deliverable: full CLI/API, dry-run/readiness, budgets/deadlines, reports, provider degradation, deterministic/security/chaos InternBench, synthetic SWE cases, mini-product hidden evaluators, and certification report.

Gate: zero control/security violations, zero false factory `PASS` results, hidden critical journeys/clean bootstrap/deployed E2E pass for every claimed PASS, and architecture-defined full-product completion threshold is met.

---

## Build-order rule

Do not begin the next increment until the previous acceptance gate is green on the integration branch. Plans may be refined for implementation discoveries, but any change that weakens architecture invariants requires an explicit architecture amendment.

## Commit policy

Each task ends with a focused commit using conventional prefixes:

```text
build:
feat:
fix:
test:
docs:
refactor:
chore:
```

## CI progression

By certification, required no-paid-provider CI includes:

```text
format/lint
typecheck
unit
postgres integration
spec/planning traceability tests
scheduler/lease tests
executor sandbox tests
provider-contract tests with fakes
verification/oracle tests
convergence tests
security-policy tests
chaos tests
InternBench deterministic subset
```

Live paid-provider tests are opt-in jobs. Full certification runs them only with an explicit provider budget and configured credentials.
