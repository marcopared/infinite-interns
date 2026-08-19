# Stage 3 Agent, Context, and Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Connect InfiniteInterns to real coding/review models while preserving typed contracts, fresh reviewer contexts, reproducible findings, and deterministic routing authority.

**Architecture:** Python owns a provider-neutral `AgentBackend` interface. Codex runs through a small TypeScript `@openai/codex-sdk` JSONL bridge inside the task worker. Kimi and DeepSeek are accessed through a model gateway using OpenAI-compatible APIs. The context builder emits task-specific packets; reviewers receive independent cold packets; model output is schema-validated before routing.

**Tech Stack:** Stage 2 stack plus TypeScript/Node 22, `@openai/codex-sdk`, OpenAI Python SDK, Pydantic JSON schemas.

**Spec:** `docs/architecture/infinite-interns-design.md`

## Global Constraints

- Provider responses never directly transition task/requirement/release authority states.
- Reviewer contexts never include the implementer's reasoning transcript.
- Agent-to-agent handoff uses typed artifacts and Git/evidence references.
- Codex may persist a session within one task; task boundaries and reviewer boundaries create fresh contexts.
- Kimi/DeepSeek output is advisory until reproduced or explicitly dispositioned.
- Provider failure is infrastructure failure unless evidence proves an engineering defect.

---

## File structure added by this stage

```text
src/infinite_interns/
  agents/
    base.py
    schemas.py
    codex.py
    openai_compatible.py
    kimi.py
    deepseek.py
    routing.py
  context/
    models.py
    builder.py
    repository_map.py
  review/
    service.py
    reproduction.py
  gateway/
    app.py
    capabilities.py
bridge/codex/
  package.json
  tsconfig.json
  src/index.ts
  src/protocol.ts
  tests/protocol.test.ts
prompts/
  implementer.md
  reviewer.md
  adversary.md
  diagnostician.md
tests/unit/agents/
tests/unit/context/
tests/integration/agents/
```

### Task 1: Define provider-neutral agent contracts

**Files:**
- Create: `src/infinite_interns/agents/base.py`
- Create: `src/infinite_interns/agents/schemas.py`
- Test: `tests/unit/agents/test_schemas.py`

**Interfaces:**
- `AgentBackend.start(request: AgentRequest) -> AgentSession`.
- `AgentBackend.run(session: AgentSession, request: AgentTurn) -> AgentResult`.
- `AgentBackend.close(session: AgentSession) -> None`.
- `AgentResult` fields: `status`, `summary`, `artifacts`, `evidence`, `candidate_commit`, `findings`, `decisions`, `memory_candidates`, `blockers`, `recommended_next_action`, `usage`.

- [ ] **Step 1: Write strict-schema tests**

```python
def test_agent_result_rejects_unknown_fields():
    with pytest.raises(ValidationError):
        AgentResult(status="ok", summary="x", surprise=True)


def test_reviewer_finding_requires_reproduction_strategy():
    with pytest.raises(ValidationError):
        ReviewFinding(
            finding_id="F1",
            severity="high",
            confidence=0.9,
            claim="auth bypass",
        )
```

- [ ] **Step 2: Implement enums and Pydantic models**

Use strict/frozen models. `ReviewFinding` must include `finding_id`, optional `requirement_id`, `severity`, `confidence`, `claim`, `reproduction_strategy`, `affected_paths`, and `evidence_refs`.

- [ ] **Step 3: Implement `AgentBackend` protocol**

```python
class AgentBackend(Protocol):
    async def start(self, request: AgentRequest) -> AgentSession: ...
    async def run(self, session: AgentSession, request: AgentTurn) -> AgentResult: ...
    async def close(self, session: AgentSession) -> None: ...
```

- [ ] **Step 4: Run and commit**

```bash
uv run pytest tests/unit/agents/test_schemas.py -q
git add src/infinite_interns/agents tests/unit/agents
git commit -m "feat: define typed agent backend contracts"
```

### Task 2: Build the Codex SDK JSONL bridge

**Files:**
- Create: `bridge/codex/package.json`
- Create: `bridge/codex/tsconfig.json`
- Create: `bridge/codex/src/protocol.ts`
- Create: `bridge/codex/src/index.ts`
- Create: `bridge/codex/tests/protocol.test.ts`
- Create: `src/infinite_interns/agents/codex.py`
- Test: `tests/integration/agents/test_codex_bridge_fake.py`

