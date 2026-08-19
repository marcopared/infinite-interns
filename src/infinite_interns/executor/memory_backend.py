"""In-memory executor backend used to prove API behavior before Docker exists."""

from uuid import uuid4

from infinite_interns.execution.base import ExecutionHandle, ExecutionRequest, ExecutionStatus


class InMemoryExecutionBackend:
    def __init__(self) -> None:
        self.create_count = 0
        self._statuses: dict[str, ExecutionStatus] = {}

    async def create(self, request: ExecutionRequest) -> ExecutionHandle:
        self.create_count += 1
        execution_id = f"exec_{uuid4().hex}"
        self._statuses[execution_id] = ExecutionStatus.CREATED
        return ExecutionHandle(
            execution_id=execution_id,
            operation_key=request.operation_key,
            status=ExecutionStatus.CREATED,
        )

    async def status(self, handle: ExecutionHandle) -> ExecutionStatus:
        return self._statuses[handle.execution_id]

    async def terminate(self, handle: ExecutionHandle) -> None:
        self._statuses[handle.execution_id] = ExecutionStatus.TERMINATED
