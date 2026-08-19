# Task 1 report

Status: DONE_WITH_CONCERNS

## RED evidence

GitHub Actions run `32208808217` executed the intended smoke test before implementation.

```text
FAILED tests/unit/test_package.py::test_package_has_version
AssertionError: assert None == '0.1.0'
1 failed
```

Ruff passed before the failing behavioral test. The failure was caused specifically by the absent `__version__` behavior.

## GREEN evidence

After adding only:

```python
__version__ = "0.1.0"
```

GitHub Actions run `32208873899` reported:

```text
uv sync --dev                 PASS
uv run ruff check .           PASS
uv run pytest tests/unit -q   PASS
uv run pyright                PASS
```

## Deliverables

- Python 3.13 package metadata and `interns` entry-point declaration.
- Package scaffold and version behavior.
- Local PostgreSQL 16 Compose service.
- Baseline GitHub Actions lint/test/typecheck gate.
- Runtime/cache ignore rules.

## Concern

`uv.lock` is not yet committed because the current controller sandbox cannot execute `uv lock` or clone GitHub locally. CI successfully resolves the dependency set with uv. The Stage 1 ledger records the ruling to keep `uv sync --dev` temporarily and close the lockfile reproducibility debt before Stage 1 completion if a lock-generating execution path becomes available.
