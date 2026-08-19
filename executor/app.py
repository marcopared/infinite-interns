"""FastAPI boundary for isolated task execution."""

from fastapi import FastAPI, HTTPException, Response

from infinite_interns.execution.base import ExecutionBackend, ExecutionHandle, ExecutionRequest


def create_app(backend: ExecutionBackend) -> FastAPI:
    app = FastAPI()
    handles_by_id: dict[str, ExecutionHandle] = {}
    ids_by_operation_key: dict[str, str] = {}

    @app.post("/executions", response_model=ExecutionHandle)
    async def create_execution(request: ExecutionRequest, response: Response) -> ExecutionHandle:
        existing_id = ids_by_operation_key.get(request.operation_key)
        if existing_id is not None:
            response.status_code = 200
            return handles_by_id[existing_id]

        handle = await backend.create(request)
        handles_by_id[handle.execution_id] = handle
        ids_by_operation_key[request.operation_key] = handle.execution_id
        response.status_code = 201
        return handle

    def get_handle(execution_id: str) -> ExecutionHandle:
        handle = handles_by_id.get(execution_id)
        if handle is None:
            raise HTTPException(status_code=404, detail="execution not found")
        return handle

    @app.get("/executions/{execution_id}")
    async def execution_status(execution_id: str) -> dict[str, str]:
        handle = get_handle(execution_id)
        status = await backend.status(handle)
        return {"execution_id": execution_id, "status": status.value}

    @app.post("/executions/{execution_id}/terminate", status_code=204)
    async def terminate_execution(execution_id: str) -> None:
        await backend.terminate(get_handle(execution_id))

    @app.post("/executions/{execution_id}/heartbeat")
    async def heartbeat(execution_id: str) -> dict[str, str]:
        handle = get_handle(execution_id)
        status = await backend.status(handle)
        return {"execution_id": execution_id, "status": status.value}

    return app
