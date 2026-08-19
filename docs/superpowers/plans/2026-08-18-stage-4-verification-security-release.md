# Stage 4 Verification, Security, and Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the protected acceptance/evidence system, browser/runtime verification, security boundary, clean-room preview deployment, and the only valid transition from release `PASS` to run `DONE`.

**Architecture:** Verification is layered E0-E5 and every result is provenance-bound. Protected oracles are mounted read-only into verifier containers, never into implementation authority. Security is enforced by capability checks, Docker isolation, scoped model tokens, and default-deny egress through an allowlist proxy. Release rebuilds from a fresh clone into an isolated preview container and reruns critical E2E before deterministic completion.

**Tech Stack:** Stage 3 stack plus Playwright, pytest, Docker Compose internal networks, Squid allowlist proxy, SHA-256 environment manifests, optional security scanners through command adapters.

**Spec:** `docs/architecture/infinite-interns-design.md`

## Global Constraints

- Protected oracle content is immutable to implementation workers.
- A failing or unstable critical browser journey blocks release regardless of model opinion.
- Evidence from another commit/environment/verifier version cannot prove the current candidate.
- Repeated pass after earlier semantic failures is `UNSTABLE` until the configured stability rule is satisfied.
- Worker egress is denied unless explicitly allowed by task profile.
- Model gateway capability tokens grant no filesystem/cloud/GitHub/database authority.
- Only a deterministic release-transition service may write `RunStatus.DONE`, and only after `ReleasePredicate` returns `PASS`.

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
    stability.py
    failure_package.py
    impact.py
  oracles/
    manifest.py
    protection.py
  security/
    capabilities.py
    policy.py
    secrets.py
    redaction.py
    actions.py
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
tests/unit/security/
tests/integration/verification/
tests/integration/security/
tests/integration/release/
```

### Task 1: Define verification adapters and gate manifests

**Files:**
- Create: `src/infinite_interns/verification/base.py`
- Create: `src/infinite_interns/oracles/manifest.py`
- Create: `tests/unit/verification/test_manifest.py`

**Interfaces:**
- `VerificationAdapter.run(request) -> VerificationResult`.
- `GateDefinition(gate_id, requirement_id, level, mandatory, critical, command, timeout_seconds)`.
- `AcceptanceManifest(version, gates, whole_product_journeys, release_gates)`.

- [ ] **Step 1: Write manifest validation tests**

```python
def test_duplicate_gate_id_is_rejected():
    with pytest.raises(ValueError):
        AcceptanceManifest(version="1", gates=[gate("A"), gate("A")])


def test_critical_gate_must_be_mandatory():
    with pytest.raises(ValueError):
        GateDefinition(
            gate_id="AUTH-E2E",
            requirement_id="AUTH-1",
            level="e3",
            mandatory=False,
            critical=True,
            command=["pytest", "x"],
            timeout_seconds=60,
        )
