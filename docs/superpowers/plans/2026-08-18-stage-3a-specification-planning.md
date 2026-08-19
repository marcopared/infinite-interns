# Stage 3A Specification and Planning Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn a raw product request plus repository baseline into a reviewed versioned specification, acceptance-oracle draft, architecture, dependency-safe task DAG, and audited traceability graph before any implementation worker is eligible to run.

**Architecture:** Specification, independent critique/synthesis, test architecture, architecture planning, task decomposition, and cross-artifact audit are separate fresh-agent roles behind typed services. Product input history is immutable and every revision creates a new spec version. The Spec Compiler first creates a draft; Product, Architecture, and Testability critics independently challenge it; a Synthesizer either creates a new immutable revision or accepts the current version. Only then do Test Architect, Architect, and Task Planner produce downstream artifacts. A deterministic planning-readiness gate requires an accepted current spec, accepted oracle draft, architecture artifact, acyclic task DAG, traceability coverage, and clean cross-artifact audit before tasks become schedulable.

**Tech Stack:** Stages 1-2B plus Pydantic planning-agent contracts and deterministic fake planning backends for CI. Stage 3B binds these roles to real Codex/Kimi/DeepSeek provider adapters.

**Spec:** `docs/architecture/infinite-interns-design.md`

## Global Constraints

- Original product input is immutable history.
- Requirement IDs are stable across non-semantic revisions; replaced requirements retain explicit lineage.
- Requirements, journeys, invariants, NFRs, constraints, assumptions, criticisms, and dispositions are typed artifacts.
- Low-risk assumptions may be chosen automatically; medium-risk assumptions must be reversible and recorded; high-risk irreversible choices require a safe alternative or explicit interrupt.
- Independent critics start fresh and do not inherit the Spec Compiler's reasoning transcript.
- Acceptance-oracle drafts are produced before implementation eligibility.
- Planner/model output cannot mark any requirement verified.
- Every planned task maps to at least one requirement or explicit architecture/release necessity.
- Every required requirement maps to at least one acceptance criterion, oracle gate, and planned implementation/verification path.
- Cross-artifact audit must be clean before any implementation task becomes READY.

---

## File structure added by this stage

```text
src/infinite_interns/
  specification/
    models.py
    versions.py
    compiler.py
    assumptions.py
    review.py
    service.py
  planning/
    architecture.py
    test_architect.py
    task_planner.py
    traceability.py
    audit.py
    readiness.py
  agents/
    planning_contracts.py
prompts/
  spec-compiler.md
  product-critic.md
  architecture-critic.md
  testability-critic.md
  spec-synthesizer.md
  test-architect.md
  architect.md
  task-planner.md
  cross-artifact-auditor.md
tests/unit/specification/
tests/unit/planning/
tests/integration/planning/
```

### Task 1: Define specification, assumption, and traceability contracts

**Files:**
- Create: `src/infinite_interns/specification/models.py`
- Create: `src/infinite_interns/specification/assumptions.py`
- Create: `src/infinite_interns/planning/traceability.py`
- Create: `tests/unit/specification/test_models.py`
- Create: `tests/unit/planning/test_traceability.py`

**Interfaces:**
- `ProductInput(input_id, raw_text, source_ref, created_at)` is immutable.
- `Requirement(requirement_id, text, kind, criticality, acceptance_criteria, source_input_id, supersedes)`.
- `ProductSpec(version_id, parent_version_id, product_input_id, requirements, journeys, invariants, nfrs, constraints, assumptions, glossary)`.
- `Assumption(risk, statement, chosen_default, reversible, disposition)`.
- `TraceabilityGraph` stores requirement -> criterion -> oracle gate -> task -> commit/evidence refs.

- [ ] **Step 1: Write immutable-history and assumption tests**

