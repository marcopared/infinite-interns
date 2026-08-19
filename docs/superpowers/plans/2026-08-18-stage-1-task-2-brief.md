# Task 2 brief — domain IDs, statuses, immutable contracts

Implement Stage 1 Task 2 from `2026-08-18-stage-1-deterministic-foundation.md`.

Required interfaces:

- `RunId`, `RequirementId`, `TaskId`, `AttemptId`, `EvidenceId` string aliases.
- `RunStatus`, `RequirementStatus`, `TaskStatus`, `EvidenceResult`, `FailureClass`, `RiskClass`.
- Frozen/strict Pydantic `RunRecord`, `RequirementRecord`, `TaskRecord`, `EvidenceRecord`.
- `RequirementStatus` must contain only `UNVERIFIED`, `VERIFIED`, `FAILED`, `BLOCKED`, `UNSTABLE` and must not contain a product-level DONE state.
- `EvidenceRecord` must require `commit_sha` and `environment_hash` plus run/requirement/gate/result/producer/verifier/timestamp provenance.

Global constraints: requirements are the completion unit; no model authority is introduced; Stage 1 has no live LLM dependency.
