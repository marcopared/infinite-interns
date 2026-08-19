# InfiniteInterns Architecture

The canonical architecture is defined in [`infinite-interns-design.md`](infinite-interns-design.md).

The system is designed around one hard rule:

> Agents may propose that work is complete. Only executable evidence may prove that it is complete.

The architecture covers:

- specification and requirement traceability,
- protected acceptance oracles,
- Codex-first SWE workers,
- fresh independent review contexts,
- Kimi/DeepSeek adversarial review for high-risk work,
- deterministic verification and evidence provenance,
- isolated worktrees/containers,
- durable LangGraph/PostgreSQL orchestration,
- crash recovery, leases, fencing, and budgets,
- default-deny security and scoped secrets,
- clean-room deployment verification,
- whole-product convergence,
- InternBench certification of the factory itself.

Implementation must preserve the invariants in the design document. Any architectural change that weakens completion authority, protected tests, evidence provenance, or security boundaries requires an explicit design amendment rather than an implementation shortcut.
