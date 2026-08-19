# Stage 3B Agent, Context, and Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Connect InfiniteInterns to real coding/review models while preserving scoped credentials, typed contracts, fresh reviewer contexts, durable validated memory, reproducible findings, and deterministic routing/escalation authority.

**Architecture:** Python owns provider-neutral agent services. Codex runs through a TypeScript `@openai/codex-sdk` bridge in the task sandbox; the SDK talks to InfiniteInterns ModelGateway using a custom `baseUrl` and a short-lived attempt capability token as its API key. The gateway validates run/task/attempt/lease/provider/model scope and substitutes the real provider credential. Kimi and DeepSeek also route through the gateway. Context is task-specific and commit-aware. Reviewers receive cold context. Model findings become structured hypotheses routed through reproduction; models never decide completion.

**Tech Stack:** Stages 1-3A plus TypeScript/Node 22, `@openai/codex-sdk`, httpx, Pydantic JSON schemas.

**Spec:** `docs/architecture/infinite-interns-design.md`

## Global Constraints

- Provider responses never directly transition requirement/release/run authority states.
- Master model-provider credentials never enter a worker container.
- Reviewer contexts never include the implementer's reasoning transcript.
- Agent-to-agent handoff uses Git, typed artifacts, evidence, findings, and validated decisions.
- Codex may persist one session within one task while making progress; task/reviewer boundaries are fresh contexts.
- Kimi/DeepSeek output is advisory until reproduced/dispositioned.
- Provider outage is infrastructure failure, not code failure.
- Repeated engineering failure triggers strategy escalation rather than unbounded same-strategy retry.
- Durable memory stores validated conclusions, not reasoning diaries.

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
    prompting.py
    worker_service.py
  context/
    models.py
    repository_map.py
    builder.py
    memory.py
  review/
    service.py
    reproduction.py
  gateway/
    app.py
    capabilities.py
    providers.py
bridge/codex/
  package.json
  package-lock.json
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

### Task 1: Define typed agent contracts

**Files:**
- Create: `src/infinite_interns/agents/base.py`
- Create: `src/infinite_interns/agents/schemas.py`
- Test: `tests/unit/agents/test_schemas.py`

**Interfaces:**
- `AgentBackend.start(request: AgentRequest) -> AgentSession`.
- `AgentBackend.run(session: AgentSession, turn: AgentTurn) -> AgentResult`.
- `AgentBackend.close(session: AgentSession) -> None`.
- `AgentResult` contains status, summary, artifact/evidence refs, candidate commit, findings, decisions, memory candidates, blockers, recommended next action, and usage.

- [ ] **Step 1: Write strict-schema tests**

```python
from pydantic import ValidationError
import pytest

from infinite_interns.agents.schemas import AgentResult, ReviewFinding


def test_agent_result_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        AgentResult.model_validate({"status": "ok", "summary": "x", "surprise": True})


def test_reviewer_finding_requires_reproduction_strategy() -> None:
    with pytest.raises(ValidationError):
        ReviewFinding.model_validate(
            {
                "finding_id": "F1",
                "severity": "high",
                "confidence": 0.9,
                "claim": "authorization bypass",
            }
        )
```

- [ ] **Step 2: Implement frozen Pydantic schemas**

Define `AgentRequest`, `AgentTurn`, `AgentSession`, `UsageRecord`, `ReviewFinding`, `AgentResult`, `DecisionCandidate`, `MemoryCandidate`, `Blocker`. `ReviewFinding` requires claim, severity, confidence, reproduction strategy, affected paths, and evidence refs.

- [ ] **Step 3: Implement abstract backend**

```python
from abc import ABC, abstractmethod

from .schemas import AgentRequest, AgentResult, AgentSession, AgentTurn


class AgentBackend(ABC):
    @abstractmethod
    async def start(self, request: AgentRequest) -> AgentSession:
        raise NotImplementedError

    @abstractmethod
    async def run(self, session: AgentSession, turn: AgentTurn) -> AgentResult:
        raise NotImplementedError

    @abstractmethod
    async def close(self, session: AgentSession) -> None:
        raise NotImplementedError
```

- [ ] **Step 4: Verify and commit**

```bash
uv run pytest tests/unit/agents/test_schemas.py -q
uv run pyright
git add src/infinite_interns/agents tests/unit/agents
git commit -m "feat: define typed agent backend contracts"
```

### Task 2: Implement scoped ModelGateway compatible with Codex SDK

**Files:**
- Create: `src/infinite_interns/gateway/capabilities.py`
- Create: `src/infinite_interns/gateway/providers.py`
- Create: `src/infinite_interns/gateway/app.py`
- Create: `tests/unit/agents/test_gateway_capabilities.py`
- Create: `tests/integration/agents/test_gateway.py`

