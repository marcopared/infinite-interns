# Stage 3A Specification and Planning Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn a raw product request plus repository baseline into versioned requirements, acceptance-oracle drafts, architecture, a dependency-safe task DAG, and an audited traceability graph before any implementation worker is eligible to run.

**Architecture:** Specification, test architecture, architecture planning, and task decomposition are separate fresh-agent roles behind typed services. Product request history is immutable and revisions create new spec versions. A deterministic readiness gate requires an accepted current spec, accepted oracle draft, architecture artifact, acyclic task DAG, and cross-artifact audit before tasks become schedulable.

**Tech Stack:** Stages 1-2 plus the typed model backend contracts introduced at the beginning of Stage 3B. For CI this plan uses deterministic fake agent backends; real Codex wiring is completed in Stage 3B.

**Spec:** `docs/architecture/infinite-interns-design.md`

## Global Constraints

- Original product input is immutable history.
- Requirement IDs are stable across non-semantic revisions; deleted/replaced requirements retain lineage.
- Requirements, journeys, invariants, NFRs, constraints, and assumptions are typed artifacts.
- Low-risk assumptions may be chosen automatically; medium-risk assumptions must be reversible and recorded; high-risk irreversible choices require a safe alternative or explicit interrupt.
- Acceptance-oracle drafts are produced before implementation eligibility.
- Planner output cannot mark any requirement verified.
- Every planned task maps to at least one requirement or architecture/release necessity.
- Every required requirement maps to at least one acceptance criterion and one planned implementation/verification path.
- Cross-artifact audit must be clean before any implementation task becomes READY.

---

## File structure added by this plan

