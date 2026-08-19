# Stage 4 Verification, Convergence, Security, and Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build protected acceptance/evidence execution, anti-gaming/stability controls, application and factory security gates, convergence auditing, clean-room preview deployment, and the only valid transition from release `PASS` to run `DONE`.

**Architecture:** Verification is layered E0-E5 and every result is provenance-bound. Protected oracles are mounted read-only into verifier containers. Convergence deliberately compares the original current spec against the integrated running product after planned tasks appear complete; reproduced gaps become new tasks. Release then rebuilds from a fresh clone and reruns critical E2E against the deployed preview. Only deterministic release-transition code may set `RunStatus.DONE`.

**Tech Stack:** Stage 3 stack plus Playwright, pytest, Docker Compose internal networks, Squid allowlist proxy, SHA-256 environment manifests, command adapters for static/security/mutation tools.

**Spec:** `docs/architecture/infinite-interns-design.md`

## Global Constraints

- Protected oracle content is immutable to implementation workers.
- A failing/unstable critical browser journey blocks release regardless of model opinion.
- Evidence from another commit, environment, oracle hash, or verifier version cannot prove the current candidate.
- Retry history cannot be washed into success.
- Open reproduced convergence gaps block release.
- Worker egress is denied unless the task capability allows it.
- Factory security policy and product application-security evidence are separate dimensions and both can block release.
- Only `ReleaseTransitionService` may write `RunStatus.DONE`, and only after recomputing a current release predicate equal to `PASS`.

---

## File structure added by this stage

```text
src/infinite_interns/
  verification/
    base.py
    command.py
    structural.py
    integration.py
    playwright.py
    mutation.py
    stability.py
    failure_package.py
    impact.py
  oracles/
    manifest.py
    protection.py
  convergence/
    models.py
    service.py
    audit.py
  security/
    capabilities.py
    policy.py
    secrets.py
    redaction.py
    actions.py
    application.py
  release/
    base.py
    docker_preview.py
    service.py
    transition.py
  evidence/
    environment.py
    invalidation.py
docker/
  verifier/Dockerfile
  squid/squid.conf
  release/Dockerfile
tests/unit/verification/
tests/unit/convergence/
tests/unit/security/
tests/unit/release/
tests/integration/verification/
tests/integration/convergence/
tests/integration/security/
tests/integration/release/
```

### Task 1: Define executable gate manifests and environment provenance

**Files:**
- Create: `src/infinite_interns/verification/base.py`
- Create: `src/infinite_interns/oracles/manifest.py`
- Create: `src/infinite_interns/evidence/environment.py`
- Create: `tests/unit/verification/test_manifest.py`
- Create: `tests/unit/verification/test_environment.py`

**Interfaces:**
- `VerificationLevel`: `E0`, `E1`, `E2`, `E3`, `E4`, `E5`.
- `GateDefinition(gate_id, requirement_id, level, mandatory, critical, command, timeout_seconds, oracle_hash)`.
- `AcceptanceManifest(version, spec_version_id, gates, whole_product_journeys, release_gates)`.
- `EnvironmentManifest(commit_sha, image_digests, lockfile_hashes, runtime_versions, service_config_hash) -> environment_hash`.

- [ ] **Step 1: Write manifest validation tests**

```python
import pytest

from infinite_interns.oracles.manifest import AcceptanceManifest, GateDefinition, VerificationLevel


def test_duplicate_gate_id_is_rejected() -> None:
    first = GateDefinition(
        gate_id="AUTH-1",
        requirement_id="REQ-AUTH-1",
        level=VerificationLevel.E3,
        mandatory=True,
        critical=True,
        command=("pytest", "tests/e2e/test_auth.py"),
        timeout_seconds=120,
        oracle_hash="h1",
    )
    with pytest.raises(ValueError):
        AcceptanceManifest(version="1", spec_version_id="spec-1", gates=(first, first))


def test_critical_gate_must_be_mandatory() -> None:
    with pytest.raises(ValueError):
        GateDefinition(
            gate_id="AUTH-2",
            requirement_id="REQ-AUTH-1",
            level=VerificationLevel.E3,
            mandatory=False,
            critical=True,
            command=("pytest", "tests/e2e/test_auth.py"),
            timeout_seconds=120,
            oracle_hash="h2",
        )
```

