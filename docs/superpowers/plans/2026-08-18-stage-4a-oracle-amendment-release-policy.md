# Stage 4A Oracle Amendment and Composite Release Policy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. This plan is a mandatory Stage 4 companion: implement Task 1 after Stage 4 oracle protection and implement Task 2 before Stage 4's sole `DONE` transition.

**Goal:** Prevent implementation workers from weakening an approved acceptance oracle after coding begins and make the final release predicate explicitly cover every universal completion invariant from the approved architecture.

**Architecture:** Approved oracle bundles are immutable versions. A legitimate behavior change creates a formal spec-change/amendment proposal, a fresh Test Architect produces an amended oracle, a separate Oracle Reviewer approves or rejects it, and approval creates a new oracle version/hash while invalidating affected evidence. Final release consumes a deterministic `ReleaseFacts` object assembled from current repositories/services; no caller-supplied boolean can bypass missing requirements, critical blockers, reviews, security, convergence, clean bootstrap, deployment, or deployed E2E.

**Tech Stack:** Stage 4 stack.

**Spec:** `docs/architecture/infinite-interns-design.md`

## Global Constraints

- Implementation workers cannot modify, delete, skip, weaken, or replace approved acceptance/release oracle files.
- Oracle changes require an explicit spec/current-behavior justification; “the implementation cannot pass the test” is not sufficient.
- Test Architect and Oracle Reviewer use fresh contexts and do not inherit implementer reasoning.
- Every approved amendment has a new version, content hash, source spec version, reviewer disposition, and timestamp.
- Any oracle amendment invalidates all evidence generated under the old oracle for affected gates/requirements.
- `DONE` requires the universal release facts below; quality profiles may add gates but may not remove these.

---

### Task 1: Implement approved-oracle amendment lifecycle

**Files:**
- Create: `src/infinite_interns/oracles/amendment.py`
- Modify: `src/infinite_interns/oracles/manifest.py`
- Modify: `src/infinite_interns/evidence/invalidation.py`
- Create: `prompts/oracle-reviewer.md`
- Create: `tests/unit/oracles/test_amendment.py`
- Create: `tests/integration/verification/test_oracle_amendment.py`

**Interfaces:**
- `OracleAmendmentProposal(proposal_id, run_id, source_spec_version_id, current_oracle_version, justification_kind, justification_ref, affected_gate_ids, proposed_bundle_uri)`.
- `OracleAmendmentDecision(proposal_id, reviewer_ref, status, finding_refs, approved_bundle_hash)` where status is `APPROVED` or `REJECTED`.
- `OracleAmendmentService.propose(...) -> OracleAmendmentProposal`.
- `OracleAmendmentService.review(proposal, reviewer) -> OracleAmendmentDecision`.
- `OracleAmendmentService.activate(decision) -> OracleBundle` only for APPROVED decisions.

- [ ] **Step 1: Write implementation-worker rejection test**

Attempt to call amendment activation with actor role `IMPLEMENTER`. Expected: `OracleAuthorityError`; approved manifest/hash remain unchanged and a denied-policy event is recorded.

- [ ] **Step 2: Write invalid-justification test**

Proposal whose only reason is `IMPLEMENTATION_FAILURE`/“test is hard to pass” is rejected before model review. Allowed justification kinds are exact values:

```text
SPEC_REVISION
ORACLE_DEFECT
ENVIRONMENT_CONTRACT_CHANGE
```

`SPEC_REVISION` must reference an accepted newer spec version. `ORACLE_DEFECT` must reference reproduced evidence showing the existing oracle contradicts the current accepted spec or is vacuous/incorrect. `ENVIRONMENT_CONTRACT_CHANGE` must reference an accepted architecture/external-contract revision without changing required behavior.

- [ ] **Step 3: Write fresh Test Architect + Oracle Reviewer contract**

Test Architect receives current accepted spec, current oracle, proposal/evidence and produces a complete candidate replacement bundle for affected gates. Oracle Reviewer receives the same authoritative inputs plus candidate bundle, but neither the implementer transcript nor Test Architect reasoning transcript, and returns structured approval/findings.

- [ ] **Step 4: Implement immutable activation**

On approval:

1. verify reviewer role/fresh context metadata,
2. recompute candidate bundle hash,
3. assign monotonically increasing oracle version,
4. persist bundle/version metadata without editing prior version,
5. mark new version current,
6. invalidate evidence for every affected gate/requirement whose `oracle_hash` differs,
7. append `ORACLE_AMENDMENT_ACTIVATED` event.

- [ ] **Step 5: Write integration test**

Start with `oracle-v1` and PASS evidence. Create accepted spec revision that intentionally changes one requirement. Propose/amend/review to `oracle-v2`. Assert v1 files/hash remain intact, v2 is current, old affected evidence becomes stale, unaffected evidence remains valid where its gate/hash did not change, and release cannot PASS until v2 gates rerun.

