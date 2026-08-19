# Stage 3 Agent, Context, and Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Connect InfiniteInterns to real coding/review models while preserving typed contracts, fresh reviewer contexts, reproducible findings, and deterministic routing authority.

**Architecture:** Python owns a provider-neutral `AgentBackend` abstract interface. Codex runs through a small TypeScript `@openai/codex-sdk` JSONL bridge inside task workers. Kimi and DeepSeek are accessed through a model gateway using OpenAI-compatible APIs. The context builder emits task-specific packets; reviewers receive independent cold packets; model output is schema-validated before routing.

**Tech Stack:** Stage 2 stack plus TypeScript/Node 22, `@openai/codex-sdk`, httpx/OpenAI-compatible HTTP, Pydantic JSON schemas.

**Spec:** `docs/architecture/infinite-interns-design.md`

## Global Constraints

- Provider responses never directly transition task, requirement, release, or run authority states.
- Reviewer contexts never include the implementer's reasoning transcript.
- Agent-to-agent handoff uses typed artifacts and Git/evidence references.
- Codex may persist a session within one task; task and reviewer boundaries create fresh contexts.
- Kimi/DeepSeek output is advisory until reproduced or explicitly dispositioned.
- Provider failure is infrastructure failure unless executable evidence proves an engineering defect.

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
                "claim": "auth bypass",
            }
        )
```

- [ ] **Step 2: Implement strict Pydantic schemas**

Define frozen `AgentRequest`, `AgentTurn`, `AgentSession`, `UsageRecord`, `ReviewFinding`, `AgentResult`, `DecisionCandidate`, `MemoryCandidate`, and `Blocker`. `ReviewFinding` includes `finding_id`, optional `requirement_id`, `severity`, `confidence`, `claim`, `reproduction_strategy`, `affected_paths`, and `evidence_refs`.

- [ ] **Step 3: Implement an abstract backend with non-placeholder method bodies**

```python
# src/infinite_interns/agents/base.py
from abc import ABC, abstractmethod

from .schemas import AgentRequest, AgentResult, AgentSession, AgentTurn


class AgentBackend(ABC):
    @abstractmethod
    async def start(self, request: AgentRequest) -> AgentSession:
        raise NotImplementedError

    @abstractmethod
    async def run(self, session: AgentSession, request: AgentTurn) -> AgentResult:
        raise NotImplementedError

    @abstractmethod
    async def close(self, session: AgentSession) -> None:
        raise NotImplementedError
```

- [ ] **Step 4: Run and commit**

```bash
uv run pytest tests/unit/agents/test_schemas.py -q
uv run pyright
git add src/infinite_interns/agents tests/unit/agents
git commit -m "feat: define typed agent backend contracts"
```

### Task 2: Build the Codex SDK JSONL bridge

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
- Stdin/stdout protocol is one JSON object per line.
- Request operations are `start`, `run`, `resume`, `close`, and `ping`.
- Every response contains `request_id`, `ok`, and exactly one of `result` or `error`.
- Python `CodexBackend` implements `AgentBackend` without parsing human-readable terminal output.

- [ ] **Step 1: Define bridge protocol types**

```ts
export type BridgeRequest =
  | { request_id: string; op: "ping" }
  | { request_id: string; op: "start"; cwd: string; prompt: string }
  | { request_id: string; op: "run"; session_id: string; prompt: string }
  | { request_id: string; op: "resume"; session_id: string }
  | { request_id: string; op: "close"; session_id: string };

export type BridgeResponse =
  | { request_id: string; ok: true; result: unknown }
  | { request_id: string; ok: false; error: { code: string; message: string } };
```

- [ ] **Step 2: Add SDK/tooling and lock dependencies**

Use Node 22, install `@openai/codex-sdk`, TypeScript, and the chosen test runner. Commit `package-lock.json` and make `npm ci` the reproducible install path.

- [ ] **Step 3: Implement bridge process**

`start` creates a Codex thread in the requested worktree and returns its durable session/thread ID. `run` executes one turn on that session. `resume` verifies/reloads the SDK session identifier. `close` releases local bridge state. All protocol output goes to stdout as JSONL; diagnostics go to stderr.

- [ ] **Step 4: Write Node protocol tests with a fake SDK adapter**

Assert fragmented stdin lines are buffered correctly, malformed JSON returns a typed error, request IDs remain paired with responses, and `resume` returns the original fake session.

- [ ] **Step 5: Implement Python bridge client**

Use `asyncio.create_subprocess_exec` with explicit argv. Maintain a pending-request map keyed by `request_id`, parse only JSONL stdout, and persist the returned Codex session/thread ID in attempt metadata.

- [ ] **Step 6: Run bridge tests and commit**

```bash
cd bridge/codex
npm ci
npm test
cd ../..
uv run pytest tests/integration/agents/test_codex_bridge_fake.py -q
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
- `issue_gateway_token(capability: GatewayCapability, signing_key: bytes) -> str`.
- Gateway verifies current lease epoch before proxying provider traffic.
- Master provider keys are loaded only by the gateway process.

