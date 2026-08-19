# Stage 2 Task 5 report

Status: COMPLETE.

## RED evidence

After fixing an async-test lint issue, Actions run `32311029814` reached integration collection and failed specifically because `DockerExecutionBackend` did not exist.

## Architecture ruling discovered during implementation

A linked Git worktree's `.git` file points to shared repository metadata outside the worktree directory. Mounting that metadata into the worker would violate the Task 5 isolation rule that a worker receives only its task worktree plus artifact directory.

Ruling: the untrusted worker mutates files and emits an atomic `worker-result.json`; after successful exit, the trusted executor validates attempt/lease identity and materializes the Git candidate commit on the host. The worker therefore never receives shared Git metadata or Docker authority.

## Docker isolation

`DockerExecutionBackend` launches workers with:

- run/task/attempt/operation/lease labels;
- non-root host UID/GID;
- `--cap-drop ALL`;
- `no-new-privileges`;
- explicit CPU/memory limits;
- explicit network profile (`none` in certification);
- exactly two bind mounts: task worktree and task artifact directory;
- no Docker socket mount.

Label lookup uses full container IDs and makes execution creation recoverable after executor-daemon restart. Duplicate operation keys cannot intentionally create a second container.

## Worker protocol

The fake worker writes only `task-output.txt` and atomic `worker-result.json`. The executor requires exact `attempt_id`, `lease_epoch`, and successful status before `git add`/candidate commit and atomic `result.json` creation.

The integration checkout remains unchanged while the task worktree receives the candidate.

## Workstation stack

`docker-compose.workstation.yml` separates PostgreSQL, Redis, Agent Server, and executor. A static test requires that only the executor receives `/var/run/docker.sock`. The internal control network is explicit.

## Implementation failures repaired

- invalid Docker long `--mount ... ,rw` syntax: repaired by relying on bind mounts' read/write default;
- recovered container IDs were short while `docker run` returned full IDs: repaired with `docker ps --no-trunc`;
- Pyright loop-state issue in the Docker integration test: repaired with explicit initialization.

## Final GREEN evidence

Actions run `32311707964` passed:

```text
uv sync --dev --locked                      PASS
uv run ruff check .                         PASS
uv run pytest tests/unit -q                 PASS (46 tests)
uv run alembic upgrade head                 PASS
uv run pytest tests/integration -q          PASS (7 tests)
uv run pyright                              PASS
docker compose ... config --quiet           PASS
docker compose ... build agent-server executor  PASS
Smoke LangGraph Agent Server                PASS
```
