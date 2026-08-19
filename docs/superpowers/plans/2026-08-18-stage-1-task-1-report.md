# Task 1 report

Status: complete.

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
- Generated and committed `uv.lock`; CI now enforces `uv sync --dev --locked`.

## Reproducibility follow-up

The original controller sandbox could not materialize `uv.lock`, so Task 1 initially carried a minor reproducibility debt. A one-shot GitHub Actions workflow later ran `uv lock` on the implementation branch and committed the generated lockfile. The temporary workflow was then removed and normal CI was switched to locked synchronization. The debt is resolved.
