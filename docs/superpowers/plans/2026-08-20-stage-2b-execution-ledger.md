# SDD ledger — plan: docs/superpowers/plans/2026-08-18-stage-2b-repository-bootstrap.md

Branch: `impl/stage-2b-repository-bootstrap`
Base: `main` @ `8af42d93ea71ffcea264fd66e3a3705ec5578641`

This controller has GitHub repository access but no durable local checkout/worktree. The feature branch is the isolation boundary and GitHub Actions is the executable verification environment.

## Pre-flight dependency/interface scan

| Producer | Consumer | Shared interface/file | Finding / ruling |
| --- | --- | --- | --- |
| Task 1 | Tasks 2-5 | `bootstrap.models` | `BaselineFailure` in Task 1 omits `base_commit` and `pre_existing`, but Task 4 explicitly requires both. **Ruling:** define them in Task 1 so provenance is structural, not added ad hoc later. |
| Task 1 | Task 3 | `BaselineSummary.guidance_refs` | Task 3 requires path, commit SHA, content SHA-256, and trust label. **Ruling:** define a typed `GuidanceRef` contract in Task 1 and have guidance discovery produce it. |
| Task 1 | Tasks 4-6 | `BaselineSummary` | Heavy command output must remain external. **Ruling:** summary stores only failure summaries/artifact URIs and compact hints/refs. |
| Task 2 | Tasks 4-5 | `RepositorySnapshot` | Service requires repo kind/base/default branch before command execution. Compatible. |
| Task 2 | Task 4 | dirty repository policy | Plan says dirty brownfield is rejected unless explicit snapshot policy exists, but no config field exists yet. **Ruling:** inspector accepts `allow_dirty=False`; Stage 2B settings later supply the explicit override. |
| Task 3 | Task 4 | detected commands + operator overrides | Existing `Settings` has no bootstrap section. **Ruling:** add strict `BootstrapSettings` with timeout, dirty policy, and tokenized command overrides; no shell strings. |
| Task 4 | Task 6 | baseline artifact | Existing `FilesystemArtifactStore` is immutable/traversal-safe and is reused for baseline logs/summary. Compatible. |
| Task 5 | Task 2 | greenfield Git initialization | Repository inspection and bootstrap service both touch initialization semantics. **Ruling:** inspector owns neutral Git initialization/snapshot; service owns the `.gitignore` control metadata baseline commit, with no product files. |
| Task 6 | DB/run state | `baseline_ref` | Plan requires a compact DB/state ref, but Stage 2 `runs` schema has no field. **Ruling:** add migration `0004_run_baseline_ref`, domain/repository support, and `FactoryState.baseline_ref`; PostgreSQL remains authoritative. |
| Task 6 | Stage 2 graph | parent graph ordering | Stage 2 graph currently routes directly to scheduler. **Ruling:** Stage 2B replaces the pre-spec path with bootstrap then `specification_pending`; scheduler service remains implemented but is not entered before Stage 3A planning. |
| Task 6 | initial `FactoryState` | commit fields | Current state requires `current_commit`/`last_green_commit`, which cannot be known before greenfield bootstrap. **Ruling:** make them nullable until bootstrap/integration establishes them; release/integration code must continue to require concrete SHAs at its own boundary. |

## Per-task self-consistency scan

| Task | Result |
| --- | --- |
| 1 | Models/tests consistent after provenance fields above are included. |
| 2 | Classification rules are deterministic; README/control-doc-only repositories remain greenfield. |
| 3 | Guidance may be read but never executed; command execution is restricted to explicit detector rules or configured argv. |
| 4 | Baseline failure execution must continue independent safe checks and capture bounded artifacts. |
| 5 | Greenfield path must not create `src/`, framework files, schemas, dependencies, requirements, or tasks. |
| 6 | Bootstrap must persist artifact + DB ref before specification can run; failure cannot route to `DONE`. |

## Progress

Stage 2B setup: COMPLETE.
Task 1: starting RED phase.
