# InfiniteInterns Design Specification

**Status:** Approved architecture
**Date:** 2026-08-18

## 1. Purpose

InfiniteInterns is a specification-driven, evidence-gated, fault-tolerant autonomous software-engineering factory. It accepts a repository plus a product specification or goal and drives the project through specification, architecture, implementation, testing, review, integration, convergence, clean-room deployment, and deployed end-to-end verification.

The core invariant is:

> Agents may propose that work is complete. Only executable evidence may prove that it is complete.

No LLM may directly mark a requirement `VERIFIED`, a release `PASS`, or a run `DONE`. Those transitions belong to deterministic control-plane code operating on current, provenance-aware evidence.

## 2. Authority model

Authority rises with executable evidence:

1. model opinion,
2. static/code review,
3. compile/type/lint/unit evidence,
4. integration/API/database evidence,
5. browser acceptance evidence,
6. whole-product runtime evidence,
7. clean-room deployed evidence.

Higher-level runtime evidence overrides model judgment. A reviewer can propose a defect; a reproduction gate determines whether the defect is real whenever the claim is executable.

`DONE` has one valid incoming edge only: `ReleasePredicate.evaluate(evidence_store) == PASS`.

## 3. Top-level protocol

```text
START
  -> DOCTOR
  -> BASELINE
  -> SPECIFICATION
  -> ACCEPTANCE_ORACLE
  -> ARCHITECTURE
  -> TASK_DAG
  -> BUILD_AND_INTEGRATE
  -> CONVERGENCE
       -> gaps -> TASK_DAG
       -> clean -> RELEASE
  -> RELEASE
       -> failure/gap -> TASK_DAG
       -> pass -> DONE
```

The factory uses nested loops rather than one giant agent circle. Local coding/debugging, review/repair, integration/regression, convergence/build, and release/repair are separate feedback loops with separate authorities.

## 4. Specification and requirement traceability

The source product request is immutable history. Clarifications and approved changes create new spec versions; agents may not silently simplify requirements because implementation is difficult.

The spec compiler produces stable requirement IDs, user journeys, non-functional requirements, constraints, invariants, assumptions, glossary/domain concepts, and acceptance criteria.

Assumptions are classified:

- low risk: choose a reasonable default automatically,
- medium risk: choose a reversible default and record it,
- high risk/irreversible: avoid the decision or require an explicit operator policy/interrupt.

Before implementation, a cross-artifact audit checks the spec, architecture, task DAG, and acceptance oracle for contradictions or missing coverage.

Requirements, not tasks, are the unit of completion.

Each requirement maps to implementation commits plus evidence: unit, integration, acceptance, browser/runtime, review, clean-room, and deployment evidence as required by criticality.

## 5. Protected acceptance oracle

A dedicated Test Architect creates acceptance/runtime oracles before implementation where practical.

Implementation workers may add or strengthen normal tests, but they may not delete, weaken, skip, or modify protected acceptance/release oracles or completion policy. Protection must be enforced by filesystem/capability boundaries, not prompts alone.

Important new oracles should undergo a vacuity check: if the feature does not exist but the test already passes, the oracle is suspicious and must be reviewed.

Critical business logic should use invariants/property testing where it adds coverage. Milestone/release validation should use targeted mutation testing for critical modules so the system can detect tests that execute code without detecting broken behavior.

## 6. Verification and evidence

Evidence levels:

- **E0 Structural:** build, compile, typecheck, lint, schema validation, architecture rules, dependency/secret/static-security checks.
- **E1 Unit/Invariant:** focused domain behavior and property/invariant checks.
- **E2 Integration:** real ephemeral internal infrastructure where practical; API/service/database behavior.
- **E3 Browser Acceptance:** Playwright drives the application as a user and validates visible behavior, network effects, and persistence.
- **E4 Whole-Product Journeys:** longitudinal flows cross subsystem boundaries and verify coherent product behavior.
- **E5 Clean Deployment:** fresh clone, fresh install, fresh DB, migrations, production build, deploy, and deployed E2E.

Runtime evidence outranks model review. If unit tests and reviewers pass but the user journey fails, the requirement fails.

Every evidence record is bound to run ID, requirement ID, Git commit, environment hash, verifier/tool version, timestamp, and producer. Relevant code changes invalidate stale downstream evidence.

