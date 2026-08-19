# InfiniteInterns Agent Map

This file is a navigation map, not the full project specification.

## Canonical architecture

- `docs/architecture/README.md` — architecture index
- `docs/architecture/infinite-interns-design.md` — approved system design

## Core invariant

Agents may propose that work is complete. Only executable evidence may prove that it is complete.

No agent may directly mark a requirement verified, a release passed, or a run `DONE`.

## Current phase

Architecture is approved. The next phase is the concrete implementation plan and then test-driven implementation.

## Working rules

- Preserve deterministic authority over scheduling, verification, integration, security policy, and release.
- Treat Git, specifications, and evidence as durable state; agent conversation state is disposable.
- Keep reviewers in fresh contexts and communicate through typed artifacts.
- Protect acceptance/release oracles from implementation workers.
- Prefer small, explicit modules and mechanically enforced boundaries over giant prompts.
