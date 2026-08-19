# InfiniteInterns

> Give the interns a spec. Go to sleep. Wake up to software that has to prove it works.

InfiniteInterns is an autonomous software-engineering factory designed to take a repository plus a product specification and drive the project through bootstrap, specification, implementation, testing, review, integration, convergence, clean-room deployment, and deployed end-to-end verification.

The defining rule is simple:

> Agents may propose that work is complete. Only executable evidence may prove that it is complete.

## Design and implementation plans

- Approved architecture: [`docs/architecture/infinite-interns-design.md`](docs/architecture/infinite-interns-design.md)
- Implementation roadmap: [`docs/superpowers/plans/2026-08-18-infinite-interns-implementation-roadmap.md`](docs/superpowers/plans/2026-08-18-infinite-interns-implementation-roadmap.md)
- Plan self-review and execution order: [`docs/superpowers/plans/2026-08-18-plan-self-review.md`](docs/superpowers/plans/2026-08-18-plan-self-review.md)

## Initial model strategy

- **Primary SWE:** Codex via OpenAI's Python Codex SDK
- **Fresh reviewer:** Codex in an independent thread/context
- **Primary adversarial reviewer:** Kimi K3
- **Secondary adversarial reviewer / diagnostician:** DeepSeek V4-Pro
- **Final authority:** deterministic verification and release evidence, never an LLM vote

## Target operator experience

```bash
interns run <project> --overnight
```

The factory is designed to continue working unattended, recover from crashes, isolate parallel workers, reject stale evidence, reproduce reviewer claims, and refuse to mark a product `DONE` until the release predicate passes against a clean deployed instance.

## Status

Architecture and implementation planning are complete. Implementation starts with the deterministic Stage 1 foundation, then proceeds through the acceptance-gated stage sequence documented in the roadmap.
