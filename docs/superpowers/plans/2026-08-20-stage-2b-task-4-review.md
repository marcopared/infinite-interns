# Stage 2B Task 4 Review

## Scope

Cold review of brownfield baseline execution and pre-existing failure provenance.

## Finding and reproduction

**Important — confirmed:** the first implementation executed baseline commands directly in the workload checkout. A build/test command could therefore mutate tracked product source during bootstrap, violating the Stage 2B invariant that bootstrap does not edit an existing brownfield application.

Regression test `test_brownfield_baseline_cannot_modify_workload_checkout` reproduced the defect in Actions run `32395867618`: a configured baseline command changed `src/app.py` from `VALUE = 1` to `MUTATED`.

## Repair

Brownfield commands now execute in a disposable detached Git worktree pinned to `BaselineSummary.base_commit`. The worktree is removed after the baseline completes, and persisted command output normalizes both source and temporary checkout paths.

## Verification

Actions run `32396027912` passed locked sync, Ruff, unit tests, Alembic migrations, integration tests including the isolation regression, chaos tests, strict Pyright, workstation Compose validation, control-plane image builds, and live LangGraph Agent Server smoke verification.

## Result

**PASS.** No remaining Critical or Important findings for Task 4.