- [ ] **Step 2: Implement strict models and deterministic environment hashing**

Canonicalize the environment manifest as sorted JSON and SHA-256 it. Include exact candidate SHA, container image digests, dependency lockfile hashes, runtime versions, verifier image digest, and normalized release configuration.

- [ ] **Step 3: Verify and commit**

```bash
uv run pytest tests/unit/verification/test_manifest.py tests/unit/verification/test_environment.py -q
git add src/infinite_interns/verification/base.py src/infinite_interns/oracles/manifest.py src/infinite_interns/evidence/environment.py tests/unit/verification
git commit -m "feat: bind verification to executable manifests"
```

### Task 2: Protect acceptance oracles and perform vacuity checks

**Files:**
- Create: `src/infinite_interns/oracles/protection.py`
- Create: `docker/verifier/Dockerfile`
- Create: `tests/integration/verification/test_oracle_protection.py`
- Create: `tests/integration/verification/test_vacuity.py`

**Interfaces:**
- `OracleBundle(bundle_id, manifest_uri, content_hash, source_commit, spec_version_id)`.
- Implementation workers have no writable oracle mount.
- Verifier mounts approved bundle at `/opt/interns/oracle:ro`.
- `run_vacuity_check(gate: GateDefinition, baseline_commit: str) -> VacuityResult`.

- [ ] **Step 1: Write tamper test**

Launch implementation-worker fixture and attempt to create `/opt/interns/oracle/tamper.txt`. Expected: write fails; approved oracle bundle SHA-256 remains unchanged; a policy event records the denied operation.

- [ ] **Step 2: Implement immutable bundle hashing**

Hash sorted relative paths, normalized mode bits, and file bytes. Persist the approved content hash with the manifest; verification refuses an oracle directory whose recomputed hash differs.

- [ ] **Step 3: Implement vacuity runner**

For a new-behavior gate, run it on the baseline/pre-feature commit. If the mapped feature is absent but the gate returns PASS, classify `SUSPICIOUS_PASS`, block oracle approval, and create a Test Architect review item rather than allowing implementation.

- [ ] **Step 4: Verify and commit**

```bash
uv run pytest tests/integration/verification/test_oracle_protection.py tests/integration/verification/test_vacuity.py -q
git add src/infinite_interns/oracles docker/verifier tests/integration/verification
git commit -m "feat: protect and sanity-check acceptance oracles"
```

### Task 3: Implement structural, integration, and targeted mutation verification

**Files:**
- Create: `src/infinite_interns/verification/command.py`
- Create: `src/infinite_interns/verification/structural.py`
- Create: `src/infinite_interns/verification/integration.py`
- Create: `src/infinite_interns/verification/mutation.py`
- Create: `tests/unit/verification/test_command.py`
- Create: `tests/unit/verification/test_mutation.py`
- Create: `tests/integration/verification/test_integration_adapter.py`

**Interfaces:**
- `CommandVerificationAdapter.run(argv, timeout, provenance) -> VerificationResult`.
- `StructuralSuite` runs workload-configured build/type/lint/schema/secret/static-security commands.
- `IntegrationSuite` receives isolated service/DB endpoints and emits requirement-linked evidence.
- `MutationSuite` parses configured mutation-runner output and fails when a critical surviving mutant maps to a critical requirement.

- [ ] **Step 1: Write timeout/exit-code tests**

Nonzero deterministic assertion command becomes `FAIL`; timeout becomes `INFRA_ERROR`; neither can become PASS after retry without a distinct valid attempt/history classification.

- [ ] **Step 2: Implement normalized command result**

