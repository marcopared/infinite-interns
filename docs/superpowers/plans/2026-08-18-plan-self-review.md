# InfiniteInterns Implementation Plan Self-Review

**Date:** 2026-08-18
**Architecture source:** `docs/architecture/infinite-interns-design.md`
**Roadmap:** `docs/superpowers/plans/2026-08-18-infinite-interns-implementation-roadmap.md`

## Result

**READY FOR IMPLEMENTATION EXECUTION.**

The plan set was reviewed for architecture coverage, placeholder/incomplete instructions, cross-stage dependency order, authority consistency, provider integration, and type/interface continuity. The review found and corrected several gaps before implementation begins.

## Required execution order

1. `2026-08-18-stage-1-deterministic-foundation.md`
2. `2026-08-18-stage-2-orchestration-execution.md`
3. `2026-08-18-stage-2b-repository-bootstrap.md`
4. `2026-08-18-stage-3a-specification-planning.md`
5. `2026-08-18-stage-3-agent-context-review.md` (Stage 3B)
6. `2026-08-18-stage-4-verification-security-release.md`
7. `2026-08-18-stage-4a-oracle-amendment-release-policy.md` is a **mandatory Stage 4 companion**: implement its oracle-amendment task immediately after protected-oracle foundations are in place and its composite-release task before the sole `DONE` transition.
8. `2026-08-18-stage-5-operator-internbench.md`

No later stage may start until the preceding stage's acceptance gate is green on the integration branch.

## Architecture coverage matrix

| Approved architecture concern | Implementation coverage |
|---|---|
| Deterministic authority / no LLM `DONE` | Stage 1 evidence predicate; Stage 4/4A sole completion transition and universal release facts |
| Small durable FactoryState | Stage 2 LangGraph compact state |
| PostgreSQL source of truth | Stage 1 DB; Stage 2 leases/events; later repositories |
| Brownfield + greenfield bootstrap | Stage 2B |
| Pre-existing failure provenance | Stage 2B |
| Spec Compiler | Stage 3A |
| Assumption risk policy | Stage 3A |
| Product/Architecture/Testability critic fanout | Stage 3A |
| Spec synthesizer + immutable revision loop | Stage 3A |
| Test Architect before implementation | Stage 3A |
| Acceptance oracle coverage | Stage 3A; execution/protection Stage 4 |
| Architecture artifact | Stage 3A |
| Task dependency DAG + cycle detection | Stage 2 + Stage 3A persistence |
| Cross-artifact audit / no uncovered requirements | Stage 3A |
| Parallel isolated workers | Stage 2 |
| Leases, fencing, idempotency, heartbeat | Stage 2 |
| Worktrees + isolated Docker runtimes | Stage 2 |
| Serialized integration + `last_green_commit` | Stage 2 |
| Codex task-local persistent context | Stage 3B official Python SDK threads |
| Fresh reviewer contexts | Stage 3B |
| Kimi/DeepSeek independent review | Stage 3B |
| Review claims -> executable reproduction | Stage 3B |
| Bounded escalation / replan / BLOCKED | Stage 3B |
| Context packets + repository map | Stage 3B |
| Evidence-backed durable memory | Stage 3B |
| E0 structural/static evidence | Stage 4 |
| Unit/integration/DB evidence | Stage 4 |
| Mutation testing for critical modules | Stage 4 |
| Playwright browser acceptance | Stage 4 |
| Whole-product journeys | Stage 4 |
| Failure forensic packages | Stage 4 |
| Retry/flaky anti-washing | Stage 4 |
| Evidence freshness/invalidation | Stage 4 |
| Protected oracle + vacuity checks | Stage 4 |
| Approved oracle amendment flow | Stage 4A |
| Factory sandbox/capability policy | Stage 4 |
| Default-deny network | Stage 4 |
| Secret refs/redaction | Stage 4 |
| Product application-security/access matrices | Stage 4 |
| Convergence distrusts completed plan | Stage 4 |
| Confirmed gaps create new tasks | Stage 4 |
| Clean clone/install/migrate/build | Stage 4 |
| Preview deployment + deployed E2E | Stage 4 |
| Restart/persistence release check | Stage 4 |
| Exact universal release predicate | Stage 4A |
| One and only one `DONE` writer | Stage 4 + Stage 4A |
| Operator CLI/API | Stage 5 |
| Dry run/readiness | Stage 5 |
| Budget/deadline convergence mode | Stage 5 |
| Explicit provider degradation | Stage 5 |
| FactoryBench/InternBench deterministic/security/chaos | Stage 5 |
| Synthetic SWE benchmarks | Stage 5 |
| Greenfield mini-products | Stage 5 |
| Brownfield benchmark | Stage 5 |
| Hidden independent evaluator | Stage 5 |
| Zero false `PASS` certification | Stage 5 |
| Reviewer precision/recall/incremental yield | Stage 5 |
| Real failure -> regression case | Stage 5 |
| Repeated experiments/champion-challenger | Stage 5 |
| Self-improvement cannot weaken judge | Stage 5 plus global constraints |