**Interfaces:**
- `GatewayCapability(run_id, task_id, attempt_id, lease_epoch, provider, allowed_models, expires_at)`.
- `issue_gateway_token(capability, signing_key) -> str`.
- Gateway exposes an OpenAI-compatible `/v1/responses` route for Codex plus compatible chat/response routes required by reviewer adapters.
- Gateway validates current lease epoch before forwarding.

- [ ] **Step 1: Write token-scope tests**

Test expired token, stale lease epoch, wrong provider, and wrong model. All return 403 without invoking fake upstream transport.

```python
async def test_stale_epoch_token_is_rejected(client, stale_token: str) -> None:
    response = await client.post(
        "/v1/responses",
        headers={"Authorization": f"Bearer {stale_token}"},
        json={"model": "codex-model", "input": "ping"},
    )
    assert response.status_code == 403
```

- [ ] **Step 2: Implement HMAC capability token**

Canonical JSON payload contains only scoped identifiers/permissions/expiry. Sign with gateway-only HMAC key. Never place provider API secret in token.

- [ ] **Step 3: Implement upstream provider registry**

`ProviderRegistry` resolves `secret://providers/openai`, `secret://providers/kimi`, and `secret://providers/deepseek` only inside gateway process, selects upstream base URL/protocol, and injects actual Authorization upstream.

- [ ] **Step 4: Implement transparent OpenAI Responses proxy**

For `/v1/responses`, validate capability and requested model, preserve request/stream semantics needed by Codex, forward to configured OpenAI upstream, and return compatible status/body/stream. Do not log request Authorization or provider credentials.

- [ ] **Step 5: Add redacted usage metadata**

Record run/task/attempt/provider/model, latency, response status, token/cost metadata when available, and capability ID—not raw token value.

- [ ] **Step 6: Verify and commit**

```bash
uv run pytest tests/unit/agents/test_gateway_capabilities.py tests/integration/agents/test_gateway.py -q
git add src/infinite_interns/gateway tests
git commit -m "feat: broker scoped model access through gateway"
```

### Task 3: Build Codex SDK JSONL bridge through ModelGateway

**Files:**
- Create: `bridge/codex/package.json`
- Create: `bridge/codex/package-lock.json`
- Create: `bridge/codex/tsconfig.json`
- Create: `bridge/codex/src/protocol.ts`
- Create: `bridge/codex/src/index.ts`
- Create: `bridge/codex/tests/protocol.test.ts`
- Create: `src/infinite_interns/agents/codex.py`
- Test: `tests/integration/agents/test_codex_bridge_fake.py`

**Interfaces:**
- JSONL request ops: `ping`, `start`, `run`, `resume`, `close`.
- Bridge obtains `INFINITE_INTERNS_MODEL_GATEWAY_URL` and `INFINITE_INTERNS_MODEL_TOKEN` from worker environment.
- SDK client uses `baseUrl=<gateway>/v1` and `apiKey=<scoped token>`.
- Required Codex environment is explicitly allowlisted; bridge does not inherit host environment wholesale.

- [ ] **Step 1: Define bridge protocol**

```ts
export type BridgeRequest =
  | { request_id: string; op: "ping" }
  | { request_id: string; op: "start"; cwd: string; prompt: string }
  | { request_id: string; op: "run"; session_id: string; prompt: string }
  | { request_id: string; op: "resume"; session_id: string }
  | { request_id: string; op: "close"; session_id: string };
```

Every response is `{request_id, ok, result}` or `{request_id, ok:false, error:{code,message}}`.

- [ ] **Step 2: Add SDK/tooling and lock dependencies**

Use Node 22, install current `@openai/codex-sdk`, TypeScript, and test runner; commit `package-lock.json`.

- [ ] **Step 3: Configure SDK securely**

Instantiate Codex with gateway URL and scoped token, and an explicit environment map containing only PATH, HOME/CODEX_HOME inside the worker, locale, model-gateway variables, and workload-required nonsecret variables. SDK thread working directory is the task worktree.

- [ ] **Step 4: Implement session lifecycle**

`start` creates a thread and returns ID; `run` executes a turn; `resume` reconstructs thread from persisted ID; `close` drops bridge-local reference. Protocol stdout is JSONL only; diagnostics use stderr.

- [ ] **Step 5: Test with local fake Responses server**

Verify bridge sends model request to configured gateway base URL, not OpenAI directly; scoped token is sent as auth to fake gateway; fragmented JSONL handling and resume behavior work.

- [ ] **Step 6: Implement Python client and commit**

Use `asyncio.create_subprocess_exec`; pending request map is keyed by request ID; persist thread ID in attempt metadata.