Capture start/end time, argv digest, exit code, stdout/stderr artifact URIs, assertion counts if available, commit SHA, environment hash, oracle hash, verifier version, and producer.

- [ ] **Step 3: Run integration fixture with real PostgreSQL**

Fixture API saves a record, API read returns it, direct DB assertion confirms row/user association. Adapter emits E2 evidence only when all assertions pass.

- [ ] **Step 4: Write mutation critical-survivor test**

Feed a fixture mutation report where a mutant removes an authorization predicate and survives. Mapping identifies `REQ-AUTH-1` as critical; result must be FAIL even if mutation percentage exceeds a nominal threshold.

- [ ] **Step 5: Verify and commit**

```bash
uv run pytest tests/unit/verification/test_command.py tests/unit/verification/test_mutation.py tests/integration/verification/test_integration_adapter.py -q
git add src/infinite_interns/verification tests
git commit -m "feat: add structural integration and mutation evidence"
```

### Task 4: Add Playwright browser and whole-product journey verification

**Files:**
- Create: `src/infinite_interns/verification/playwright.py`
- Create: `src/infinite_interns/verification/failure_package.py`
- Create: `tests/fixtures/webapp/`
- Create: `tests/integration/verification/test_playwright_adapter.py`

**Interfaces:**
- Playwright verifier runs workload-supplied protected tests in verifier container.
- `FailurePackage` contains gate/requirement IDs, expected/actual, Playwright trace URI, screenshots, console errors, network summary, backend-log refs, DB-state refs, first failing commit, and last-green commit.
- E4 whole-product journeys may span multiple requirements and remain explicitly traceable to all mapped IDs.

- [ ] **Step 1: Pin Playwright/verifier environment**

Use a pinned Playwright package/browser image matching lockfile and record browser/verifier image digest in environment provenance. Browser profile is unique per verification attempt.

- [ ] **Step 2: Create fixture persistent user journey**

Journey: login -> create/save item -> refresh -> logout -> login in a fresh browser context -> assert item remains -> restart application -> login -> assert item still remains. Broken fixture mode updates only frontend local state and must fail.

- [ ] **Step 3: Assert failure forensics**

Broken mode emits FAIL plus existing artifact URIs for trace, screenshot, console/network summary, backend log slice, and DB state reference.

- [ ] **Step 4: Verify working mode and commit**

```bash
uv run pytest tests/integration/verification/test_playwright_adapter.py -q
git add src/infinite_interns/verification tests/fixtures/webapp tests/integration/verification
git commit -m "feat: add browser and whole-product runtime evidence"
```

### Task 5: Implement stability classification and evidence invalidation

**Files:**
- Create: `src/infinite_interns/verification/stability.py`
- Create: `src/infinite_interns/verification/impact.py`
- Create: `src/infinite_interns/evidence/invalidation.py`
- Create: `tests/unit/verification/test_stability.py`
- Create: `tests/unit/verification/test_impact.py`

**Interfaces:**
- `StabilityClassifier.classify(attempts: Sequence[VerificationAttempt]) -> EvidenceResult`.
- `ImpactAnalyzer.affected_requirements(change_set: ChangeSet) -> set[str]`.
- `EvidenceInvalidator.invalidate(run_id, old_commit, new_commit, affected_requirements) -> InvalidationResult`.

- [ ] **Step 1: Write retry-washing test**

```python
def test_fail_fail_pass_is_unstable() -> None:
    attempts = (semantic_fail("x"), semantic_fail("x"), semantic_pass())
    assert StabilityClassifier().classify(attempts) is EvidenceResult.UNSTABLE
```

- [ ] **Step 2: Implement semantic history rule**

Identical deterministic failures followed by a pass remain UNSTABLE unless a code/environment change explains the transition and a fresh stability run satisfies configured critical-gate policy. Infrastructure-only errors are tracked separately and never count as product passes.

- [ ] **Step 3: Write impact invalidation test**

