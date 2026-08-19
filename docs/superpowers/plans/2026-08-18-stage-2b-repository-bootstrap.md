# Stage 2B Repository Bootstrap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish a reproducible brownfield or greenfield baseline before specification/planning so later agents know what repository, environment, existing failures, project rules, and runnable commands they are inheriting.

**Architecture:** Bootstrap is deterministic-first. It snapshots Git identity, inspects repository structure and configured/detected commands, records project guidance, executes bounded baseline verification, and stores a typed `BaselineSummary`. Brownfield failures are recorded as pre-existing evidence rather than silently attributed to new work. Empty/greenfield repos receive a minimal Git baseline but no speculative application architecture before the specification phase.

**Tech Stack:** Stages 1-2 plus Git CLI, filesystem inspection, command verification adapter shell established here in minimal form and generalized in Stage 4.

**Spec:** `docs/architecture/infinite-interns-design.md`

## Global Constraints

- Bootstrap never edits an existing brownfield application's production source.
- Pre-existing failures remain distinguishable from regressions introduced by InfiniteInterns.
- Greenfield bootstrap creates repository/control metadata only; product architecture is decided after spec acceptance.
- Current base commit is recorded before any autonomous implementation work.
- Project guidance such as `AGENTS.md` is treated as repository guidance, not higher authority than factory security/completion policies.
- Baseline commands are explicit and provenance-recorded; unbounded arbitrary discovery scripts are not executed.

---

## File structure added by this stage

```text
src/infinite_interns/
  bootstrap/
    models.py
    repository.py
    commands.py
    service.py
  context/
    guidance.py
tests/unit/bootstrap/
tests/integration/bootstrap/
```

### Task 1: Define baseline and repository inspection contracts

**Files:**
- Create: `src/infinite_interns/bootstrap/models.py`
- Create: `tests/unit/bootstrap/test_models.py`

**Interfaces:**
- `RepositoryKind`: `BROWNFIELD`, `GREENFIELD`.
- `CommandKind`: `INSTALL`, `BUILD`, `TYPECHECK`, `LINT`, `UNIT`, `INTEGRATION`, `START`.
- `DetectedCommand(kind, argv, source, confidence)`.
- `BaselineFailure(failure_id, command_kind, exit_code, summary, artifact_uri)`.
- `BaselineSummary(repo_kind, base_commit, default_branch, languages, package_managers, guidance_refs, commands, failures, architecture_hints, dependency_hints, generated_at)`.

- [ ] **Step 1: Write strict model tests**

```python
from pydantic import ValidationError
import pytest

from infinite_interns.bootstrap.models import DetectedCommand


def test_command_argv_must_be_nonempty() -> None:
    with pytest.raises(ValidationError):
        DetectedCommand(kind="build", argv=(), source="config", confidence=1.0)
```

- [ ] **Step 2: Implement frozen Pydantic models**

Command argv is a tuple of tokens, never one shell string. Confidence is constrained to 0-1. `BaselineFailure` stores artifact refs, not raw giant logs.

- [ ] **Step 3: Verify and commit**

```bash
uv run pytest tests/unit/bootstrap/test_models.py -q
git add src/infinite_interns/bootstrap/models.py tests/unit/bootstrap/test_models.py
git commit -m "feat: define repository baseline contracts"
```

### Task 2: Detect brownfield versus greenfield and snapshot Git state

**Files:**
- Create: `src/infinite_interns/bootstrap/repository.py`
- Create: `tests/unit/bootstrap/test_repository.py`

**Interfaces:**
- `RepositoryInspector.inspect(path: Path) -> RepositorySnapshot`.
- Brownfield requires existing tracked product content or existing commits beyond factory metadata.
- Greenfield may be an empty directory or Git repo containing only control/docs bootstrap files.

- [ ] **Step 1: Write classification tests**

Cases: empty directory -> GREENFIELD; repo with only README/control docs -> GREENFIELD; repo with application/package source -> BROWNFIELD; dirty brownfield repo -> rejected by default with `DirtyRepositoryError` unless explicit snapshot policy is configured.

- [ ] **Step 2: Implement Git snapshot commands**

Use explicit argv:

```text
git -C <repo> rev-parse --is-inside-work-tree
git -C <repo> rev-parse HEAD
git -C <repo> status --porcelain=v1
git -C <repo> branch --show-current
```

For a non-Git empty greenfield directory, initialize `git init -b main`, create only `.gitignore`/factory metadata required by bootstrap, and create a baseline commit before planning.

- [ ] **Step 3: Verify and commit**

```bash
uv run pytest tests/unit/bootstrap/test_repository.py -q
git add src/infinite_interns/bootstrap/repository.py tests/unit/bootstrap/test_repository.py
git commit -m "feat: classify and snapshot workload repositories"
```

### Task 3: Discover project guidance and bounded runnable commands

**Files:**
- Create: `src/infinite_interns/context/guidance.py`
- Create: `src/infinite_interns/bootstrap/commands.py`
- Create: `tests/unit/bootstrap/test_commands.py`
- Create: `tests/unit/bootstrap/test_guidance.py`

**Interfaces:**
- Guidance discovery reads `AGENTS.md`, `CONTRIBUTING.md`, build manifests, test config, and explicitly configured docs.
- `CommandDetector.detect(repo, config) -> tuple[DetectedCommand, ...]`.
- Operator config overrides heuristics.