## Corrections made during self-review

### 1. Added repository bootstrap

Initial plans jumped from orchestration to specification without implementing the approved `BOOTSTRAP` state. Stage 2B now covers brownfield/greenfield classification, base commit, project guidance, bounded command detection, pre-existing failures, and neutral greenfield initialization.

### 2. Added explicit specification critique/synthesis loop

The initial Stage 3A plan had a Spec Compiler but did not fully implement the approved Product Critic / Architecture Critic / Testability Critic fanout and synthesizer revision cycle. Stage 3A now requires fresh critic contexts, typed critiques, immutable spec revisions, bounded re-review, and a review-accepted spec before downstream planning.

### 3. Added convergence as executable implementation work

The initial verification plan did not explicitly implement the approved post-plan convergence loop. Stage 4 now compares the current accepted spec/traceability/runtime product, reproduces gap candidates, creates repair tasks for confirmed gaps, and blocks release until convergence is clean.

### 4. Added application-security evidence

Factory sandbox security alone was insufficient. Stage 4 now includes application access-control matrices and blocking executable security gates in addition to control-plane sandbox/network/secret policy.

### 5. Added approved oracle amendment lifecycle

Read-only oracle protection alone did not define how a legitimately incorrect or changed oracle could evolve. Stage 4A requires spec/evidence-backed justification, fresh Test Architect amendment, fresh Oracle Reviewer approval, immutable oracle version/hash, and automatic invalidation of affected evidence.

### 6. Made the final predicate explicit and caller-proof

Stage 4A defines `ReleaseFacts` covering requirement completeness, tests, stability, critical blocked tasks, blocking reviews, product/factory security, convergence, clean bootstrap, migration/build/deployment, deployed E2E, restart persistence, traceability/evidence completeness, and stale evidence. `complete_run()` accepts only run/expected-commit identity; it cannot accept a caller-supplied PASS object.

### 7. Replaced the custom TypeScript Codex bridge with OpenAI's official Python SDK

The current OpenAI Codex repository now publishes the `openai-codex` Python SDK, including async clients, thread start/resume, workspace sandbox presets, and the matching pinned Codex runtime. Stage 3B now uses `AsyncCodex` directly and configures a custom Codex model provider that points to InfiniteInterns ModelGateway. This removes an unnecessary Node/TypeScript bridge and keeps the v1 control plane Python-native.

### 8. Clarified credential isolation

The Codex SDK process can inherit its worker process environment. Therefore the security boundary is the executor-created worker container/process environment: workers are launched with a minimal explicit environment and only receive a short-lived `INFINITE_INTERNS_MODEL_TOKEN`. `CodexConfig` is used to select the gateway provider; it is not treated as an environment-scrubber.

### 9. Added evaluation/learning details

Stage 5 now records configuration refs and eventual outcomes, reviewer precision/seeded recall/incremental yield, real failures as regression cases, repeated experiments, and champion/challenger promotion with critical holdout floors. No learned router or fine-tuning is required for v1.

## Placeholder scan

Repository plan search was run for:

```text
TBD
TODO
implement later
bridge/codex
@openai/codex-sdk
npm test
```

The current plan set contains no intentional incomplete implementation placeholders and no remaining dependency on the removed TypeScript Codex bridge. Python type syntax such as `tuple[str, ...]` is not a placeholder.

## Interface consistency checks

- `RunStatus.DONE` is a terminal run status; there is no persisted intermediate run `PASS` state.
- `EvidenceResult.PASS` is the release-predicate result type; only Stage 4/4A transition code can convert a current PASS evaluation into `RunStatus.DONE`.
- Requirement verification derives from mandatory current evidence, never task state.
- Task `DONE` means integrated task work, not product/release completion.
- Stage 3A planning roles use a provider-neutral `PlanningAgent`; Stage 3B binds real providers without changing planning service contracts.
- Stage 3B SWE roles use `AgentBackend` and normalize all providers to strict Pydantic outputs.
- Codex task-local state is a persisted thread ID; reviewers start fresh threads.
- Task ownership is always fenced by lease epoch.
- Release transition assembles current facts itself instead of trusting caller data.
- Hidden InternBench evaluators remain outside candidate workspaces.

## Intentional v1 deferrals

These are deliberate scope choices, not missing implementation details:

- Kubernetes execution backend: interface only after Docker workstation certification.
- Hosted cloud deployment adapters: `DockerPreviewDeployment` is the first concrete adapter.
- Learned model router: deterministic routing first; collect evaluation history before considering learned selection.
- Fine-tuning: no v1 fine-tuning.
- Dedicated web dashboard: API + Typer/Rich operator surface first.
- Mandatory LangSmith: optional observability only; correctness does not depend on it.

## Implementation readiness decision

The plan set now covers the approved architecture without intentionally weakening any authority, evidence, security, convergence, or certification invariant. Implementation may begin with Stage 1 under the selected execution workflow.