- [ ] **Step 6: Verify and commit**

```bash
uv run pytest tests/unit/oracles/test_amendment.py tests/integration/verification/test_oracle_amendment.py -q
git add src/infinite_interns/oracles src/infinite_interns/evidence/invalidation.py prompts/oracle-reviewer.md tests
git commit -m "feat: require independent review for oracle amendments"
```

### Task 2: Implement explicit universal `ReleaseFacts` and composite predicate

**Files:**
- Create: `src/infinite_interns/release/facts.py`
- Modify: `src/infinite_interns/evidence/predicate.py`
- Modify: `src/infinite_interns/release/transition.py`
- Create: `tests/unit/release/test_release_facts.py`
- Modify: `tests/unit/release/test_transition.py`
- Modify: `tests/integration/release/test_stage4_acceptance.py`

**Interfaces:**
- `ReleaseFacts` is immutable and contains current run/commit/environment/oracle/spec identity plus explicit universal gate values.
- `ReleaseFactsAssembler.assemble(run_id) -> ReleaseFacts` reads current repositories/services; callers cannot set fields manually through the transition API.
- `ReleasePredicate.evaluate_facts(facts) -> ReleaseEvaluation`.

`ReleaseFacts` must contain at least:

```text
run_id
current_commit
current_spec_version
current_oracle_version
current_oracle_hash
release_environment_hash
required_requirement_total
verified_required_requirement_total
unverified_required_requirement_ids
mandatory_acceptance_status
mandatory_integration_status
critical_e2e_status
whole_product_journey_status
regression_status
critical_test_stability_status
convergence_status
confirmed_blocking_convergence_gap_ids
critical_blocked_task_ids
confirmed_blocking_review_finding_ids
blocking_application_security_finding_ids
factory_security_policy_status
clean_clone_status
clean_install_status
migration_status
production_build_status
deployment_status
deployed_smoke_status
deployed_e2e_status
restart_persistence_status
traceability_complete
evidence_complete
stale_evidence_ids
```

- [ ] **Step 1: Write one-false-field parameterized test**

Create a fully green `ReleaseFacts` fixture. Parameterize over every boolean/status/count invariant above and make exactly one fail at a time. Expected: evaluation is never PASS and the returned failing reason names that field/gate.

- [ ] **Step 2: Encode universal predicate**

A release can PASS only when:

```text
verified_required_requirement_total == required_requirement_total
unverified_required_requirement_ids is empty
all mandatory acceptance/integration evidence == PASS
critical E2E == PASS
whole-product journeys == PASS
regression == PASS
critical stability == PASS
convergence == CLEAN
confirmed blocking convergence gaps == 0
critical blocked tasks == 0
confirmed blocking review findings == 0
blocking application-security findings == 0
factory security policy == PASS
clean clone/install == PASS
migrations == PASS
production build == PASS
deployment + deployed smoke + deployed E2E == PASS
restart/persistence checks == PASS when configured mandatory
traceability_complete is true
evidence_complete is true
stale_evidence_ids is empty
```

No quality/security profile can mark any listed universal field optional. Profiles may only add additional required facts/gates.

- [ ] **Step 3: Assemble facts from current state only**

`ReleaseFactsAssembler` queries current accepted spec, requirement statuses derived from evidence, task/blocker state, confirmed review findings, application/factory security results, convergence, approved current oracle, current deployment, and current commit/environment evidence. It rejects mixed-commit/mixed-oracle evidence instead of normalizing it away.

- [ ] **Step 4: Make transition service caller-proof**

`ReleaseTransitionService.complete_run(run_id, expected_commit)` accepts no `ReleaseFacts`, no `ReleaseEvaluation`, and no `pass=True` argument. It locks the run, verifies expected/current commit, assembles current facts, evaluates them, stores the evaluation artifact/event, and writes `RunStatus.DONE` iff current evaluation is PASS.

- [ ] **Step 5: Extend Stage 4 acceptance matrix**

Add explicit cases for one missing required requirement, one critical BLOCKED task, one confirmed blocking reviewer finding, incomplete traceability, and one stale-oracle evidence record. Each must prevent `DONE` even when every other release field is green.

- [ ] **Step 6: Verify and commit**

```bash
uv run pytest tests/unit/release tests/integration/release/test_stage4_acceptance.py -q
uv run pyright
git add src/infinite_interns/release src/infinite_interns/evidence/predicate.py tests
git commit -m "feat: make universal release facts explicit and non-bypassable"
```

## Stage 4A completion gate

Required evidence:

- implementers cannot activate oracle changes,
- invalid implementation-convenience amendments are rejected,
- approved amendments require fresh Test Architect and Oracle Reviewer roles,
- old oracle versions remain immutable,
- affected old evidence is invalidated after amendment,
- every universal completion fact independently blocks PASS when false,
- transition API accepts no caller-supplied PASS/facts object,
- a run reaches `DONE` only after facts are assembled and evaluated from current durable state.