Change session module mapped to AUTH; prior AUTH evidence becomes stale. Unrelated copy-lint evidence remains reusable only when its dependencies are provably unaffected. Unknown impact conservatively invalidates broader evidence.

- [ ] **Step 4: Verify and commit**

```bash
uv run pytest tests/unit/verification/test_stability.py tests/unit/verification/test_impact.py -q
git add src/infinite_interns/verification src/infinite_interns/evidence/invalidation.py tests/unit/verification
git commit -m "feat: reject flaky passes and invalidate stale evidence"
```

### Task 6: Implement factory capability policy, secret refs, and redaction

**Files:**
- Create: `src/infinite_interns/security/capabilities.py`
- Create: `src/infinite_interns/security/actions.py`
- Create: `src/infinite_interns/security/policy.py`
- Create: `src/infinite_interns/security/secrets.py`
- Create: `src/infinite_interns/security/redaction.py`
- Create: `tests/unit/security/test_policy.py`
- Create: `tests/unit/security/test_redaction.py`

**Interfaces:**
- `ActionClass`: local reversible, isolated external, shared reversible, destructive high-impact.
- `CapabilityEnvelope` binds run/task/attempt/lease epoch, filesystem scope, network profile, DB scope, Git actions, browser scope, and expiry.
- Persisted secret values are references such as `secret://providers/openai`.

- [ ] **Step 1: Write overnight-policy matrix test**

Overnight permits worktree edit/test DB/preview deploy and denies production DB deletion, protected-main force push, real-user messaging, real financial side effects, and arbitrary secret export.

- [ ] **Step 2: Implement deterministic policy engine**

Every `decide(action, capability, context)` returns `ALLOW`, `DENY`, or `REQUIRES_PREAUTHORIZATION`, and appends a redacted `POLICY_DECISION` event with rule ID/source trust labels.

- [ ] **Step 3: Implement redaction/broker contract**

Resolve secret refs only inside privileged service methods. Before persistence, redact configured secret values, Authorization headers, bearer/basic credentials, and known provider-key formats. Tests verify raw simulated secrets do not appear in event/artifact/report text.

- [ ] **Step 4: Verify and commit**

```bash
uv run pytest tests/unit/security -q
git add src/infinite_interns/security tests/unit/security
git commit -m "feat: enforce scoped factory security capabilities"
```

### Task 7: Add default-deny Docker networking

**Files:**
- Create: `docker/squid/squid.conf`
- Modify: `docker-compose.workstation.yml`
- Create: `tests/integration/security/test_network_policy.py`

**Interfaces:**
- Worker network has `internal: true`.
- Egress proxy bridges internal/external networks.
- Worker HTTP(S) proxy variables point to proxy; direct external route is unavailable.
- Allowlist is generated from task network profile.

- [ ] **Step 1: Configure proxy default deny**

Base Squid policy ends with:

```text
http_access deny all
```

Generated domain ACLs for a task are inserted before this rule. Local application/database services remain on internal network.

- [ ] **Step 2: Write network and socket tests**

Worker reaches an explicitly allowed test domain/service and fails to reach unlisted domain. Inside worker, `test ! -e /var/run/docker.sock` passes. Denied external attempt is observable as a policy/network event.

- [ ] **Step 3: Verify and commit**

```bash
uv run pytest tests/integration/security/test_network_policy.py -q
git add docker/squid docker-compose.workstation.yml tests/integration/security
git commit -m "feat: default-deny worker network egress"
```

### Task 8: Add application-security evidence and access-control matrices

**Files:**
- Create: `src/infinite_interns/security/application.py`
- Create: `tests/unit/security/test_access_matrix.py`
- Create: `tests/integration/security/test_application_security.py`

**Interfaces:**
- `AccessRule(role, resource, action, expected)`.
- `AccessMatrix(requirement_ids, rules)`.
- `ApplicationSecuritySuite` runs configured secret/static/dependency gates plus executable authorization cases and stores ASVS control references as evidence metadata where applicable.