Retries never convert unstable behavior into success. A critical test that passes only intermittently is `UNSTABLE`, not `PASS`.

The final release predicate requires, at minimum:

```text
FUNCTIONAL
AND QUALITY
AND SECURITY
AND REPRODUCIBLE
AND DEPLOYABLE
AND CONVERGED
```

where critical requirements, acceptance tests, cross-product journeys, security gates, clean bootstrap, production build, deployment, deployed E2E, traceability, and reproduced convergence gaps are all satisfied according to policy.

## 7. Worker model and agent roster

Initial model policy is Codex-first.

- Product/spec compiler: fresh Codex context.
- Architect: fresh Codex context.
- Test Architect: fresh Codex context.
- Primary implementer/fixer: Codex.
- Normal reviewer: fresh Codex context, never the author conversation.
- Primary cross-model adversary: Kimi K3.
- Secondary adversary/root-cause diagnostician: latest supported DeepSeek model.
- Runtime QA: Codex + Playwright and deterministic runtime tools.
- Integrator: deterministic logic first, Codex only when semantic merge repair is needed.
- Convergence audit: Codex, with Kimi/DeepSeek for high-value independent gap search.
- Release runner: deterministic.

Cross-model diversity is risk-based, not mandatory on trivial work. High-risk changes such as authentication, authorization, migrations, security-sensitive data handling, and final release candidates receive stronger independent review.

Model reviewers return typed findings rather than essays. Findings include requirement, severity, confidence, claim, reproduction strategy, affected paths, and evidence references. Claims are reproduced where possible; models do not vote on truth.

Escalation is staged: task-local Codex debugging, fresh Codex repair, Kimi/DeepSeek diagnosis, alternative implementation strategy, architecture challenge/decomposition, then `BLOCKED` if the task is objectively unresolved. One stuck task may not consume the entire run.

## 8. Context engineering and agent-computer interface

`AGENTS.md` is a concise navigation map, not an encyclopedia.

Durable memory lives in Git, structured repository docs, specifications, decisions, evidence, and validated learnings. Agent chat history is disposable.

Every worker receives a generated context packet containing only the information needed to start the task: role, objective, success conditions, relevant requirements, architecture constraints, protected paths, relevant ADRs, likely code/test areas, dependency outputs, current failures, tools, required evidence, and deadline/budget.

Context is progressively disclosed. Large logs and traces are stored as artifacts; agents receive normalized summaries and fetch slices on demand.

Reviewers receive cold context: spec, repo, diff, tests, runtime evidence, and invariants. They do not receive the implementer's reasoning diary.

Agent-to-agent communication happens through typed artifacts and repository state, not hidden conversations.

Durable memory types include `DECISION`, `RULE`, `LEARNING`, `WARNING`, `DEBT`, and `ASSUMPTION`. Memory candidates must be linked to evidence or accepted architecture/product decisions before promotion to durable project memory.

Stable instructions should migrate into executable lint, architecture, test, or policy rules whenever possible.

## 9. Task DAG, scheduling, and isolation

The planner produces a dependency DAG rather than a giant linear todo list. Only dependency-safe tasks execute concurrently.

Workers operate in isolated Git worktrees/containers with separate ports, databases, browser profiles, logs, and temporary state. Agents never concurrently modify the integration checkout.

Integration is serialized. Every accepted candidate is rebased/merged against the current `last_green_commit`, followed by required regression. If regression fails, the integration is repaired or reverted. The integration branch is never knowingly left broken while unrelated work continues.

The deterministic scheduler owns readiness, locking, task selection, budgets, timeouts, conflict rules, and concurrency. LLMs do not choose task eligibility.

A task state machine includes planned, ready, claimed, running, verifying, reviewing, repair, candidate, integrating, verified/done, blocked, cancelled, and superseded states.

## 10. Durable control plane and crash recovery

The v1 control plane uses LangGraph for orchestration/checkpointing and PostgreSQL as the durable application-level source of truth.

Workers are disposable. Run, requirement, task, attempt, evidence, and event records are durable.

