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

Architecture and implementation planning are approved/complete. Implementation begins at Stage 1 only after the operator selects the execution workflow.

## Working rules

- Follow the current stage plan task-by-task with test-first implementation and focused commits.
- Do not begin a later stage until the current stage acceptance gate is green on the integration branch.
- Preserve deterministic authority over scheduling, verification, integration, security policy, convergence, and release.
- Treat Git, specifications, evidence, and durable events as authoritative state; agent conversation state is disposable.
- Keep reviewers in fresh contexts and communicate through typed artifacts.
- Protect acceptance/release oracles from implementation workers; use the independent amendment flow for legitimate oracle changes.
- Prefer small, explicit modules and mechanically enforced boundaries over giant prompts.
- Any implementation discovery that would weaken an approved architecture invariant requires an explicit architecture amendment rather than an ad hoc workaround.