- [ ] **Step 1: Write expired/stale token tests**

```python
async def test_stale_epoch_token_is_rejected(client, stale_token: str) -> None:
    response = await client.post(
        "/v1/proxy/openai",
        headers={"Authorization": f"Bearer {stale_token}"},
        json={"model": "allowed-model", "messages": [{"role": "user", "content": "ping"}]},
    )
    assert response.status_code == 403
```

- [ ] **Step 2: Implement signed short-lived capabilities**

Encode a canonical JSON payload and sign it with HMAC-SHA256. Payload contains run/task/attempt/lease epoch, exact allowed providers/models, and expiry; it contains no provider secret.

- [ ] **Step 3: Implement provider/model allowlists**

A Kimi-only capability cannot call DeepSeek/OpenAI. A capability for one model cannot switch models. Before proxying, query current task lease epoch from the control-plane service/repository and reject stale capabilities.

- [ ] **Step 4: Add redacted gateway logging**

Log provider, model, latency, usage/cost metadata, run/task/attempt IDs, and status. Never persist Authorization values, capability token bodies, prompt secrets, or master provider keys.

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
- `DeepSeekBackend` defaults to `deepseek-v4-pro` with configured high reasoning/thinking.
- Both normalize provider responses to `AgentResult`/`ReviewFinding`.

- [ ] **Step 1: Write HTTP contract tests with `httpx.MockTransport`**

Assert Kimi requests use `https://api.kimi.com/coding/v1`, DeepSeek requests use `https://api.deepseek.com`, and 429/5xx/provider timeout maps to `ProviderUnavailable` rather than `ENGINEERING_FAILURE`.

- [ ] **Step 2: Implement shared OpenAI-compatible transport**

Create a transport that accepts `base_url`, gateway token, model, JSON schema, timeout, and request metadata. Parse response JSON into Pydantic. If content fails schema validation, allow exactly one schema-repair request and persist both attempt metadata records.

- [ ] **Step 3: Implement provider defaults**

Kimi uses `k3-256k` normally and `k3` only when `large_context=True`. DeepSeek uses `deepseek-v4-pro` and explicit provider request fields for high reasoning/thinking supported by the adapter contract.

- [ ] **Step 4: Run and commit**

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
- `ContextPacket` contains role, objective, success conditions, requirement refs, architecture refs, protected paths, relevant paths, dependency outputs, current failures, available tools, required evidence, deadline, budget, and `generated_at_commit`.
- `ContextBuilder.build(task_id: TaskId, role: AgentRole, commit: str) -> ContextPacket`.
- `ContextBuilder.is_fresh(packet: ContextPacket, current_commit: str) -> bool`.

- [ ] **Step 1: Write minimal-context test**

Create a fixture repository where a task affects `src/search/**`. Assert unrelated `docs/payments.md` and `src/payments/**` are absent from the initial packet, while the mapped search files and requirement are present.

- [ ] **Step 2: Write freshness test**

Generate a packet at commit A, change a relevant source file at commit B, and assert `is_fresh(packet, B)` is false. Change only an unrelated documentation file and assert the packet remains usable if its referenced inputs are unchanged.

- [ ] **Step 3: Implement repository map**

Index paths, detected language/module role, direct imports where parseable, test/source relation by naming/path convention, requirement/file links from task/evidence metadata, and architecture refs. Unsupported language parsers fall back to deterministic path/text indexing.

- [ ] **Step 4: Implement progressive packet builder**

Initial packet contains summaries/references, not raw large logs or entire repository bodies. Large observations remain artifact URIs; expose explicit lookup methods for file excerpts, artifact slices, and related decisions.

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
- `PromptRef(name: str, version: str, sha256: str)`.
- `PromptRegistry.load(name: str) -> PromptTemplate`.
- Reviewer renderer accepts only `ReviewerContext`, which intentionally has no implementer-transcript field.

- [ ] **Step 1: Write reviewer isolation test**

Pass a dictionary containing `implementer_transcript` to `ReviewerContext.model_validate`. Expected: `ValidationError` because models use `extra="forbid"`.

- [ ] **Step 2: Write concise role contracts**

Implementer prompt: inspect before editing, satisfy supplied task, run deterministic local QA, create coherent candidate commit, and never claim a requirement is verified.

Reviewer prompt: inspect original requirement, candidate diff, repository, and evidence; produce only typed blocker/advisory findings with reproduction strategy; do not rely on author reasoning.

Adversary prompt: search for behavioral/security/integration gaps and return structured candidate findings.

