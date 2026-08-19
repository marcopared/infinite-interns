# Stage 1 final review

**Plan:** `2026-08-18-stage-1-deterministic-foundation.md`
**Branch:** `impl/stage-1-deterministic-foundation`

## Scope reviewed

- package/bootstrap/locked dependency setup;
- immutable domain contracts and run/requirement/task/evidence statuses;
- validated overnight configuration;
- PostgreSQL schema, Alembic migration, and repository boundaries;
- artifact URI/filesystem backend;
- deterministic release/requirement evidence evaluation;
- environment doctor and status CLI;
- Stage 1 persisted acceptance scenario;
- CI ordering and complete Stage 1 gate.

## Authority review

**PASS.**

- Persisted `RunStatus` has no intermediate `PASS` state.
- `RequirementStatus` has no `DONE` state.
- New requirements must enter persistence as `UNVERIFIED`.
- Requirement `VERIFIED` is derived by the evidence service, not task state.
- Release evaluation is pure and cannot mutate the database.
- A release policy with no mandatory gate is rejected instead of vacuously passing.
- Missing, failed, blocked, unstable, infrastructure-error, or stale mandatory evidence cannot satisfy release PASS.
- Current failure evidence cannot be washed away by merely adding a later current PASS for the same gate.
- No Stage 1 production code writes `RunStatus.DONE`.

## Evidence integrity review

**PASS.**

- Evidence records require commit SHA and environment hash.
- PostgreSQL enforces the planned evidence identity uniqueness constraint.
- Artifact URIs are traversal-safe and rooted under the configured store.
- Artifact IDs are immutable: repeat writes with identical bytes are idempotent; different bytes at the same URI are rejected.
- Raw artifact bodies remain outside PostgreSQL.

## Durability review

**PASS.**

- PostgreSQL schema `ii` contains the full Stage 1 control-plane table set.
- Repositories return domain records rather than ORM rows.
- Repository writes flush without taking transaction commit authority from callers.
- Alembic, not runtime metadata creation, owns schema migration.

## Operator review

**PASS.**

- `interns doctor` reports deterministic environment checks and exits nonzero when not ready.
- `interns status --run <id>` reads persisted run state through the repository boundary.
- Neither command can grant completion authority.

## Review findings fixed before completion

The final review found and fixed three Important issues before declaring Stage 1 ready:

1. vacuous release-policy PASS;
2. pre-verified requirement insertion;
3. mutable artifact identity.

Regression tests cover all three.

## Verification evidence

Hardened full Stage 1 run `32211472042` passed:

```text
uv sync --dev --locked
uv run ruff check .
uv run pytest tests/unit -q
uv run alembic upgrade head
uv run pytest tests/integration -q
uv run pyright
```

## Verdict

**READY TO MERGE.**

Critical findings: 0
Important findings: 0 unresolved
Known Stage 1 reproducibility debt: 0

Stage 2 must not begin until this Stage 1 branch lands on `main`.