**Interfaces:**
- Stdin/stdout protocol is one JSON object per line.
- Request operations: `start`, `run`, `resume`, `close`, `ping`.
- Every response contains `request_id`, `ok`, and either `result` or `error`.
- Python `CodexBackend` implements `AgentBackend` without parsing human-readable terminal output.

- [ ] **Step 1: Define bridge protocol types**

```ts
export type BridgeRequest =
  | { request_id: string; op: "ping" }
  | { request_id: string; op: "start"; cwd: string; prompt: string }
  | { request_id: string; op: "run"; session_id: string; prompt: string }
  | { request_id: string; op: "resume"; session_id: string }
  | { request_id: string; op: "close"; session_id: string };
```

- [ ] **Step 2: Add `@openai/codex-sdk` and TypeScript tooling**

Use Node 22. Lock npm dependencies with `package-lock.json`.

- [ ] **Step 3: Implement bridge session map**

`start` creates a Codex thread in the requested worktree; `run` executes one turn; `resume` rehydrates the SDK thread/session identifier when supported; `close` releases bridge state. Errors are serialized, never printed as unstructured stdout.

- [ ] **Step 4: Write Node protocol tests with a fake SDK adapter**

Assert fragmented stdin lines are buffered correctly, malformed JSON returns an error response, and concurrent request IDs do not cross responses.

- [ ] **Step 5: Implement Python bridge client**

Use `asyncio.create_subprocess_exec` and explicit stdin/stdout framing. Persist the returned Codex session/thread ID in attempt metadata.

- [ ] **Step 6: Run bridge tests**

```bash
cd bridge/codex && npm ci && npm test
cd ../..
uv run pytest tests/integration/agents/test_codex_bridge_fake.py -q
```

- [ ] **Step 7: Commit**

```bash
git add bridge/codex src/infinite_interns/agents/codex.py tests/integration/agents/test_codex_bridge_fake.py
git commit -m "feat: add structured Codex SDK bridge"
```

### Task 3: Implement the model gateway and scoped attempt tokens

**Files:**
- Create: `src/infinite_interns/gateway/capabilities.py`
- Create: `src/infinite_interns/gateway/app.py`
- Test: `tests/unit/agents/test_gateway_capabilities.py`
- Test: `tests/integration/agents/test_gateway.py`

**Interfaces:**
- `GatewayCapability(run_id, task_id, attempt_id, lease_epoch, providers, models, expires_at)`.
- `issue_gateway_token(capability) -> str`.
- Gateway verifies current lease epoch before proxying provider traffic.
- Master provider keys are loaded only by gateway process.

- [ ] **Step 1: Write expired/stale token tests**

```python
async def test_stale_epoch_token_is_rejected(client, stale_token):
    response = await client.post("/v1/proxy/openai", headers={"Authorization": f"Bearer {stale_token}"})
    assert response.status_code == 403
```

- [ ] **Step 2: Implement signed short-lived capability token**

Use HMAC-SHA256 with a gateway signing secret held only by the gateway. Token payload contains no provider secret.

- [ ] **Step 3: Implement provider allowlist enforcement**

A token issued for Kimi cannot call DeepSeek or OpenAI. A token issued for one model cannot silently switch models.

- [ ] **Step 4: Add secret redaction middleware**

Ensure gateway logs record provider, model, latency, token counts/cost metadata, run/task/attempt IDs, and status, but never Authorization values or provider keys.

- [ ] **Step 5: Run and commit**

```bash
uv run pytest tests/unit/agents/test_gateway_capabilities.py tests/integration/agents/test_gateway.py -q
git add src/infinite_interns/gateway tests
git commit -m "feat: broker model access through scoped gateway"
```

### Task 4: Add Kimi and DeepSeek reviewer adapters

**Files:**
- Create: `src/infinite_interns/agents/openai_compatible.py`
- Create: `src/infinite_interns/agents/kimi.py`
- Create: `src/infinite_interns/agents/deepseek.py`
- Test: `tests/unit/agents/test_openai_compatible.py`