Diagnostician prompt: analyze repeated failure evidence and propose a materially different root-cause/repair strategy.

- [ ] **Step 3: Hash/version prompts**

Load prompt bytes, require a version header, compute SHA-256, and include `PromptRef` in every model-call metadata record.

- [ ] **Step 4: Run and commit**

```bash
uv run pytest tests/unit/agents/test_prompting.py -q
git add prompts src/infinite_interns/agents/prompting.py tests/unit/agents/test_prompting.py
git commit -m "feat: add versioned isolated agent role prompts"
```

### Task 7: Implement review tiers and reproduction routing

**Files:**
- Create: `src/infinite_interns/agents/routing.py`
- Create: `src/infinite_interns/review/service.py`
- Create: `src/infinite_interns/review/reproduction.py`
- Test: `tests/unit/agents/test_routing.py`
- Test: `tests/integration/agents/test_review_reproduction.py`

**Interfaces:**
- `ReviewTier`: `STANDARD`, `IMPORTANT`, `CRITICAL`.
- `RoutingPolicy.for_task(features: TaskFeatures) -> ReviewPlan`.
- `ReproductionService.enqueue(finding: ReviewFinding) -> ReproductionTask`.
- Finding dispositions: `PENDING`, `CONFIRMED`, `NOT_REPRODUCED`, `ADVISORY`.

- [ ] **Step 1: Write routing tests**

Authentication, authorization, migration, and security-sensitive tasks route to `CRITICAL`. Low-risk narrow changes route to `STANDARD`. Two semantically similar failures trigger a diagnostician escalation.

- [ ] **Step 2: Implement deterministic router**

Router input is task metadata only: risk, touched domains, migration flag, external integration flag, failure count, estimated context size. Models never choose their own review tier.

- [ ] **Step 3: Write false-positive reproduction test**

Synthetic reviewer claims `GET /health` returns 500; deterministic reproduction receives 200. Assert finding becomes `NOT_REPRODUCED` and no repair task is created.

- [ ] **Step 4: Write confirmed-defect reproduction test**

Synthetic reviewer claims user B can read user A's record; fixture receives 200 instead of 403. Assert finding becomes `CONFIRMED`, evidence is attached, and one repair task is created.

- [ ] **Step 5: Run and commit**

```bash
uv run pytest tests/unit/agents/test_routing.py tests/integration/agents/test_review_reproduction.py -q
git add src/infinite_interns/agents/routing.py src/infinite_interns/review tests
git commit -m "feat: turn model review claims into reproducible work"
```

### Task 8: Wire task-local implement/review/repair into orchestration

**Files:**
- Modify: `src/infinite_interns/graph/nodes.py`
- Modify: `src/infinite_interns/scheduler/service.py`
- Create: `src/infinite_interns/agents/worker_service.py`
- Create: `tests/integration/agents/test_stage3_acceptance.py`
- Modify: `README.md`
- Modify: `AGENTS.md`

**Interfaces:**
- `WorkerService.execute_task(attempt: AttemptRecord) -> CandidateResult`.
- Same Codex session may handle implementation and task-local repair.
- Reviewer invocation always creates a new session/request with `ReviewerContext`.

- [ ] **Step 1: Build seeded-defect fixture repository**

Fixture contains one API validation defect, a deterministic visible test command, a hidden reproduction script, and unrelated passing tests.

- [ ] **Step 2: Exercise implementation/fix cycle**

CI uses a deterministic fake backend applying the known patch. Provider opt-in test uses the real Codex bridge. In both modes, the worker result is a candidate commit and deterministic QA evidence, not a verified requirement.

- [ ] **Step 3: Assert fresh reviewer context**

Capture backend requests and assert the implementation session ID is absent from reviewer metadata/content. Reviewer gets requirement, diff, repository refs, and current evidence only.

- [ ] **Step 4: Inject one false and one true reviewer finding**

Assert only the reproduced true defect creates repair work. After repair, rerun deterministic QA and a fresh review according to the routing tier.

- [ ] **Step 5: Run stage gate and commit**

```bash
uv run ruff check .
uv run pyright
uv run pytest tests/unit/agents tests/unit/context -q
uv run pytest tests/integration/agents -q
cd bridge/codex
npm test
cd ../..
git add src tests prompts bridge README.md AGENTS.md
git commit -m "feat: complete typed multi-model worker pipeline"
```

## Stage 3 completion gate

Required evidence:

- Codex bridge protocol is structured and resumable at task scope,
- provider failures are infrastructure failures,
- Kimi/DeepSeek responses are schema validated,
- context packets are commit-aware and minimal,
- reviewer contexts cannot contain implementer reasoning fields,
- false-positive findings can be rejected by reproduction,
- confirmed findings create repair work,
- no provider/model output directly marks requirement or release success.