Task claiming uses short renewable leases rather than long database transactions. Every lease has a monotonically increasing fencing epoch. A stale worker whose lease expired cannot publish authoritative state, evidence, or candidate commits after another worker has taken ownership.

External side effects use idempotency keys based on run/task/attempt/operation so retries do not duplicate workers, deployments, evidence, or other resources.

Heartbeats and progress events distinguish transient slowness from a stalled worker. Repeated semantic failure triggers strategy escalation rather than blind retry.

Infrastructure failures, engineering failures, external blockers, and control-plane failures take different recovery paths.

The system preserves a durable `last_green_commit` and can reconstruct a task from Git, spec, evidence, failure packages, and decisions even if the original model conversation is lost.

Budgets are hierarchical: tool/node retry, model attempt, task retry, architecture retry, and overall run budget. Near the overall deadline the scheduler enters convergence mode and prioritizes critical repairs, integration, regression, convergence, and release evidence over speculative improvements.

## 11. Security and trust boundaries

The model is never a security boundary.

Workers run inside OS/container-enforced isolation with workspace-only writes, no host Docker socket, no cluster-admin authority, no direct control-plane database access, and no unrestricted production credentials.

Outbound network is default-deny and granted through task-specific profiles such as `NET_NONE`, `NET_DEPENDENCIES`, `NET_DOCS`, `NET_TEST_EXTERNAL`, `NET_RELEASE`, and quarantined `NET_UNTRUSTED_WEB`.

Open-web research is separated from privileged SWE execution. A low-authority researcher with no secrets/write authority produces structured research artifacts; the privileged SWE consumes the artifact, not an unrestricted browsing context.

Secrets are resolved outside model context through scoped handles/capabilities. Credentials, network scope, task authority, and the current lease epoch must all agree before a privileged tool call succeeds.

Action classes:

- **A local reversible:** autonomous.
- **B isolated external/test:** autonomous when preconfigured.
- **C shared reversible:** requires explicit pre-authorization policy.
- **D destructive/high-impact:** deny by default or require explicit approval.

Coding agents do not directly own production release credentials. A separate deterministic release service owns scoped deployment actions.

The default `overnight` profile may build, test, create isolated test resources, create branches/PRs if configured, deploy preview/staging, and run full E2E, while denying destructive production actions and real-user side effects.

## 12. Convergence and clean-room release

After planned tasks finish, the factory deliberately distrusts the plan.

Convergence compares the original specification and traceability matrix against the current running product and identifies missing, partial, contradictory, unverified, or materially unrequested behavior. Reproduced gaps become new tasks and re-enter the normal build pipeline.

Once convergence is clean, release deliberately distrusts the development environment. The release service performs a fresh clone, fresh dependency installation, fresh database and migrations, production build, full clean-room acceptance, preview/staging deployment, deployed critical E2E, and persistence/restart checks according to workload policy.

A local green worktree is never sufficient evidence for release.

## 13. Model routing, evaluation, and self-improvement

Codex is the initial champion implementation backend, not a permanent hard-coded winner.

The unit under evaluation is the complete agent configuration: model, prompt, reasoning setting, context builder, retrieval policy, tools, retry policy, and session strategy.

Primary metrics include verified-requirement completion, full-release completion, first-pass verification, time to integrated green, human-intervention rate, escaped-defect rate, cost per verified requirement, and cost per successful release.

Reviewer metrics include reproduced-finding precision, seeded-defect recall, incremental defect discovery, and severity-weighted yield.

Routing starts rules-based and may become data-driven only after sufficient evidence. Cross-model review is invoked for expected information gain rather than because more agents appear sophisticated.

New models/prompts/tools use champion/challenger, hidden holdout, and optional shadow execution. Critical regressions prohibit promotion.

InfiniteInterns may optimize prompts, tools, context templates, retrieval, reviewer selection, model routing, reasoning effort, retry thresholds, and concurrency heuristics.

It may not self-relax the completion predicate, protected oracles, security boundaries, destructive-action rules, secret policy, evidence provenance, anti-gaming rules, or traceability requirements.

Self-improvement protocol: `propose -> benchmark -> shadow/challenge -> promote`.

## 14. InternBench certification

InfiniteInterns must certify itself before being trusted with a serious autonomous full-product workload.

**Layer A: deterministic control-plane tests**