**Interfaces:**
- `KimiBackend` defaults to `k3-256k`; caller may request `k3` for large-context audit.
- `DeepSeekBackend` defaults to `deepseek-v4-pro` with thinking enabled/high reasoning.
- Both return validated `AgentResult`/`ReviewFinding` models.

- [ ] **Step 1: Write HTTP-contract tests with `httpx.MockTransport`**

Assert Kimi requests use base URL `https://api.kimi.com/coding/v1`, DeepSeek uses `https://api.deepseek.com`, and provider errors map to `ProviderUnavailable` rather than engineering failure.

- [ ] **Step 2: Implement shared OpenAI-compatible adapter**

Normalize usage, latency, error class, and JSON content. Parse JSON into Pydantic; on schema failure, allow one schema-repair retry with the same provider and record both attempts.

- [ ] **Step 3: Add Kimi defaults**

Use `k3-256k` for normal review packets and `k3` only when router marks the context `large_context=True`.

- [ ] **Step 4: Add DeepSeek defaults**

Use `deepseek-v4-pro`, `reasoning_effort="high"`, and thinking enabled through provider-compatible extra body.

- [ ] **Step 5: Run and commit**

```bash
uv run pytest tests/unit/agents/test_openai_compatible.py -q
git add src/infinite_interns/agents tests/unit/agents
git commit -m "feat: add Kimi and DeepSeek adversarial backends"
```

### Task 5: Build repository map and task context packets

**Files:**
- Create: `src/infinite_interns/context/models.py`
- Create: `src/infinite_interns/context/repository_map.py`
- Create: `src/infinite_interns/context/builder.py`
- Test: `tests/unit/context/test_builder.py`

**Interfaces:**
- `ContextPacket` fields: role, objective, success_conditions, requirement_refs, architecture_refs, protected_paths, relevant_paths, dependency_outputs, current_failures, available_tools, required_evidence, deadline, budget, generated_at_commit.
- `ContextBuilder.build(task_id, role, commit) -> ContextPacket`.

- [ ] **Step 1: Write minimal-context test**

Create a fixture repo where task affects `src/search/**`; assert unrelated `docs/payments.md` and `src/payments/**` are not injected in the initial packet.

- [ ] **Step 2: Write freshness test**

Generate packet at commit A, change a relevant file at B, and assert `ContextBuilder.is_fresh(packet, B)` is false.

- [ ] **Step 3: Implement repository map**

Index file paths, detected language/module role, direct imports where parseable, test-file relation by naming/path convention, requirement/file links from evidence/task metadata, and architecture-doc refs. Keep parser adapters isolated so unsupported languages fall back to path/text search.

- [ ] **Step 4: Implement progressive packet builder**

Initial packet contains summaries and references. Large logs remain artifact URIs. Provide separate lookup methods for deeper retrieval.

- [ ] **Step 5: Run and commit**

```bash
uv run pytest tests/unit/context -q
git add src/infinite_interns/context tests/unit/context
git commit -m "feat: generate commit-aware task contexts"
```

### Task 6: Version role prompts and enforce cold reviewer packets

**Files:**
- Create: `prompts/implementer.md`
- Create: `prompts/reviewer.md`
- Create: `prompts/adversary.md`
- Create: `prompts/diagnostician.md`
- Create: `src/infinite_interns/agents/prompting.py`
- Test: `tests/unit/agents/test_prompting.py`

**Interfaces:**
- `PromptRef(name, version, sha256)`.
- `PromptRegistry.load(name) -> PromptTemplate`.
- Reviewer renderer accepts only `ReviewerContext`, a type that has no implementer transcript field.

- [ ] **Step 1: Write reviewer-isolation test**

Attempt to construct a reviewer prompt with an `implementer_transcript` key. Expected: Pydantic validation failure.

- [ ] **Step 2: Write concise role contracts**

Implementer: inspect, implement, verify, commit candidate; cannot verify requirement.
Reviewer: find blockers against original requirement/diff/evidence; no author reasoning.
Adversary: produce typed candidate defects with reproduction strategy.
Diagnostician: explain repeated failure and propose a materially different repair strategy.

- [ ] **Step 3: Hash/version prompts**

Prompt version and SHA-256 are included in every model-call metadata record.

- [ ] **Step 4: Run and commit**

