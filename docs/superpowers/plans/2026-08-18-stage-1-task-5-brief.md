# Task 5 brief — artifact URIs and filesystem storage

Implement Stage 1 Task 5 from `2026-08-18-stage-1-deterministic-foundation.md`.

Required interfaces:

- `ArtifactStore.put(run_id, kind, artifact_id, data) -> str`
- `ArtifactStore.get(uri) -> bytes`
- concrete `FilesystemArtifactStore`

URI format is exactly:

```text
artifact://runs/<run_id>/<kind>/<artifact_id>
```

Requirements:

- raw artifact bodies stay outside PostgreSQL;
- every read/write resolves under the configured artifact root;
- reject path traversal, path separators in identifiers, malformed schemes/netlocs, and malformed path arity;
- use `pathlib.Path.resolve()` containment checks;
- no sidecar metadata files in Stage 1; SHA/size metadata belongs to the calling evidence/artifact service later.