```python
from pydantic import ValidationError
import pytest

from infinite_interns.specification.models import Assumption, AssumptionRisk, ProductInput


def test_product_input_is_frozen() -> None:
    item = ProductInput(input_id="input-1", raw_text="Build a job tracker", source_ref="cli")
    with pytest.raises(ValidationError):
        item.raw_text = "simpler request"


def test_high_risk_assumption_cannot_be_auto_accepted() -> None:
    with pytest.raises(ValidationError):
        Assumption(
            assumption_id="A-1",
            risk=AssumptionRisk.HIGH,
            statement="Delete production data during migration",
            chosen_default="delete it",
            reversible=False,
            disposition="auto_accepted",
        )
```

- [ ] **Step 2: Implement strict frozen Pydantic contracts**

Define enums for requirement kind (`functional`, `nfr`, `constraint`) and assumption risk/disposition. Required functional requirements have non-empty acceptance criteria. High-risk assumptions validate that disposition is `needs_operator` or `safe_alternative`.

- [ ] **Step 3: Implement traceability graph invariants**

`TraceabilityGraph.validate()` reports typed errors:

```text
REQUIREMENT_WITHOUT_CRITERIA
REQUIREMENT_WITHOUT_ORACLE
REQUIREMENT_WITHOUT_TASK
TASK_WITHOUT_JUSTIFICATION
UNKNOWN_REFERENCE
```

Release/infrastructure tasks may use explicit justification kind `architecture` or `release` instead of a product requirement.

- [ ] **Step 4: Run and commit**

```bash
uv run pytest tests/unit/specification tests/unit/planning/test_traceability.py -q
git add src/infinite_interns/specification src/infinite_interns/planning/traceability.py tests/unit/specification tests/unit/planning/test_traceability.py
git commit -m "feat: define versioned product and traceability contracts"
```

### Task 2: Persist immutable spec versions and requirement lineage

**Files:**
- Modify: `src/infinite_interns/db/models.py`
- Modify: `src/infinite_interns/db/repositories.py`
- Create: `migrations/versions/0003_specification_lineage.py`
- Create: `src/infinite_interns/specification/versions.py`
- Test: `tests/integration/planning/test_spec_versions.py`

**Interfaces:**
- `SpecVersionRepository.add(spec: ProductSpec) -> None` never mutates prior rows.
- `SpecVersionService.revise(parent_version_id, revision) -> ProductSpec` creates a new version.
- `RequirementLineage` preserves stable IDs and supersession links.

- [ ] **Step 1: Write immutability test**

Persist v1, revise one requirement into v2, then assert v1 serialized content/hash is unchanged and v2 references `parent_version_id=v1`.

- [ ] **Step 2: Add database fields/tables**

Add `ii.product_inputs`. `ii.spec_versions` stores `version_id`, `run_id`, `parent_version_id`, `product_input_id`, `content_hash`, `artifact_uri`, `review_status`, `created_at`. `ii.requirements` adds `spec_version_id`, `source_input_id`, nullable `supersedes_requirement_id` while preserving stable requirement identity semantics.

- [ ] **Step 3: Implement content hashing/version service**

Canonicalize `ProductSpec.model_dump(mode="json")` with sorted JSON keys and SHA-256 before persistence. Revision writes a new immutable artifact/row; it never edits previous spec content.

- [ ] **Step 4: Verify and commit**

```bash
uv run alembic upgrade head
uv run pytest tests/integration/planning/test_spec_versions.py -q
git add migrations src/infinite_interns/db src/infinite_interns/specification/versions.py tests/integration/planning/test_spec_versions.py
git commit -m "feat: persist immutable specification lineage"
```

### Task 3: Implement Spec Compiler with structured planning-agent interface

**Files:**
- Create: `src/infinite_interns/agents/planning_contracts.py`
- Create: `src/infinite_interns/specification/compiler.py`
- Create: `src/infinite_interns/specification/service.py`
- Create: `prompts/spec-compiler.md`
- Create: `tests/unit/specification/test_compiler.py`

**Interfaces:**
- `PlanningRole` enum covers spec compiler, critics, synthesizer, Test Architect, Architect, Task Planner, auditor.
- `PlanningAgent.generate(role: PlanningRole, context: PlanningContext, schema: type[T]) -> T`.
- `SpecCompiler.compile(product_input, baseline) -> ProductSpecDraft`.
- `SpecificationService.compile_and_store(run_id, product_input, baseline) -> ProductSpec`.

