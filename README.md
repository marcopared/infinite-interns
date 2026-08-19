# InfiniteInterns

> **Enterprise software development, powered by an irresponsible amount of intern labor.**

InfiniteInterns is an autonomous software-engineering factory built on a simple management philosophy:

> If one AI coding intern can make mistakes, an unreasonable number of AI coding interns can make mistakes in parallel — and then review each other until the software actually works.

Give the interns a repository and a product specification. Go to sleep. InfiniteInterns handles bootstrap, specification, implementation, testing, review, integration, convergence, clean-room deployment, and deployed end-to-end verification while management is unavailable.

The interns write the software.

**The interns do not decide whether the software works.**

We have standards.

## Management philosophy

InfiniteInterns is deliberately built around disposable, isolated software-engineering workers with very limited institutional power.

A worker gets a task, a worktree, a sandbox, enough context to be dangerous, and an opportunity to demonstrate impact before the next performance review.

If the worker succeeds, its candidate moves through deterministic verification and independent review.

If the worker gets stuck, the system diagnoses the failure, escalates, or assigns the problem to a fresh worker with fewer emotional attachments to the previous implementation.

If every agent says the feature is finished but the acceptance tests fail, **the feature is not finished**.

This is management's one genuinely good policy.

## What happens while you sleep

```text
PRODUCT SPEC
    │
    ▼
SPECIFICATION + ARCHITECTURE
    │
    ▼
PROTECTED ACCEPTANCE ORACLES
    │
    ▼
TASK DAG
    │
    ├───────────────┬───────────────┐
    ▼               ▼               ▼
 WORKER A         WORKER B         WORKER C
 "I got this"    "easy ticket"    "quick change"
    │               │               │
    └───────────────┼───────────────┘
                    ▼
          DETERMINISTIC VERIFICATION
                    │
                    ▼
             INDEPENDENT REVIEW
                    │
              blockers found?
               ↙           ↘
             YES           NO
              │             │
           REPAIR           ▼
              │        INTEGRATION
              └──────↻      │
                             ▼
                        CONVERGENCE
                             │
                       gaps found?
                        ↙       ↘
                      YES       NO
                       │         │
                    MORE WORK    ▼
                              RELEASE
                                 │
                                 ▼
                         CLEAN DEPLOYMENT
                                 │
                                 ▼
                           DEPLOYED E2E
                                 │
                                 ▼
                       RELEASE PREDICATE
                           ↙          ↘
                         FAIL         PASS
                          │             │
                    back to work      DONE
```

In other words: the interns may submit the assignment, but the test suite grades it.

## The defining rule

> **Agents may propose that work is complete. Only executable evidence may prove that it is complete.**

No worker, reviewer, planner, or suspiciously confident model can set a requirement to `VERIFIED`, a release to `PASS`, or a run to `DONE` by opinion.

That authority belongs to deterministic evidence.

An intern saying _"looks good to me"_ is not evidence.

## The intern program

### Primary SWE

**Codex** does most of the implementation work.

It gets the repository, a scoped context packet, an isolated environment, and a coherent engineering task. Within that task it can investigate, edit, run the app, execute tests, debug failures, and produce a candidate commit.

This is the intern that somehow has production-level output despite technically still being in orientation.

### Fresh reviewer

A separate **Codex** context reviews the candidate cold.

The reviewer does not inherit the implementer's reasoning transcript, because interns are highly susceptible to confidently repeating what the previous intern told them in Slack.

### Competitive interns

For high-risk work, **Kimi K3** and **DeepSeek V4-Pro** can act as independent adversarial reviewers or diagnosticians.

They are not allowed to win arguments by majority vote. They produce concrete findings and reproduction strategies; executable evidence decides whether those findings are real.

Think of it as return-offer competition, except the winner is whichever claim survives contact with reality.

### Management

Deterministic infrastructure handles the things interns should never be trusted to negotiate among themselves:

- task state and dependency readiness
- worker leases and fencing
- budgets and deadlines
- protected acceptance tests
- evidence provenance
- integration against the last green commit
- security policy
- release eligibility
- the final `DONE` transition

Management contributes no code and still takes credit for the release.

## Why so many interns?

Because different failure modes benefit from different contexts.

- A fresh implementation worker avoids carrying hours of stale reasoning into the next task.
- A cold reviewer is less anchored to the implementation author's decisions.
- An independent model family can surface a different class of mistake.
- A failed approach can be replaced without losing authoritative project state.
- Parallel workers can handle dependency-independent tasks without sharing a mutable checkout.

The repository, specification, Git history, evidence, and control plane hold the institutional knowledge.

The interns are temporary.

Just like real life.

## Performance reviews are executable

InfiniteInterns does not treat code review as the final authority.

