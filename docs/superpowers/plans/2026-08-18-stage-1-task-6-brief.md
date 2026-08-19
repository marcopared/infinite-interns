# Task 6 brief — deterministic evidence authority

Implement Stage 1 Task 6 from `2026-08-18-stage-1-deterministic-foundation.md`.

Required interfaces:

- `GateRequirement(gate_id, mandatory, requirement_id)`
- `ReleasePolicy(gates)`
- release evaluation status distinct from persisted `RunStatus`
- `ReleaseEvaluation(status, failing_gate_ids, stale_evidence_ids)`
- `ReleasePredicate.evaluate(policy, evidence, current_commit, environment_hash)`
- `EvidenceService.requirement_status(requirement_id, policy, evidence, current_commit, environment_hash)`

Hard rules:

- missing mandatory evidence is not PASS;
- mandatory FAIL is FAIL;
- mandatory BLOCKED or INFRA_ERROR is not PASS;
- mandatory UNSTABLE is not PASS;
- wrong commit/environment evidence is stale and cannot prove the current candidate;
- all mandatory current evidence must PASS for release evaluation PASS;
- a FAIL followed by a PASS for the same current gate cannot be washed into PASS merely by retrying;
- requirement `VERIFIED` derives from current mandatory gate evidence, never task state;
- this task returns evaluations only and does not persist `RunStatus.DONE`.