```bash
cd bridge/codex
npm ci
npm test
cd ../..
uv run pytest tests/integration/agents/test_codex_bridge_fake.py -q
git add bridge/codex src/infinite_interns/agents/codex.py tests/integration/agents/test_codex_bridge_fake.py
git commit -m "feat: run Codex through scoped model gateway"
```

### Task 4: Add Kimi and DeepSeek reviewer adapters

**Files:**
- Create: `src/infinite_interns/agents/openai_compatible.py`
- Create: `src/infinite_interns/agents/kimi.py`
- Create: `src/infinite_interns/agents/deepseek.py`
- Test: `tests/unit/agents/test_openai_compatible.py`

**Interfaces:**
- `KimiBackend` default logical model `k3-256k`; `k3` for large audit.
- `DeepSeekBackend` default logical model `deepseek-v4-pro`.
- Both call ModelGateway using a scoped token and strict structured-output parser.

- [ ] **Step 1: Write MockTransport contract tests**

Assert adapter sends provider/model metadata expected by gateway, maps 429/5xx/timeouts to `ProviderUnavailable`, and never classifies provider transport failure as engineering failure.

- [ ] **Step 2: Implement shared compatible adapter**

Accept gateway URL/token, provider, model, prompt payload, response schema, timeout. Parse model content into Pydantic. Allow one schema-repair turn after invalid structured output and preserve both usage records.

- [ ] **Step 3: Implement provider defaults and commit**

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
- `ContextPacket` contains role/objective/success conditions, requirement/spec/architecture refs, protected paths, relevant paths, dependency outputs, current failures, available tools, required evidence, deadline/budget, and `generated_at_commit`.
- `ContextBuilder.build(task_id, role, commit) -> ContextPacket`.
- `ContextBuilder.is_fresh(packet, current_commit) -> bool`.

- [ ] **Step 1: Write minimal-context test**

Fixture task maps to `src/search/**`; initial packet contains mapped search sources/tests/architecture refs and excludes unrelated payments subtree/docs.

- [ ] **Step 2: Write freshness test**

Relevant file changed after packet commit -> false. Unrelated file changed with no dependency edge -> packet can remain usable.

- [ ] **Step 3: Implement repository map**

Index file roles/languages, imports where parseable, source-test relations, routes/DB entities using adapters, requirement/task/file/evidence links, and architecture refs. Unsupported languages fall back to path/text map.

- [ ] **Step 4: Implement progressive disclosure**

Initial packet uses summaries/URIs for large evidence; expose explicit lookups for source excerpts, log slices, decisions, warnings, and dependency outputs.

- [ ] **Step 5: Verify and commit**

```bash
uv run pytest tests/unit/context/test_builder.py -q
git add src/infinite_interns/context tests/unit/context
git commit -m "feat: generate commit-aware task contexts"
```

### Task 6: Implement validated durable memory

**Files:**
- Create: `src/infinite_interns/context/memory.py`
- Create: `tests/unit/context/test_memory.py`

**Interfaces:**
- Memory kinds: `DECISION`, `RULE`, `LEARNING`, `WARNING`, `DEBT`, `ASSUMPTION`.
- `MemoryCandidate` must link evidence refs or an accepted architecture/spec decision before promotion to `MemoryRecord` for durable retrieval.

- [ ] **Step 1: Write rejection test**

A model candidate saying “always disable retries” with no evidence/decision reference is rejected. A learning referencing reproduced flaky-test root cause and repair evidence is accepted.

- [ ] **Step 2: Implement memory service**

Persist concise statement, kind, scope, source refs, validating evidence/decision refs, introduced-at commit, and invalidated-at commit. Never persist reasoning transcript as memory body.

- [ ] **Step 3: Verify and commit**

```bash
uv run pytest tests/unit/context/test_memory.py -q
git add src/infinite_interns/context/memory.py tests/unit/context/test_memory.py
git commit -m "feat: persist evidence-backed engineering memory"
```

### Task 7: Version prompts and enforce cold reviewer contexts

**Files:**
- Create: `prompts/implementer.md`
- Create: `prompts/reviewer.md`
- Create: `prompts/adversary.md`
- Create: `prompts/diagnostician.md`
- Create: `src/infinite_interns/agents/prompting.py`
- Test: `tests/unit/agents/test_prompting.py`

**Interfaces:**
- `PromptRef(name, version, sha256)`.
- `ReviewerContext` has no implementer-transcript/reasoning field and forbids extras.

- [ ] **Step 1: Write reviewer-isolation test**

`ReviewerContext.model_validate` with `implementer_transcript` must raise `ValidationError`.

- [ ] **Step 2: Write role contracts**

Implementer: inspect, implement smallest coherent solution, deterministic QA, candidate commit, never verify requirement.
Reviewer: original requirement + diff + repo/evidence only; return typed findings.
Adversary: find behavioral/security/integration gaps with reproduction strategy.
Diagnostician: analyze repeated evidence and propose materially different root-cause strategy.