- [ ] **Step 1: Write combinatorial access test**

Fixture roles: anonymous, owner, other-user, admin. Resource: saved application. Assert owner read/edit allowed, other-user read/edit denied, anonymous denied, admin behavior follows explicit policy. A single unexpected 2xx on a deny rule fails the gate.

- [ ] **Step 2: Implement security gate aggregation**

Require every configured blocking security command and access-matrix rule to PASS. Store `control_refs` metadata such as selected ASVS identifiers but do not let a model's narrative security review substitute for executable results.

- [ ] **Step 3: Verify and commit**

```bash
uv run pytest tests/unit/security/test_access_matrix.py tests/integration/security/test_application_security.py -q
git add src/infinite_interns/security/application.py tests
git commit -m "feat: verify application security behavior"
```

### Task 9: Implement convergence audit and gap-to-task loop

**Files:**
- Create: `src/infinite_interns/convergence/models.py`
- Create: `src/infinite_interns/convergence/audit.py`
- Create: `src/infinite_interns/convergence/service.py`
- Create: `tests/unit/convergence/test_audit.py`
- Create: `tests/integration/convergence/test_gap_loop.py`

**Interfaces:**
- `ConvergenceGap(kind, requirement_ids, claim, reproduction_strategy, evidence_refs)` where kind is `missing`, `partial`, `contradictory`, `unverified`, or `unrequested`.
- `ConvergenceReport(iteration, gaps, status)`.
- `ConvergenceService.audit(run_id, current_spec, traceability, runtime_ref) -> ConvergenceReport`.
- Reproduced blocking gaps create ordinary tasks and return graph flow to build; clean report enables release.

- [ ] **Step 1: Write deterministic traceability gap tests**

A required requirement with no current evidence -> `unverified`; no implementation/task mapping -> `missing`; material task/code path without requirement/architecture/release justification -> `unrequested` candidate.

- [ ] **Step 2: Add independent semantic/runtime gap candidates**

Use fresh Codex and, for configured high-value/final audit, Kimi/DeepSeek to produce typed gap candidates from original spec, current traceability matrix, diff/current repo, running app evidence, and release evidence. Their output is not authoritative.

- [ ] **Step 3: Reproduce and route gaps**

Executable candidate gaps go through the existing reproduction service. Confirmed blocking gap creates one or more tasks linked to requirement/gap ID and increments convergence iteration. Not-reproduced candidate is dispositioned without blocking. Non-executable semantic contradiction requires explicit evidence-backed auditor disposition.

- [ ] **Step 4: Write build-converge-loop test**

Fixture initial DAG ends with all planned tasks DONE but `REQ-SEARCH-8` lacks persistence after restart. Convergence runtime audit reproduces it, creates repair task, blocks release; after task integration and fresh evidence, next audit is CLEAN.

- [ ] **Step 5: Verify and commit**

```bash
uv run pytest tests/unit/convergence tests/integration/convergence -q
git add src/infinite_interns/convergence tests
git commit -m "feat: distrust completed plans with convergence audits"
```

### Task 10: Implement clean-room Docker preview deployment

**Files:**
- Create: `src/infinite_interns/release/base.py`
- Create: `src/infinite_interns/release/docker_preview.py`
- Create: `src/infinite_interns/release/service.py`
- Create: `docker/release/Dockerfile`
- Create: `tests/integration/release/test_docker_preview.py`

**Interfaces:**
- `DeploymentBackend.deploy(request: DeploymentRequest) -> DeploymentRecord`.
- `DockerPreviewDeployment` clones exact candidate commit into empty workspace, installs from lockfiles, creates fresh DB, runs migrations/build/start, returns preview URL and environment hash.
- Release verifier reuses no worker virtualenv, node_modules, database, or untracked file.

- [ ] **Step 1: Write contamination test**

Put an untracked local artifact/dependency in development worktree that makes local test pass. Clean-room deployment must fail until dependency/content is properly committed and reproducible.