```

- [ ] **Step 2: Implement strict gate/manifest models**

Levels are exactly `E0`, `E1`, `E2`, `E3`, `E4`, `E5`. Every gate has a stable ID and explicit requirement mapping or release-wide scope.

- [ ] **Step 3: Run and commit**

```bash
uv run pytest tests/unit/verification/test_manifest.py -q
git add src/infinite_interns/verification src/infinite_interns/oracles tests/unit/verification
git commit -m "feat: define executable acceptance manifests"
```

### Task 2: Protect acceptance oracles and perform vacuity checks

**Files:**
- Create: `src/infinite_interns/oracles/protection.py`
- Create: `docker/verifier/Dockerfile`
- Create: `tests/integration/verification/test_oracle_protection.py`
- Create: `tests/integration/verification/test_vacuity.py`

**Interfaces:**
- `OracleBundle(bundle_id, manifest_uri, content_hash, source_commit)`.
- Implementation containers receive no writable mount for oracle bundle.
- Verifier mounts bundle at `/opt/interns/oracle:ro`.
- `run_vacuity_check(gate, baseline_commit) -> VacuityResult`.

- [ ] **Step 1: Write tampering test**

Launch a worker fixture and attempt to write `/opt/interns/oracle/test.txt`. Expected: filesystem failure and a policy event; the oracle hash remains unchanged.

- [ ] **Step 2: Implement immutable bundle hashing**

Hash sorted relative paths plus file bytes with SHA-256. Persist bundle hash in evidence metadata.

- [ ] **Step 3: Implement vacuity runner**

For gates representing new behavior, run gate against baseline/pre-feature commit. A gate that returns PASS when its mapped behavior is absent returns `SUSPICIOUS_PASS`, which blocks oracle approval.

- [ ] **Step 4: Run and commit**

```bash
uv run pytest tests/integration/verification/test_oracle_protection.py tests/integration/verification/test_vacuity.py -q
git add src/infinite_interns/oracles docker/verifier tests/integration/verification
git commit -m "feat: protect and sanity-check acceptance oracles"
```

### Task 3: Implement structural, command, and integration verification

**Files:**
- Create: `src/infinite_interns/verification/command.py`
- Create: `src/infinite_interns/verification/structural.py`
- Create: `src/infinite_interns/verification/integration.py`
- Test: `tests/unit/verification/test_command.py`
- Test: `tests/integration/verification/test_integration_adapter.py`

**Interfaces:**
- `CommandVerificationAdapter` executes argv without shell interpolation and captures stdout/stderr artifacts.
- `StructuralSuite` runs configured build/type/lint/security/secret commands.
- `IntegrationSuite` receives isolated service URLs/DB IDs and emits requirement-linked evidence.

- [ ] **Step 1: Write timeout and exit-code tests**

Assert timeout produces `INFRA_ERROR` or configured engineering failure class, never `PASS`. Nonzero deterministic assertion command produces `FAIL`.

- [ ] **Step 2: Implement normalized result**

Result includes start/end timestamps, exit code, command digest, assertion counts where available, artifact URIs, commit, environment hash, and verifier version.

- [ ] **Step 3: Run integration fixture with real PostgreSQL**

Fixture service writes one row and API reads it back; verifier asserts both HTTP result and DB side effect.

- [ ] **Step 4: Run and commit**

```bash
uv run pytest tests/unit/verification/test_command.py tests/integration/verification/test_integration_adapter.py -q
git add src/infinite_interns/verification tests
git commit -m "feat: add deterministic structural and integration verification"
```

### Task 4: Add Playwright browser verification and forensic failure packages

**Files:**
- Create: `src/infinite_interns/verification/playwright.py`
- Create: `src/infinite_interns/verification/failure_package.py`
- Create: `tests/fixtures/webapp/`
- Create: `tests/integration/verification/test_playwright_adapter.py`

**Interfaces:**
- Playwright adapter runs workload-supplied Playwright commands inside verifier container.
- `FailurePackage` includes gate ID, expected, actual, trace URI, screenshots, browser console, network summary, backend-log refs, DB-state refs, first failing commit, and last green commit.

- [ ] **Step 1: Add Playwright tooling to verifier image**

Use a pinned Playwright Python package/browser image compatible with the lockfile. Browser profile is unique per attempt.

- [ ] **Step 2: Create fixture web app and journey**

Journey saves an item, refreshes, logs out/in, and verifies persisted state. Add an intentional broken mode where frontend local state changes but database does not.

- [ ] **Step 3: Assert broken mode creates full failure package**

The test must verify trace/screenshot/log artifact URIs exist and the evidence result is `FAIL`.

- [ ] **Step 4: Assert working mode passes after persistence and relogin**

- [ ] **Step 5: Run and commit**

```bash
uv run pytest tests/integration/verification/test_playwright_adapter.py -q
git add src/infinite_interns/verification tests/fixtures/webapp tests/integration/verification
git commit -m "feat: add browser acceptance evidence and failure forensics"
```

### Task 5: Implement stability classification and evidence invalidation

**Files:**
- Create: `src/infinite_interns/verification/stability.py`
- Create: `src/infinite_interns/verification/impact.py`
- Create: `src/infinite_interns/evidence/invalidation.py`
- Test: `tests/unit/verification/test_stability.py`
- Test: `tests/unit/verification/test_impact.py`

**Interfaces:**
- `StabilityClassifier.classify(attempt_results) -> EvidenceResult`.
- `ImpactAnalyzer.affected_requirements(change_set) -> set[str]`.
- `EvidenceInvalidator.invalidate(commit_before, commit_after, affected_requirements)`.

- [ ] **Step 1: Write retry-washing test**

```python
def test_fail_fail_pass_is_unstable():
    assert classify([FAIL, FAIL, PASS]) == UNSTABLE