A change can look excellent, receive glowing feedback from multiple models, and still fail because Playwright clicked the button and the app exploded.

Evidence can include:

- build, typecheck, lint, and static checks
- unit and property tests
- integration/API/database tests
- protected acceptance tests
- browser journeys with Playwright
- persistence and restart checks
- security verification
- clean-room bootstrap
- production build
- preview/staging deployment
- end-to-end tests against the deployed application

If a higher-authority runtime check fails, lower-authority approval does not matter.

The intern has been placed on a performance improvement plan.

## Parallelism without a group-project disaster

Workers never share a mutable checkout.

Each task runs in an isolated Git worktree and execution environment. Candidates are integrated one at a time against the current `last_green_commit` and regression-tested before becoming the new green baseline.

This is because three interns editing the same branch simultaneously is not "multi-agent collaboration." It is an incident.

## Crash recovery

Workers are disposable. Project state is not.

InfiniteInterns is designed so that an orchestrator can crash, a worker can disappear, or a provider can temporarily fail without turning five hours of work into institutional amnesia.

Durable state lives in PostgreSQL, Git, specifications, and evidence artifacts. Worker leases expire, stale workers lose authority, and replacement workers reconstruct their task from durable state.

If an intern disappears for 90 seconds, management does not assume they are "heads-down."

## Security

The interns do not get the keys to the building.

Workers operate inside restricted sandboxes with scoped filesystem access, default-deny networking, scoped credentials, and capability-based access to external actions.

They do **not** receive unrestricted production credentials, the host Docker socket, cluster-admin access, or permission to make destructive external decisions because a README told them to.

Open-web research is treated as untrusted input. High-impact operations belong to separate policy-controlled services.

Despite what their LinkedIn headline says, they started Tuesday.

## Operator experience

The target experience is intentionally boring:

```bash
interns run <project> --overnight
```

Then:

```bash
interns status
interns watch
interns inspect
interns report
```

The human-facing output can have personality. The underlying technical states remain precise.

For example:

```text
InfiniteInterns

Run: jobbot-2026-08-18
Status: RUNNING

Workers:       4 active
Tasks:         23 / 31 complete
Requirements:  64 / 84 verified

Current situation:
Four interns are independently convinced they are correct.
The test suite disagrees with two of them.

Last green commit: 9af2c11
Release status: NOT READY
```

## Architecture

InfiniteInterns is designed as a durable control plane around disposable software-engineering workers:

- **LangGraph** for stateful orchestration and recovery
- **PostgreSQL** for durable control-plane state
- **Git worktrees + isolated execution** for concurrent workers
- **Codex** as the primary SWE backend
- **Kimi K3 / DeepSeek V4-Pro** as optional independent adversaries
- **Playwright** for browser/runtime verification
- **protected acceptance oracles** for implementation-independent judgment
- **deterministic integration, convergence, security, and release gates**
- **InternBench** for certifying the factory itself before trusting it with serious autonomous builds

The system is intentionally designed so that adding more intelligence never requires giving an agent more authority over the definition of success.

## Design and implementation plans

The joke stops at the architecture boundary. The engineering documents use precise technical terminology.

- Approved architecture: [`docs/architecture/infinite-interns-design.md`](docs/architecture/infinite-interns-design.md)
- Implementation roadmap: [`docs/superpowers/plans/2026-08-18-infinite-interns-implementation-roadmap.md`](docs/superpowers/plans/2026-08-18-infinite-interns-implementation-roadmap.md)
- Plan self-review and execution order: [`docs/superpowers/plans/2026-08-18-plan-self-review.md`](docs/superpowers/plans/2026-08-18-plan-self-review.md)
- Stage 1 plan: [`docs/superpowers/plans/2026-08-18-stage-1-deterministic-foundation.md`](docs/superpowers/plans/2026-08-18-stage-1-deterministic-foundation.md)

## Development status

Stage 1 — the deterministic foundation — is implemented on its feature branch and is undergoing final merge review. It includes the Python package, validated configuration, PostgreSQL control-plane schema, artifact store, evidence authority, environment doctor, status CLI, and Stage 1 acceptance tests.

Stage 2 adds durable orchestration, leases/fencing, isolated Docker/worktree execution, serialized integration, and crash recovery.

To verify the current Stage 1 branch locally:

```bash
uv sync --dev --locked
docker compose -f docker-compose.dev.yml up -d postgres
export INFINITE_INTERNS_DATABASE_URL='postgresql+psycopg://interns:interns@127.0.0.1:54329/infinite_interns'
uv run alembic upgrade head
uv run ruff check .
uv run pytest tests/unit -q
uv run pytest tests/integration -q
uv run pyright
uv run interns doctor
```

The interns now have laptops. Management has already scheduled their performance reviews.