- [ ] **Step 1: Write command-detection fixtures**

Fixtures for Python/uv, Node/pnpm, and mixed repo. Assert detected argv uses `uv run pytest`, `pnpm test`, or configured commands only when supporting manifest/config exists.

- [ ] **Step 2: Implement deterministic detection table**

Examples:

```text
pyproject.toml + uv.lock       -> uv sync --frozen
pytest config/dependency       -> uv run pytest
package.json + pnpm-lock.yaml  -> pnpm install --frozen-lockfile
package.json build script      -> pnpm run build
```

Never execute a README code block merely because it exists. Guidance text is surfaced to later context but commands are executable only if configured or matched by explicit safe detector rules.

- [ ] **Step 3: Hash guidance artifacts**

Store path, commit SHA, content SHA-256, and trust label `REPOSITORY_CONTENT`; later context packets can detect drift.

- [ ] **Step 4: Verify and commit**

```bash
uv run pytest tests/unit/bootstrap/test_commands.py tests/unit/bootstrap/test_guidance.py -q
git add src/infinite_interns/bootstrap/commands.py src/infinite_interns/context/guidance.py tests/unit/bootstrap tests/unit/bootstrap/test_guidance.py
git commit -m "feat: discover bounded project guidance and commands"
```

### Task 4: Run brownfield baseline and record pre-existing failures

**Files:**
- Create: `src/infinite_interns/bootstrap/service.py`
- Create: `tests/integration/bootstrap/test_brownfield_baseline.py`

**Interfaces:**
- `BootstrapService.run(repo, run_id, settings) -> BaselineSummary`.
- Baseline executes configured/detected install/build/type/lint/unit commands with timeouts and artifact capture.
- Failure identity includes base commit + command kind + normalized failure signature.

- [ ] **Step 1: Build brownfield fixture with one known existing failure**

Fixture repository contains two tests, one passing and one known failing before InfiniteInterns work. Record fixture base SHA.

- [ ] **Step 2: Implement bounded execution**

Run command argv without shell interpolation, enforce configured timeout, store stdout/stderr in artifact store, summarize exit status into `BaselineFailure`, and continue independent baseline checks where safe.

- [ ] **Step 3: Assert baseline failure provenance**

Failure must include the original base SHA and be marked `pre_existing=True`. Later regression attribution can compare failure signature against this baseline.

- [ ] **Step 4: Verify and commit**

```bash
uv run pytest tests/integration/bootstrap/test_brownfield_baseline.py -q
git add src/infinite_interns/bootstrap/service.py tests/integration/bootstrap
git commit -m "feat: record brownfield baseline before autonomous work"
```

### Task 5: Run greenfield baseline without inventing product design

**Files:**
- Create: `tests/integration/bootstrap/test_greenfield_baseline.py`

**Interfaces:**
- Greenfield result contains base commit, empty/no-op product command set unless explicitly bootstrapped, no product architecture artifact, and no product requirements/tasks.

- [ ] **Step 1: Write greenfield acceptance test**

Start empty temp directory; bootstrap; assert Git repo/main/base commit exists; assert no `src/`, web framework, database schema, or product dependencies were invented; assert summary kind is GREENFIELD.

- [ ] **Step 2: Implement greenfield path in `BootstrapService`**

Create only factory-control-safe files needed for repository reproducibility (for example `.gitignore` entries for `.infinite-interns/` runtime data). Commit with `chore: initialize greenfield baseline`.

- [ ] **Step 3: Verify and commit**

```bash
uv run pytest tests/integration/bootstrap/test_greenfield_baseline.py -q
git add src/infinite_interns/bootstrap/service.py tests/integration/bootstrap/test_greenfield_baseline.py
git commit -m "feat: establish neutral greenfield baseline"
```

### Task 6: Wire BOOTSTRAP into parent graph before specification

**Files:**
- Modify: `src/infinite_interns/graph/factory.py`
- Modify: `src/infinite_interns/graph/nodes.py`
- Create: `tests/integration/bootstrap/test_stage2b_acceptance.py`
- Modify: `AGENTS.md`

**Interfaces:**
- Parent graph path becomes `START -> bootstrap -> specification_pending` for a new run.
- Bootstrap failure can produce `BLOCKED`/control-plane failure but never `DONE`.
- `FactoryState` stores `baseline_ref` rather than raw logs/source map.

- [ ] **Step 1: Write graph ordering test**

Use fake bootstrap/specification nodes and assert specification node is never invoked before bootstrap returns a persisted baseline ref.

- [ ] **Step 2: Wire real bootstrap service**

Persist `BaselineSummary` as artifact + compact DB/state ref, then route to Stage 3A specification entry node.

- [ ] **Step 3: Run Stage 2B gate and commit**

```bash
uv run ruff check .
uv run pyright
uv run pytest tests/unit/bootstrap -q
uv run pytest tests/integration/bootstrap -q
git add src/infinite_interns/graph src/infinite_interns/bootstrap tests AGENTS.md
git commit -m "feat: require reproducible repository baseline before planning"
```

## Stage 2B completion gate

Required evidence:

- brownfield/greenfield classification is deterministic,
- dirty brownfield input is not silently overwritten,
- base commit is recorded before autonomous edits,
- guidance/command detection is bounded and provenance-aware,
- pre-existing failures are recorded distinctly,
- greenfield bootstrap does not invent product architecture,
- parent graph cannot enter specification without a baseline ref.