- [ ] **Step 1: Implement explicit abstract planning-agent contract**

```python
from abc import ABC, abstractmethod
from typing import TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class PlanningAgent(ABC):
    @abstractmethod
    async def generate(
        self,
        role: PlanningRole,
        context: PlanningContext,
        schema: type[T],
    ) -> T:
        raise NotImplementedError
```

CI uses `FakePlanningAgent` with role-keyed deterministic outputs; Stage 3B adds a Codex-backed adapter implementing this same interface.

- [ ] **Step 2: Write compiler contract test**

Fake returns one journey and requirements `REQ-AUTH-001` and `REQ-JOBS-001`. Assert duplicate IDs, empty required acceptance criteria, and high-risk auto-assumptions are rejected while valid draft is stored as immutable version.

- [ ] **Step 3: Write Spec Compiler role contract**

Prompt requires requirements, user journeys, invariants, NFRs, constraints, glossary, assumptions and explicit source linkage. It forbids task/implementation generation and forbids simplifying the raw product input because a feature seems difficult.

- [ ] **Step 4: Implement compiler validation/assumption policy**

Reject duplicate IDs, contradictory duplicate requirement content, empty critical behavior criteria, invalid source refs, and high-risk unsafe defaults. Apply low/medium/high assumption policy after schema validation.

- [ ] **Step 5: Verify and commit**

```bash
uv run pytest tests/unit/specification/test_compiler.py -q
git add src/infinite_interns/agents/planning_contracts.py src/infinite_interns/specification prompts/spec-compiler.md tests/unit/specification/test_compiler.py
git commit -m "feat: compile product input into typed specification"
```

### Task 4: Implement independent spec critics and synthesizer revision loop

**Files:**
- Create: `src/infinite_interns/specification/review.py`
- Create: `prompts/product-critic.md`
- Create: `prompts/architecture-critic.md`
- Create: `prompts/testability-critic.md`
- Create: `prompts/spec-synthesizer.md`
- Create: `tests/unit/specification/test_review.py`
- Create: `tests/integration/planning/test_spec_review_loop.py`

**Interfaces:**
- `CriticKind`: `PRODUCT`, `ARCHITECTURE`, `TESTABILITY`.
- `SpecCritique(critic_kind, findings, blocking)`.
- `SpecReviewFinding(code, severity, requirement_ids, claim, proposed_resolution)`.
- `SpecReviewReport(spec_version_id, critiques, disposition, next_version_id)`.
- `SpecReviewService.review_until_accepted(spec, baseline, max_revisions) -> AcceptedSpec`.

- [ ] **Step 1: Write fresh-context fanout test**

Inject fake planning backend recording requests. Assert three critic calls receive the same current spec/baseline but no Spec Compiler transcript and no other critic output. Each critic role has a distinct request/context ID.

- [ ] **Step 2: Write critic role contracts**

Product Critic: missing/ambiguous user behavior, contradictions, scope drift, unmet original intent.
Architecture Critic: infeasible/non-reversible constraints, missing system boundaries, brownfield compatibility risks, high-risk assumptions.
Testability Critic: unobservable criteria, vacuous/unverifiable requirements, missing negative/error/persistence cases.

Critics may identify gaps but cannot directly edit the spec.

- [ ] **Step 3: Write synthesizer contract**

Synthesizer receives raw immutable product input, current spec, three typed critiques, and baseline. It must return either:

```text
ACCEPT_CURRENT
```

or a `SpecRevision` whose changes explicitly cite critic finding IDs and preserve requirement/source lineage. It may not erase a blocking user requirement without an explicit supersession/change rationale allowed by policy.

- [ ] **Step 4: Implement bounded revision loop**

If any blocking critique remains, synthesizer creates vN+1 via `SpecVersionService`, critics rerun fresh against vN+1, and review continues up to configured `max_revisions` (default 5). If still blocked, run becomes planning-BLOCKED with critique evidence; it does not proceed to implementation.

- [ ] **Step 5: Write integration loop test**