```

- [ ] **Step 2: Implement semantic stability rules**

Identical deterministic failures followed by a pass do not become stable without a code/environment change that explains the result. Infrastructure-only failures may be retried separately and do not count as product passes.

- [ ] **Step 3: Write impact invalidation test**

Change session module mapped to AUTH requirements and assert prior AUTH evidence is stale while unrelated copy-lint evidence remains valid.

- [ ] **Step 4: Implement conservative fallback**

If impact analysis cannot establish independence, invalidate broader evidence rather than reusing questionable proof. Full release suite always runs from current commit regardless of incremental reuse.

- [ ] **Step 5: Run and commit**

```bash
uv run pytest tests/unit/verification/test_stability.py tests/unit/verification/test_impact.py -q
git add src/infinite_interns/verification src/infinite_interns/evidence/invalidation.py tests/unit/verification
git commit -m "feat: reject flaky passes and invalidate stale evidence"
```

### Task 6: Enforce capabilities, action classes, redaction, and secret refs

**Files:**
- Create: `src/infinite_interns/security/capabilities.py`
- Create: `src/infinite_interns/security/actions.py`
- Create: `src/infinite_interns/security/policy.py`
- Create: `src/infinite_interns/security/secrets.py`
- Create: `src/infinite_interns/security/redaction.py`
- Test: `tests/unit/security/test_policy.py`
- Test: `tests/unit/security/test_redaction.py`

**Interfaces:**
- `ActionClass`: `LOCAL_REVERSIBLE`, `ISOLATED_EXTERNAL`, `SHARED_REVERSIBLE`, `DESTRUCTIVE_HIGH_IMPACT`.
- `CapabilityEnvelope` binds run/task/attempt/lease epoch, filesystem scope, network profile, DB scope, Git actions, browser scope, expiry.
- Persisted secrets are refs such as `secret://providers/openai`.

- [ ] **Step 1: Write policy decision matrix tests**

Overnight profile allows worktree edits/test DB/preview deploy but denies production DB deletion, force-push protected main, real-user messaging, and arbitrary secret export.

- [ ] **Step 2: Implement deterministic policy engine**

```python
Decision = Literal["allow", "deny", "requires_pre_authorization"]
```

Every decision emits a `POLICY_DECISION` event with rule ID and no secret values.

- [ ] **Step 3: Implement redaction**

Redact configured token patterns, Authorization headers, secret values known to the broker, and common key formats before event/artifact persistence.

- [ ] **Step 4: Run and commit**

```bash
uv run pytest tests/unit/security -q
git add src/infinite_interns/security tests/unit/security
git commit -m "feat: enforce scoped security capabilities"
```

### Task 7: Add default-deny Docker networking through allowlist proxy

**Files:**
- Create: `docker/squid/squid.conf`
- Modify: `docker-compose.workstation.yml`
- Create: `tests/integration/security/test_network_policy.py`

**Interfaces:**
- Worker network is Docker `internal: true`.
- Egress proxy is connected to both internal and external networks.
- Worker `HTTP_PROXY`/`HTTPS_PROXY` point at proxy.
- Allowlist is generated per profile into mounted Squid config; unknown domains are denied.

- [ ] **Step 1: Configure default deny**

Squid base policy:

```text
http_access deny all
```

Generated allow rules are inserted before final deny. Local service addresses remain reachable through internal network without internet egress.

- [ ] **Step 2: Write network test**

Worker must reach configured package-test fixture/localhost service but fail to reach an unlisted external domain. The denied attempt produces a policy/network event.

- [ ] **Step 3: Assert worker has no Docker socket**

Inside worker:

```bash
test ! -e /var/run/docker.sock
```

- [ ] **Step 4: Run and commit**

```bash
uv run pytest tests/integration/security/test_network_policy.py -q
git add docker/squid docker-compose.workstation.yml tests/integration/security
git commit -m "feat: default-deny worker network egress"
```

