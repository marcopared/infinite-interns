# Task 4 brief — PostgreSQL schema and repositories

Implement Stage 1 Task 4 from `2026-08-18-stage-1-deterministic-foundation.md`.

Required v1 schema: PostgreSQL schema `ii` with tables for runs, spec versions, requirements, tasks, task dependencies, attempts, evidence, review findings, events, deployments, and budgets.

Required repository surface:

- `RunRepository`
- `RequirementRepository`
- `TaskRepository`
- `EvidenceRepository`
- `EventRepository`

Repositories return Pydantic domain records rather than ORM objects. Evidence uniqueness must prevent duplicate identity for `(run_id, requirement_id, gate_id, commit_sha, environment_hash, verifier_version)`.

Use timezone-aware timestamps, JSONB metadata where appropriate, Alembic migrations, SQLAlchemy 2 async sessions with psycopg 3, and PostgreSQL 16.