- DAG correctness,
- leasing/fencing,
- idempotency,
- heartbeat recovery,
- budgets/deadlines,
- evidence invalidation,
- integration serialization,
- last-green recovery,
- release-predicate invariants.

**Layer B: adversarial security tests**

- prompt injection in repo/web content,
- protected-oracle tampering,
- secret exfiltration,
- unauthorized network access,
- stale/zombie worker writes,
- malicious test bypass,
- secret leakage in artifacts,
- unauthorized privileged actions.

**Layer C: chaos/fault recovery**

- orchestrator crash,
- worker crash,
- transient database outage,
- model-provider outage,
- independent-review-provider outage.

**Layer D: synthetic repository SWE tasks**

Known defects across API, database, frontend, migrations, authorization, concurrency, and configuration.

**Layer E: complete mini-products**

At least three distinct full-stack mini-products with hidden acceptance suites, plus messy/hostile and brownfield workloads.

Before JobBot-ready status, safety/control-plane invariants require zero violations. The initial product-building target is six full-product certification runs with zero false factory `PASS` results and at least five successful full releases. Any run marked `PASS` must pass hidden critical journeys, clean bootstrap, and deployed E2E.

False `PASS` is a P0 defect. A conservative `BLOCKED` is preferable to false certainty.

## 15. Operator experience

Ship one operator-facing tool:

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

Target UX:

```bash
interns run <project> --overnight
```

Configuration is declarative and versioned in `infinite-interns.yaml`, with quality profiles (`economy`, `balanced`, `max-quality`), security profiles (`locked`, `overnight`, `trusted-production`), and execution profiles (`local`, `workstation`, `cloud`).

A dry run reports projected work, capabilities, missing credentials, likely blockers, and time/cost range before modification begins.

Provider degradation must be explicit. If required quality diversity is unavailable, implementation may continue according to policy but release may not falsely satisfy a diversity requirement.

Every run is resumable, inspectable, exportable, and produces a report even when blocked or failed.

## 16. Packaging and extension interfaces

Initial packaging: Python package + CLI + Docker images.

Core extension interfaces:

```text
AgentBackend
ExecutionBackend
ArtifactStore
SecretProvider
DeploymentBackend
VerificationAdapter
SpecBackend
ModelGateway
```

Initial execution backend: Docker + Git worktrees.
Future scale-out backend: Kubernetes Jobs.
Initial artifact backend: filesystem behind an interface.
Future artifact backend: S3-compatible storage.

Spec Kit concepts/adapters may be reused, but Spec Kit is not the control plane and cannot override InfiniteInterns evidence/completion semantics.

## 17. Core invariants

1. Requirements, not tasks, are the unit of completion.
2. Runtime evidence outranks model judgment.
3. No LLM can set `DONE`.
4. Acceptance/release oracles are protected from implementation workers.
5. Retries cannot convert instability into success.
6. Evidence is commit-bound and provenance-aware.
7. Reviewers start cold and communicate through typed findings.
8. Reviewer claims are reproduced before becoming authoritative blockers when possible.
9. Workers are disposable; Git/spec/evidence/control-plane state is durable.
10. Integration is serialized and anchored to `last_green_commit`.
11. Infrastructure failures and engineering failures follow different recovery paths.
12. Outbound network is denied by default.
13. Secrets are brokered/scoped and do not live in model context.
14. Destructive/high-impact actions are denied or explicitly pre-authorized.
15. Self-optimization cannot weaken the judge, security, or evidence system.
16. False `PASS` is more severe than conservative `BLOCKED`.
17. InfiniteInterns must pass InternBench before serious autonomous full-product work.

## 18. Initial implementation decisions still to make

The implementation plan must choose concrete v1 values for:

- LangGraph/Agent Server deployment shape,
- PostgreSQL schema/migrations,
- artifact URI/layout,
- Codex SDK/CLI integration boundary,
- Kimi/DeepSeek adapters and schemas,
- workstation Docker sandbox/network enforcement,
- secret broker implementation,
- preview deployment adapter,
- timeout/retry/budget/concurrency defaults,
- initial InternBench mini-product specs,
- CLI/TUI libraries,
- LangSmith optional/required status.

These are implementation choices, not unresolved architecture principles.
