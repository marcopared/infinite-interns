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

## Per-task result

| Task | Result |
| --- | --- |
| 1 — baseline contracts | COMPLETE — strict immutable models, command provenance, guidance refs, pre-existing failure attribution. |
| 2 — repository inspection | COMPLETE — deterministic brownfield/greenfield classification, Git snapshotting, dirty brownfield fail-closed by default. |
| 3 — guidance and commands | COMPLETE — bounded manifest/config detection; guidance is hashed and explicitly untrusted repository content. |
| 4 — brownfield baseline | COMPLETE — commands execute in a disposable detached worktree pinned to the recorded base commit; failures and output are external artifacts. |
| 5 — greenfield baseline | COMPLETE — only neutral Git/control metadata is created; no product architecture or dependencies are invented. |
| 6 — graph/runtime wiring | COMPLETE — baseline artifact + PostgreSQL reference are established before `specification_pending`; production Agent Server lifespan wires the real coordinator. |

## Reproduced findings repaired during Stage 2B

- dot-prefixed repository paths were initially normalized incorrectly; fixed with literal `./` prefix handling and regression coverage.
- pnpm commands could initially be inferred without evidence that pnpm was selected; fixed by requiring a lockfile or explicit package-manager declaration.
- baseline commands initially ran in the workload checkout and could mutate product source; fixed by executing from a detached worktree at the recorded commit.
- the production LangGraph runtime initially lacked the real bootstrap composition root; fixed in the FastAPI lifespan and covered by an integration test.
- an artifact-write / database-commit crash window initially caused retry collisions; fixed by recovering and validating the deterministic existing summary artifact.
- dirty working-tree guidance could initially be hashed while carrying the clean base-commit SHA; fixed by performing guidance discovery and command detection in the detached base-commit worktree.
- pre-bootstrap `FactoryState` initially represented unknown commit refs as empty strings; fixed by making `current_commit` and `last_green_commit` explicitly nullable until bootstrap establishes them.

## Verification

Fresh full gate on feature head `f340c692a83d1fb90159dd8b08cc78a28d3d9b12`, GitHub Actions run `393` (`32405502252`):

- locked dependency sync: PASS
- Ruff: PASS
- unit tests: `71 passed`
- Alembic migrations through `0004_run_baseline_ref`: PASS
- integration tests: `20 passed`
- chaos tests: `1 passed`
- Pyright: `0 errors, 0 warnings`
- workstation Compose validation: PASS
- `agent-server` and `executor` image builds: PASS
- live `langgraph dev` `/api/health` smoke: PASS

A documentation-only ledger finalization follows this verified head and must receive its own CI result before merge.

## Stage result

Stage 2B implementation is **functionally complete pending the final CI result on the ledger-finalization commit and PR integration**. No agent assertion alone constitutes completion; the final branch and post-merge states remain evidence-gated.

Stage 4 remains responsible for hardening the minimal bootstrap subprocess path into the approved sandbox/network/secret-isolation security boundary; Stage 2B does not claim that later release-grade boundary is already implemented.
