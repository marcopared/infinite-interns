# Task 5 report

Status: complete.

## RED evidence

GitHub Actions run `32210388262` passed Ruff and failed the unit suite because `FilesystemArtifactStore` was absent. The failure occurred before any artifact implementation existed.

## GREEN evidence

GitHub Actions run `32210447099`:

```text
uv sync --dev                         PASS
uv run ruff check .                   PASS
uv run pytest tests/unit -q           PASS
uv run alembic upgrade head           PASS
uv run pytest tests/integration/db -q PASS
uv run pyright                        PASS
```

## Deliverables

- Provider-neutral `ArtifactStore` protocol.
- `FilesystemArtifactStore` rooted at a resolved configured directory.
- Exact URI format `artifact://runs/<run_id>/<kind>/<artifact_id>`.
- Traversal/path-separator rejection on both writes and URI reads.
- URI scheme/netloc/path-arity validation.
- No artifact bodies or sidecar metadata stored in PostgreSQL.