```bash
uv run pytest tests/unit/agents/test_prompting.py -q
git add prompts src/infinite_interns/agents/prompting.py tests/unit/agents/test_prompting.py
git commit -m "feat: add versioned isolated agent role prompts"
```

### Task 7: Implement review tiers, finding synthesis, and reproduction queue

**Files:**
- Create: `src/infinite_interns/agents/routing.py`
- Create: `src/infinite_interns/review/service.py`
- Create: `src/infinite_interns/review/reproduction.py`
- Test: `tests/unit/agents/test_routing.py`
- Test: `tests/integration/agents/test_review_reproduction.py`

**Interfaces:**
- `ReviewTier`: `STANDARD`, `IMPORTANT`, `CRITICAL`.
- `RoutingPolicy.for_task(TaskFeatures) -> ReviewPlan`.
- `ReproductionService.enqueue(finding) -> ReproductionTask`.
- A reproduced finding becomes `CONFIRMED`; failed reproduction becomes `NOT_REPRODUCED`; neither result is decided by majority vote.

- [ ] **Step 1: Write routing tests**

Auth/migration/security-sensitive tasks must route to critical policy. Low-risk narrow changes route to standard policy. Two similar failures trigger diagnostician escalation.

- [ ] **Step 2: Implement deterministic router**

Use task metadata only: risk, touched domains, migration flag, external integration, failure count, estimated context size. No model decides review tier.

- [ ] **Step 3: Write reproduction test with false positive**

Synthetic reviewer claims `GET /health returns 500`; deterministic reproduction receives 200. Assert finding is `NOT_REPRODUCED` and does not create a repair task.

- [ ] **Step 4: Write reproduced-defect test**

Synthetic reviewer claims unauthorized user can access another user's record; fixture reproduction receives 200 instead of 403. Assert finding becomes `CONFIRMED` and repair task is created.

- [ ] **Step 5: Run and commit**

```bash
uv run pytest tests/unit/agents/test_routing.py tests/integration/agents/test_review_reproduction.py -q
git add src/infinite_interns/agents/routing.py src/infinite_interns/review tests
git commit -m "feat: turn model review claims into reproducible work"
```

### Task 8: Wire task-local implement/review/repair loop into worker orchestration

**Files:**
- Modify: `src/infinite_interns/graph/nodes.py`
- Modify: `src/infinite_interns/scheduler/service.py`
- Create: `src/infinite_interns/agents/worker_service.py`
- Create: `tests/integration/agents/test_stage3_acceptance.py`
- Modify: `README.md`
- Modify: `AGENTS.md`

**Interfaces:**
- `WorkerService.execute_task(attempt) -> CandidateResult`.
- Same Codex session may handle implementation and task-local repair.
- Reviewer invocation always creates a new session/backend request.

- [ ] **Step 1: Build seeded-defect fixture repo**

Fixture contains a failing API validation behavior with an existing deterministic test command and a separate hidden reviewer reproduction script.

- [ ] **Step 2: Run primary backend through implementation/fix cycle**

In CI use a deterministic fake `AgentBackend` that applies a known patch. In provider opt-in test use real Codex bridge.

- [ ] **Step 3: Assert reviewer context is fresh**

Capture backend requests and assert implementation session ID never appears in reviewer request metadata/content.

- [ ] **Step 4: Inject one false reviewer finding and one true finding**

Assert only reproduced defect creates repair work.

- [ ] **Step 5: Run stage gate**

```bash
uv run ruff check .
uv run pyright
uv run pytest tests/unit/agents tests/unit/context -q
uv run pytest tests/integration/agents -q
cd bridge/codex && npm test
```

- [ ] **Step 6: Update docs and commit**

```bash
git add src tests prompts bridge README.md AGENTS.md
git commit -m "feat: complete typed multi-model worker pipeline"
```

## Stage 3 completion gate

Required evidence:

- Codex bridge protocol is structured and resumable at task scope,
- provider failures are classified as infrastructure failures,
- Kimi/DeepSeek responses are schema validated,
- context packets are commit-aware and minimal,
- reviewer contexts cannot contain implementer transcript fields,
- false-positive review claims can be rejected by reproduction,
- confirmed findings create repair work,
- no model output directly marks requirement/release success.