- [ ] **Step 3: Version/hash prompt bytes and commit**

```bash
uv run pytest tests/unit/agents/test_prompting.py -q
git add prompts src/infinite_interns/agents/prompting.py tests/unit/agents/test_prompting.py
git commit -m "feat: add versioned isolated agent prompts"
```

### Task 8: Implement deterministic review tiers and reproduction routing

**Files:**
- Create: `src/infinite_interns/agents/routing.py`
- Create: `src/infinite_interns/review/service.py`
- Create: `src/infinite_interns/review/reproduction.py`
- Test: `tests/unit/agents/test_routing.py`
- Test: `tests/integration/agents/test_review_reproduction.py`

**Interfaces:**
- Review tiers `STANDARD`, `IMPORTANT`, `CRITICAL`.
- `RoutingPolicy.for_task(features) -> ReviewPlan`.
- Finding dispositions `PENDING`, `CONFIRMED`, `NOT_REPRODUCED`, `ADVISORY`.

- [ ] **Step 1: Write routing tests**

Auth/authz/migrations/security-sensitive work -> CRITICAL; low-risk narrow work -> STANDARD; two semantically similar failures -> diagnostic escalation.

- [ ] **Step 2: Implement deterministic router**

Input only risk/domain/migration/external integration/failure count/context-size metadata. No model chooses its own tier.

- [ ] **Step 3: Write reproduction tests**

False claim `GET /health returns 500` while actual 200 -> NOT_REPRODUCED/no repair task. True claim user B reads user A resource returning 200 instead of 403 -> CONFIRMED/repair task.

- [ ] **Step 4: Verify and commit**

```bash
uv run pytest tests/unit/agents/test_routing.py tests/integration/agents/test_review_reproduction.py -q
git add src/infinite_interns/agents/routing.py src/infinite_interns/review tests
git commit -m "feat: turn review claims into reproducible work"
```

### Task 9: Wire implement/review/repair and escalation ladder

**Files:**
- Create: `src/infinite_interns/agents/worker_service.py`
- Modify: `src/infinite_interns/graph/nodes.py`
- Modify: `src/infinite_interns/scheduler/service.py`
- Create: `tests/integration/agents/test_stage3b_acceptance.py`
- Modify: `README.md`
- Modify: `AGENTS.md`

**Interfaces:**
- `WorkerService.execute_task(attempt) -> CandidateResult`.
- Same task-local Codex session handles normal debug/repair while productive.
- Escalation levels:
  - L0 same Codex task-local debugging,
  - L1 fresh Codex diagnosis + repair,
  - L2 Kimi independent diagnosis + fresh Codex implementation,
  - L3 DeepSeek second diagnosis + architecture challenge,
  - L4 Kimi implementer + Codex reviewer,
  - L5 decompose/replan/alternate architecture,
  - still impossible -> BLOCKED.

- [ ] **Step 1: Build seeded-defect fixture**

One API validation defect, visible deterministic tests, hidden reproduction script, unrelated passing tests.

- [ ] **Step 2: Run deterministic fake implementation/review cycle in CI**

Fake implementer produces known patch and candidate SHA. QA passes. Fresh fake reviewer returns one false and one true finding. Reproduction discards false, confirms true, repair cycle produces final candidate.

- [ ] **Step 3: Assert reviewer isolation and escalation accounting**

Implementation session ID never appears in reviewer context. Attempt/escalation records persist level, provider/model/prompt refs, cause, cost, and outcome.

- [ ] **Step 4: Add optional real-provider smoke**

When scoped gateway/provider credentials exist, run one Codex task through gateway and one Kimi/DeepSeek structured review. This job is opt-in and budget-bounded, not required for ordinary CI.

- [ ] **Step 5: Run Stage 3B gate and commit**

```bash
uv run ruff check .
uv run pyright
uv run pytest tests/unit/agents tests/unit/context -q
uv run pytest tests/integration/agents -q
cd bridge/codex
npm test
cd ../..
git add src tests prompts bridge README.md AGENTS.md
git commit -m "feat: complete scoped multi-model worker pipeline"
```

## Stage 3B completion gate

Required evidence:

- Codex SDK traffic is routed through scoped gateway instead of master credential in worker,
- bridge session can resume within task,
- provider failures are infrastructure failures,
- Kimi/DeepSeek structured output is schema validated,
- context packets are commit-aware/minimal,
- durable memory requires evidence/accepted decisions,
- reviewers cannot inherit implementer transcript,
- false model findings can be rejected by reproduction,
- confirmed findings create repair work,
- escalation is bounded and changes strategy,
- no model output directly marks requirement/release/run success.