v1 omits persistence after re-login. Testability Critic returns blocker; synthesizer creates v2 adding explicit persistence criterion; all critics accept v2. Assert v1 remains immutable, v2 lineage points to v1, final `AcceptedSpec.version_id == v2`, and downstream Test Architect receives v2 only.

- [ ] **Step 6: Verify and commit**

```bash
uv run pytest tests/unit/specification/test_review.py tests/integration/planning/test_spec_review_loop.py -q
git add src/infinite_interns/specification/review.py prompts tests
git commit -m "feat: challenge and synthesize specifications before planning"
```

### Task 5: Implement independent Test Architect and oracle draft

**Files:**
- Create: `src/infinite_interns/planning/test_architect.py`
- Create: `prompts/test-architect.md`
- Create: `tests/unit/planning/test_test_architect.py`

**Interfaces:**
- `AcceptanceCriterion(criterion_id, requirement_id, given, when, then, critical)`.
- `OracleGateDraft(gate_id, requirement_id, level, scenario, expected_observations, critical)`.
- `TestArchitect.design(accepted_spec: ProductSpec, baseline: BaselineSummary) -> OracleDraft`.

- [ ] **Step 1: Write oracle coverage test**

Create accepted spec with three required functional requirements. Fake Test Architect omits one. Assert `OracleDraft.validate_coverage(spec)` reports `REQ_WITHOUT_ORACLE` and planning readiness remains false.

- [ ] **Step 2: Write Test Architect role contract**

Role sees accepted spec/baseline, not implementation output. It creates E1-E5 gate drafts as appropriate, persistence/relogin/restart observations for durable state, access-control negative cases for authorization, and error-path observations for critical integrations.

- [ ] **Step 3: Implement deterministic coverage validator**

Every required requirement has at least one mandatory gate. Critical requirements require at least one integration/runtime gate (`E2+`) unless explicitly classified as static with a deterministic rationale.

- [ ] **Step 4: Verify and commit**

```bash
uv run pytest tests/unit/planning/test_test_architect.py -q
git add src/infinite_interns/planning/test_architect.py prompts/test-architect.md tests/unit/planning/test_test_architect.py
git commit -m "feat: design acceptance oracle before implementation"
```

### Task 6: Implement Architect and requirement-linked architecture artifact

**Files:**
- Create: `src/infinite_interns/planning/architecture.py`
- Create: `prompts/architect.md`
- Create: `tests/unit/planning/test_architecture.py`

**Interfaces:**
- `ArchitectureArtifact(architecture_id, spec_version_id, components, data_flows, boundaries, persistence, external_integrations, security_constraints, decisions, requirement_mappings)`.
- `ArchitectService.design(spec, baseline, oracle_draft) -> ArchitectureArtifact`.

- [ ] **Step 1: Write architecture validation test**

A spec requiring durable saved searches is rejected if architecture has no persistence component/data-flow mapping for that requirement.

- [ ] **Step 2: Write Architect role contract**

Architect reuses brownfield architecture when compatible, names new/changed components, maps requirements to components, declares datastore/migration implications, external trust boundaries, security constraints and high-risk decisions. It cannot mark requirements complete.

- [ ] **Step 3: Implement deterministic structural validation**

Validate all requirement IDs exist, all critical requirements have component mapping, external integrations have explicit boundary/policy fields, persistence-required requirements have datastore/data-flow mapping, and architecture is bound to current accepted spec version.

- [ ] **Step 4: Verify and commit**

```bash
uv run pytest tests/unit/planning/test_architecture.py -q
git add src/infinite_interns/planning/architecture.py prompts/architect.md tests/unit/planning/test_architecture.py
git commit -m "feat: produce requirement-linked architecture"
```

### Task 7: Implement task planner and dependency DAG persistence

**Files:**
- Create: `src/infinite_interns/planning/task_planner.py`
- Create: `prompts/task-planner.md`
- Modify: `src/infinite_interns/db/repositories.py`
- Create: `tests/unit/planning/test_task_planner.py`
- Create: `tests/integration/planning/test_task_dag_persistence.py`