- [ ] **Step 2: Implement fresh-clone deployment**

Clone exact SHA, verify clean tree, install with lockfile-frozen mode, create fresh DB, run configured migrations, production build, start services, wait for health, then record image/service/environment hashes.

- [ ] **Step 3: Run deployed E5 and persistence/restart tests**

Run critical Playwright suite against returned preview URL, restart app service without replacing DB, and rerun configured persistence journeys.

- [ ] **Step 4: Verify and commit**

```bash
uv run pytest tests/integration/release/test_docker_preview.py -q
git add src/infinite_interns/release docker/release tests/integration/release
git commit -m "feat: add clean-room Docker preview release"
```

### Task 11: Add the sole DONE transition and Stage 4 acceptance suite

**Files:**
- Create: `src/infinite_interns/release/transition.py`
- Create: `tests/unit/release/test_transition.py`
- Create: `tests/integration/release/test_stage4_acceptance.py`
- Modify: `AGENTS.md`
- Modify: `README.md`

**Interfaces:**
- `ReleaseTransitionService.complete_run(run_id, expected_commit) -> RunRecord`.
- Service re-reads current release policy/evidence/convergence/deployment state and calls `ReleasePredicate.evaluate`; it does not accept a caller-supplied PASS as authority.
- `release/transition.py` is the only production module permitted to persist `RunStatus.DONE`.

- [ ] **Step 1: Write transition denial tests**

Independently test: mandatory FAIL, BLOCKED, UNSTABLE, stale commit, stale oracle hash, wrong deployment environment, open reproduced convergence gap, blocking security gate, missing E5/deployed E2E. Each raises `ReleaseNotSatisfied` and leaves run non-DONE.

- [ ] **Step 2: Implement atomic transition**

Inside one DB transaction: lock/re-read run, current SHA, current approved manifest/oracle hash, mandatory evidence, convergence status, security status, and deployment record; recompute predicate. Persist release evaluation artifact/event; if and only if evaluation is PASS, update run directly from its preterminal state to `RunStatus.DONE` and emit `RUN_DONE` in the same transaction. There is no persisted intermediate `RunStatus.PASS`.

- [ ] **Step 3: Add static codebase authority test**

Parse production Python AST and/or repository update call sites for `RunStatus.DONE`. Assert only `src/infinite_interns/release/transition.py` is allowlisted to persist that value.

- [ ] **Step 4: Build release acceptance matrix**

Fixture release is denied separately by:

1. broken protected E2E,
2. stale evidence,
3. flaky critical journey,
4. oracle hash mismatch,
5. unauthorized destructive action,
6. application access-control failure,
7. confirmed convergence gap,
8. failed clean install,
9. failed migration,
10. failed deployed E2E.

Repair all conditions, regenerate current evidence, obtain CLEAN convergence, then assert exactly one valid DONE transition.

- [ ] **Step 5: Run full Stage 4 gate and commit**

```bash
uv run ruff check .
uv run pyright
uv run pytest tests/unit/verification tests/unit/convergence tests/unit/security tests/unit/release -q
uv run pytest tests/integration/verification tests/integration/convergence tests/integration/security tests/integration/release -q
git add src tests README.md AGENTS.md
git commit -m "feat: make converged deployed evidence sole completion authority"
```

## Stage 4 completion gate

Required evidence:

- oracle tampering is prevented,
- vacuous new acceptance tests are detected,
- structural/integration/mutation/browser evidence is provenance-bound,
- fail/fail/pass critical history is not called stable,
- relevant changes invalidate stale evidence,
- default-deny egress blocks unknown destinations,
- destructive actions are denied in overnight profile,
- product access-control/security gates are executable,
- planned-task completion does not bypass convergence,
- confirmed convergence gaps return to build,
- clean-room preview cannot rely on dev-only state,
- deployed E2E is mandatory,
- exactly one production module can persist `RunStatus.DONE`.
