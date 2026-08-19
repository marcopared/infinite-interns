import pytest
from executor.app import create_app
from executor.memory_backend import InMemoryExecutionBackend
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_duplicate_execution_request_reuses_execution() -> None:
    backend = InMemoryExecutionBackend()
    app = create_app(backend)
    payload = {
        "operation_key": "run1:task1:attempt1:execute",
        "run_id": "run1",
        "task_id": "task1",
        "attempt_id": "attempt1",
        "lease_epoch": 1,
        "worktree_path": "/worktrees/run1/task1/attempt1",
        "image": "fake-worker:test",
        "argv": ["python", "/worker.py"],
        "artifact_path": "/artifacts/run1/task1/attempt1",
        "environment_names": ["TEST_TOKEN"],
        "cpu_limit": 1.0,
        "memory_limit_mb": 512,
        "network_profile": "none",
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://executor") as client:
        first = await client.post("/executions", json=payload)
        second = await client.post("/executions", json=payload)

    assert first.status_code == 201
    assert second.status_code == 200
    assert first.json()["execution_id"] == second.json()["execution_id"]
    assert backend.create_count == 1