**Interfaces:**
- `TaskDraft(task_id, title, requirement_ids, architecture_refs, dependencies, risk, verification_gate_ids, exclusive_resources)`.
- `TaskPlanner.plan(spec, architecture, oracle) -> TaskPlan`.
- `TaskPlan` converts to Stage 2 `TaskDag` and must validate acyclic before persistence.

- [ ] **Step 1: Write decomposition/cycle tests**

Task with no requirement/architecture/release justification is rejected. Dependency cycle fails persistence. Independent tasks remain independent where architecture has no true dependency.

- [ ] **Step 2: Write task-planner role contract**

Each task is a coherent independently reviewable engineering unit, declares required verification gates, dependencies, risk, likely paths and exclusive resources. It may not create speculative features/refactors without requirement, reproduced defect, security, or release justification.

- [ ] **Step 3: Persist valid DAG**

Inside one transaction insert tasks and `ii.task_dependencies` only after reference validation and `TaskDag.validate_acyclic()`. Initial task state is `PLANNED`, never READY.

- [ ] **Step 4: Verify and commit**

```bash
uv run pytest tests/unit/planning/test_task_planner.py tests/integration/planning/test_task_dag_persistence.py -q
git add src/infinite_interns/planning/task_planner.py prompts/task-planner.md src/infinite_interns/db/repositories.py tests
git commit -m "feat: turn architecture into dependency-safe task plan"
```

### Task 8: Implement cross-artifact audit and planning readiness gate

**Files:**
- Create: `src/infinite_interns/planning/audit.py`
- Create: `src/infinite_interns/planning/readiness.py`
- Create: `prompts/cross-artifact-auditor.md`
- Create: `tests/unit/planning/test_audit.py`
- Create: `tests/integration/planning/test_stage3a_acceptance.py`

**Interfaces:**
- `AuditFinding(code, severity, artifact_refs, requirement_ids, claim)`.
- `CrossArtifactAuditor.audit(spec, oracle, architecture, task_plan) -> AuditReport`.
- `PlanningReadiness.evaluate(spec_review, oracle, architecture, task_plan, audit) -> PlanningReadinessResult`.
- Only `READY` may transition dependency-root PLANNED tasks to `TaskStatus.READY`.

- [ ] **Step 1: Implement deterministic audit checks**

Include unknown IDs, current spec not review-accepted, missing oracle coverage, missing task coverage, orphan task, architecture/task contradiction, task references unknown gate, critical requirement lacks runtime gate, traceability break and DAG cycle.

- [ ] **Step 2: Add independent semantic cross-artifact auditor**

After deterministic checks pass, fresh auditor receives accepted spec, oracle, architecture, task plan and baseline; it may return typed contradiction/gap candidates. Blocking semantic findings keep readiness false until artifacts are revised/dispositioned. Auditor cannot mutate artifacts directly.

- [ ] **Step 3: Write readiness acceptance test**

Start raw product input and deterministic fake planning agents. First task plan omits one accepted required requirement: assert zero implementation tasks READY. Revised plan covers it, audit becomes clean: assert only dependency-root tasks transition to READY.

- [ ] **Step 4: Run Stage 3A gate and commit**

```bash
uv run ruff check .
uv run pyright
uv run pytest tests/unit/specification tests/unit/planning -q
uv run pytest tests/integration/planning -q
git add src/infinite_interns/planning src/infinite_interns/specification prompts tests
git commit -m "feat: gate implementation on reviewed planning artifacts"
```

## Stage 3A completion gate

Required evidence:

- original product input is immutable,
- spec revisions preserve lineage,
- assumption policy rejects unsafe auto-decisions,
- Product/Architecture/Testability critics run in independent contexts,
- blocking critiques force an immutable revision loop or honest planning-BLOCKED state,
- accepted current spec has acceptance-oracle coverage before implementation,
- architecture maps critical requirements to concrete components/boundaries,
- task DAG is acyclic and every task is justified,
- cross-artifact audit catches omitted/contradictory coverage,
- no task becomes READY until spec review and planning readiness are clean.