### Task 8: Implement clean-room Docker preview deployment

**Files:**
- Create: `src/infinite_interns/release/base.py`
- Create: `src/infinite_interns/release/docker_preview.py`
- Create: `src/infinite_interns/release/service.py`
- Create: `docker/release/Dockerfile`
- Test: `tests/integration/release/test_docker_preview.py`

**Interfaces:**
- `DeploymentBackend.deploy(request) -> DeploymentRecord`.
- `DockerPreviewDeployment` clones exact candidate commit into empty workspace, runs configured install/migration/build/start commands, returns preview URL and environment hash.
- Release verifier never reuses worker virtualenv/node_modules/database.

- [ ] **Step 1: Write contamination test**

Put an untracked dependency artifact in development worktree that makes app pass locally. Clean-room deployment must fail because the artifact is absent from Git.

- [ ] **Step 2: Implement fresh-clone build**

Clone from repository source at exact commit SHA, install strictly from lockfiles, create fresh DB, run migrations, production build, and start container.

- [ ] **Step 3: Run critical Playwright suite against returned preview URL**

Evidence level is E5 and must include deployment ID/environment hash.

- [ ] **Step 4: Test restart/persistence**

Restart application container without replacing database and rerun configured persistence journey.

- [ ] **Step 5: Run and commit**

```bash
uv run pytest tests/integration/release/test_docker_preview.py -q
git add src/infinite_interns/release docker/release tests/integration/release
git commit -m "feat: add clean-room Docker preview release"
```

### Task 9: Add the sole DONE transition and Stage 4 release acceptance suite

**Files:**
- Create: `src/infinite_interns/release/transition.py`
- Create: `tests/unit/release/test_transition.py`
- Create: `tests/integration/release/test_stage4_acceptance.py`
- Modify: `AGENTS.md`
- Modify: `README.md`

**Interfaces:**
- `ReleaseTransitionService.complete_run(run_id, evaluation, expected_commit) -> RunRecord`.
- It accepts only `ReleaseEvaluation(status=PASS)` produced for current run/current commit/current release environment.
- This file is the only production code allowed to assign `RunStatus.DONE`.

- [ ] **Step 1: Write transition-denial tests**

Cases: FAIL, BLOCKED, UNSTABLE, stale commit, wrong run ID, missing E5 deployed evidence. All must raise `ReleaseNotSatisfied` and leave run non-DONE.

- [ ] **Step 2: Implement transition service**

Inside one DB transaction, re-read current run commit, current mandatory evidence, and evaluation inputs; recompute predicate or validate evaluation digest; then set `PASS` and `DONE` transition atomically and emit `RUN_DONE` event.

- [ ] **Step 3: Add codebase invariant test**

Search Python AST for assignments/repository updates that set `RunStatus.DONE`. Assert only `release/transition.py` is allowlisted.

- [ ] **Step 4: Build Stage 4 acceptance scenarios**

The fixture release must be denied for each condition independently:

1. broken protected E2E,
2. stale evidence,
3. flaky critical journey,
4. oracle hash mismatch,
5. unauthorized destructive action attempt,
6. failed clean install,
7. failed migration,
8. failed deployed E2E.

Then repair all conditions and assert exact one valid DONE transition.

- [ ] **Step 5: Run full stage gate**

```bash
uv run ruff check .
uv run pyright
uv run pytest tests/unit/verification tests/unit/security tests/unit/release -q
uv run pytest tests/integration/verification tests/integration/security tests/integration/release -q
```

- [ ] **Step 6: Update docs and commit**

```bash
git add src tests README.md AGENTS.md
git commit -m "feat: make deployed evidence the sole completion authority"
```

## Stage 4 completion gate

Required evidence:

- oracle write attempts fail,
- vacuous new acceptance test is detected,
- Playwright failure artifacts are complete,
- fail/fail/pass critical sequence is not considered stable,
- relevant code change invalidates stale evidence,
- default-deny egress blocks unknown destination,
- destructive actions are denied in overnight profile,
- clean-room preview cannot rely on dev-only state,
- deployed E2E is required,
- static analysis confirms exactly one production location can write `RunStatus.DONE`.