```text
src/infinite_interns/
  specification/
    models.py
    versions.py
    compiler.py
    assumptions.py
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
- `TraceabilityGraph` stores requirement -> criteria -> oracle gate -> task -> commit/evidence refs.

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

Define enums for requirement kind (`functional`, `nfr`, `constraint`) and assumption risk/disposition. `Requirement.acceptance_criteria` is a non-empty tuple for required functional requirements. High-risk assumptions validate that disposition is `needs_operator` or `safe_alternative`.

- [ ] **Step 3: Implement traceability graph invariants**

`TraceabilityGraph.validate()` reports:

```text
REQUIREMENT_WITHOUT_CRITERIA
REQUIREMENT_WITHOUT_ORACLE
REQUIREMENT_WITHOUT_TASK
TASK_WITHOUT_JUSTIFICATION
UNKNOWN_REFERENCE
```

Release-only infrastructure tasks may use explicit justification kind `architecture` or `release` instead of a product requirement.

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

- [ ] **Step 2: Add database fields**

`ii.spec_versions` stores `version_id`, `run_id`, `parent_version_id`, `product_input_id`, `content_hash`, `artifact_uri`, `created_at`. `ii.requirements` adds `spec_version_id`, `source_input_id`, and nullable `supersedes_requirement_id` while preserving stable requirement ID semantics.

- [ ] **Step 3: Implement content hashing and version service**

Canonicalize `ProductSpec.model_dump(mode="json")` with sorted JSON keys and SHA-256 it before persistence. A revision writes a new immutable artifact and row; it never updates old spec content.

- [ ] **Step 4: Verify and commit**

```bash
uv run alembic upgrade head
uv run pytest tests/integration/planning/test_spec_versions.py -q
git add migrations src/infinite_interns/db src/infinite_interns/specification/versions.py tests/integration/planning/test_spec_versions.py
git commit -m "feat: persist immutable specification lineage"
```

### Task 3: Implement Spec Compiler service with structured output

**Files:**
- Create: `src/infinite_interns/agents/planning_contracts.py`
- Create: `src/infinite_interns/specification/compiler.py`
- Create: `src/infinite_interns/specification/service.py`
- Create: `prompts/spec-compiler.md`
- Create: `tests/unit/specification/test_compiler.py`

**Interfaces:**
- `PlanningAgent.generate(role: PlanningRole, context: PlanningContext, schema: type[T]) -> T`.
- `SpecCompiler.compile(product_input, baseline) -> ProductSpecDraft`.
- `SpecificationService.compile_and_store(run_id, product_input, baseline) -> ProductSpec`.

- [ ] **Step 1: Write compiler contract test with fake planning agent**

Fake returns one journey and two requirements with stable IDs `REQ-AUTH-001` and `REQ-JOBS-001`. Assert the service rejects output with duplicate IDs or missing acceptance criteria and accepts the valid draft.

- [ ] **Step 2: Implement planning-agent abstraction**

Create a small abstract interface separate from SWE `AgentBackend`; it accepts a role/context/schema and returns schema-validated structured output. Stage 3B adapts Codex to this interface. Unit tests use a deterministic fake.

- [ ] **Step 3: Write Spec Compiler role contract**

Prompt requires extraction of requirements, user journeys, invariants, NFRs, constraints, glossary terms, and explicit assumptions. It forbids implementation/task creation and forbids weakening the original request.

- [ ] **Step 4: Implement compiler validation**

Reject duplicate IDs, empty required criteria, contradictory duplicate requirements with the same ID, and high-risk assumptions marked auto-accepted. Run assumption policy after schema validation.

- [ ] **Step 5: Verify and commit**

```bash
uv run pytest tests/unit/specification/test_compiler.py -q
git add src/infinite_interns/agents/planning_contracts.py src/infinite_interns/specification prompts/spec-compiler.md tests/unit/specification/test_compiler.py
git commit -m "feat: compile product input into typed requirements"
```

### Task 4: Implement independent Test Architect and oracle draft

**Files:**
- Create: `src/infinite_interns/planning/test_architect.py`
- Create: `prompts/test-architect.md`
- Create: `tests/unit/planning/test_test_architect.py`

**Interfaces:**
- `AcceptanceCriterion(criterion_id, requirement_id, given, when, then, critical)`.
- `OracleGateDraft(gate_id, requirement_id, level, scenario, expected_observations, critical)`.
- `TestArchitect.design(spec: ProductSpec, baseline: BaselineSummary) -> OracleDraft`.

- [ ] **Step 1: Write coverage test**

Create a spec with three required functional requirements. Fake Test Architect omits one requirement. Assert `OracleDraft.validate_coverage(spec)` returns `REQ_WITHOUT_ORACLE` and planning readiness remains false.

- [ ] **Step 2: Implement Test Architect role contract**

The role sees accepted spec and baseline, not implementation output. It creates E1-E5 gate drafts as appropriate, including persistence/relogin/restart observations for durable behaviors and access-control negative cases for authorization behavior.

- [ ] **Step 3: Implement deterministic coverage validator**

Every required requirement must have at least one mandatory gate; critical requirements require at least one runtime/integration gate (`E2` or above), unless the requirement is provably static and explicitly classified that way.

- [ ] **Step 4: Verify and commit**

```bash
uv run pytest tests/unit/planning/test_test_architect.py -q
git add src/infinite_interns/planning/test_architect.py prompts/test-architect.md tests/unit/planning/test_test_architect.py
git commit -m "feat: design acceptance oracle before implementation"
```

### Task 5: Implement Architect and architecture artifact

**Files:**
- Create: `src/infinite_interns/planning/architecture.py`
- Create: `prompts/architect.md`
- Create: `tests/unit/planning/test_architecture.py`

**Interfaces:**
- `ArchitectureArtifact(architecture_id, spec_version_id, components, data_flows, boundaries, persistence, external_integrations, security_constraints, decisions)`.
- `ArchitectService.design(spec, baseline, oracle_draft) -> ArchitectureArtifact`.

- [ ] **Step 1: Write architecture validation test**

A spec requiring durable saved searches must be rejected if an architecture draft contains no persistence component/data flow for that requirement mapping.

- [ ] **Step 2: Write role contract**

Architect must reuse brownfield architecture when compatible, name new/changed components, map requirements to components, declare datastore/migration implications, identify high-risk changes, and record decisions. It may not mark requirements complete.

- [ ] **Step 3: Implement deterministic structural validation**

Validate referenced requirement IDs exist, all critical requirements have at least one component mapping, external integrations have explicit boundary/policy fields, and architecture ID is bound to current spec version.

- [ ] **Step 4: Verify and commit**

```bash
uv run pytest tests/unit/planning/test_architecture.py -q
git add src/infinite_interns/planning/architecture.py prompts/architect.md tests/unit/planning/test_architecture.py
git commit -m "feat: produce requirement-linked architecture"
```

### Task 6: Implement task planner and dependency DAG persistence

**Files:**
- Create: `src/infinite_interns/planning/task_planner.py`
- Create: `prompts/task-planner.md`
- Modify: `src/infinite_interns/db/repositories.py`
- Test: `tests/unit/planning/test_task_planner.py`
- Test: `tests/integration/planning/test_task_dag_persistence.py`

**Interfaces:**
- `TaskDraft(task_id, title, requirement_ids, architecture_refs, dependencies, risk, verification_gate_ids, exclusive_resources)`.
- `TaskPlanner.plan(spec, architecture, oracle) -> TaskPlan`.
- Task plan is converted to Stage 2 `TaskDag` and must be acyclic before persistence.

- [ ] **Step 1: Write decomposition and cycle tests**

Assert generated task with no requirement/architecture/release justification is rejected. Assert dependency cycle fails persistence. Assert independent frontend/backend tasks can remain dependency-independent when architecture allows parallel work.

- [ ] **Step 2: Write task-planner role contract**

Each task must be a coherent independently reviewable engineering unit, declare required verification gates, dependencies, risk, likely paths, and exclusive resources. It must not create speculative improvements without requirement/defect/security/release justification.

- [ ] **Step 3: Persist valid DAG**

Inside one transaction insert tasks and `ii.task_dependencies` only after `TaskDag.validate_acyclic()` and reference validation pass. Initial task state is `PLANNED`, never READY.

- [ ] **Step 4: Verify and commit**

```bash
uv run pytest tests/unit/planning/test_task_planner.py tests/integration/planning/test_task_dag_persistence.py -q
git add src/infinite_interns/planning/task_planner.py prompts/task-planner.md src/infinite_interns/db/repositories.py tests
git commit -m "feat: turn architecture into dependency-safe task plan"
```

### Task 7: Implement cross-artifact audit and planning readiness gate

**Files:**
- Create: `src/infinite_interns/planning/audit.py`
- Create: `src/infinite_interns/planning/readiness.py`
- Create: `prompts/cross-artifact-auditor.md`
- Create: `tests/unit/planning/test_audit.py`
- Create: `tests/integration/planning/test_stage3a_acceptance.py`

**Interfaces:**
- `AuditFinding(code, severity, artifact_refs, requirement_ids, claim)`.
- `CrossArtifactAuditor.audit(spec, oracle, architecture, task_plan) -> AuditReport`.
- `PlanningReadiness.evaluate(spec, oracle, architecture, task_plan, audit) -> PlanningReadinessResult`.
- Only a `READY` readiness result may transition dependency-eligible planned tasks to `TaskStatus.READY`.

- [ ] **Step 1: Write deterministic audit checks**

Include: unknown IDs, missing oracle coverage, missing task coverage, orphan task, architecture/task contradiction, task references unknown gate, critical requirement lacking runtime gate, and DAG cycle.

- [ ] **Step 2: Add independent semantic audit role**

After deterministic checks pass, fake/real auditor receives all four artifacts and may return additional typed contradiction/gap candidates. Blocking semantic findings keep readiness false until artifacts are revised/dispositioned.

- [ ] **Step 3: Write readiness acceptance test**

Start with raw product input and fake planning agents. Produce spec/oracle/architecture/task plan where one required requirement is omitted from tasks. Assert zero implementation tasks READY. Revise plan to cover it, run clean audit, assert only dependency-root tasks become READY.

- [ ] **Step 4: Verify and commit**

```bash
uv run ruff check .
uv run pyright
uv run pytest tests/unit/specification tests/unit/planning -q
uv run pytest tests/integration/planning -q
git add src/infinite_interns/planning prompts tests
git commit -m "feat: gate implementation on audited planning artifacts"
```

## Stage 3A completion gate

Required evidence:

- original product input is immutable,
- spec revisions preserve lineage,
- assumption policy rejects unsafe auto-decisions,
- required requirements have acceptance-oracle coverage before implementation,
- architecture maps critical requirements to concrete components/boundaries,
- task DAG is acyclic and every task is justified,
- cross-artifact audit catches omitted/contradictory coverage,
- no task becomes READY until planning readiness is clean.
