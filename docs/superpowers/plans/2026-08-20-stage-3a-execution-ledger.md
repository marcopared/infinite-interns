# SDD ledger — plan: docs/superpowers/plans/2026-08-18-stage-3a-specification-planning.md

Branch: `impl/stage-3a-specification-planning`
Base: `main` @ `db0ed753dcc5824bebf58d791745376a93e85169`

GitHub Actions is the executable verification environment; this controller has repository write access but no durable local checkout.

## Pre-flight dependency/interface scan

| Producer | Consumer | Shared interface | Finding / ruling |
| --- | --- | --- | --- |
| Stage 2B | Task 2 | Alembic revision chain | Plan names `0003_specification_lineage`, but `0003_integration_state` and `0004_run_baseline_ref` already exist. **Ruling:** Stage 3A lineage migration is `0005_specification_lineage`, down-revision `0004_run_baseline_ref`. |
| Stage 1 evidence | Task 2 | `ii.requirements` identity | Existing evidence FK targets `(run_id, requirement_id)`, so duplicating stable requirement IDs per spec version would break identity/uniqueness. **Ruling:** `ii.requirements` remains the append-only stable requirement identity catalog; `spec_version_id` records the introducing version. Non-semantic revisions reuse the same requirement identity; semantic replacement creates a new ID with `supersedes_requirement_id`. Immutable per-version membership/content lives in the `ProductSpec` artifact. |
| Stage 1 DB | Task 2 | `ii.spec_versions` | Existing schema is `(run_id, version:int, artifact_ref, created_at)`, while Stage 3A requires immutable `version_id`, parent/product-input lineage, content hash, review status. **Ruling:** migrate the legacy table compatibly rather than creating a second authoritative spec-version store. |
| Stage 2 scheduler | Task 7 | `TaskDag` | Existing `TaskDag.from_edges()` does not represent isolated zero-edge nodes. **Ruling:** Stage 3A `TaskPlan` must preserve all task IDs and construct/persist dependency-safe tasks without losing independent singletons; adapt the scheduler DAG contract if needed with regression coverage. |
| Task 7 | Task 8 / scheduler | task lifecycle | Planning must persist tasks without making them executable. **Ruling:** planned tasks remain `PLANNED`; only the deterministic readiness gate may materialize `READY` after accepted spec/oracle/architecture/traceability/audit evidence. |
| Stage 2B graph | Task 8 | graph boundary | Current parent graph intentionally ends at `specification_pending`. **Ruling:** Stage 3A owns the planning subgraph/service and may advance to scheduling eligibility only after the deterministic readiness predicate; no planning agent may set verification/completion state. |
| Stage 2B baseline | Tasks 3-8 | baseline provenance | Planning consumes only persisted baseline references/typed `BaselineSummary`; raw baseline command logs remain external artifacts. |

## Execution order

1. typed specification, assumption, and traceability contracts
2. immutable spec version persistence and requirement lineage
3. Spec Compiler + structured planning-agent interface
4. independent critics + synthesizer revision loop
5. Test Architect + acceptance-oracle draft
6. Architect + requirement-linked architecture
7. task planner + dependency DAG persistence
8. cross-artifact audit + deterministic planning-readiness gate

## Progress

Stage 3A setup: COMPLETE.
Task 1: starting RED phase.
