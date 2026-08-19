# InfiniteInterns

> Give the interns a spec. Go to sleep. Wake up to software that has to prove it works.

InfiniteInterns is an autonomous software-engineering factory designed to take a repository plus a product specification and drive the project through specification, implementation, testing, review, integration, convergence, clean-room deployment, and deployed end-to-end verification.

The defining rule is simple:

> Agents may propose that work is complete. Only executable evidence may prove that it is complete.

The project is currently in the architecture-to-implementation transition. The approved design is stored under [`docs/architecture/`](docs/architecture/README.md).

## Initial model strategy

- **Primary SWE:** Codex
- **Fresh reviewer:** Codex in an independent context
- **Primary adversarial reviewer:** Kimi K3
- **Secondary adversarial reviewer / diagnostician:** latest supported DeepSeek model
- **Final authority:** deterministic verification and release evidence, never an LLM vote

## Target operator experience

```bash
interns run <project> --overnight
```

The factory should continue working unattended, recover from crashes, isolate parallel workers, reject stale evidence, reproduce reviewer claims, and refuse to mark a product `DONE` until the release predicate passes against a clean deployed instance.

## Status

Architecture approved. Implementation planning is next.
