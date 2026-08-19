"""Thin LangGraph node adapters for the parent factory graph."""

from infinite_interns.graph.state import FactoryState


class FactoryGraphServices:
    """Typed service boundary used by graph nodes.

    Stage 2 later replaces these shell operations with deterministic scheduler
    and recovery services. Graph nodes remain orchestration adapters rather
    than locations for SQL or Docker lifecycle logic.
    """

    async def load_run(self, state: FactoryState) -> dict[str, object]:
        return {"run_id": state.run_id}

    async def schedule(self, state: FactoryState) -> dict[str, object]:
        return {"ready_task_ids": list(state.ready_task_ids)}

    async def wait_or_finish(self, state: FactoryState) -> dict[str, object]:
        return {"current_commit": state.current_commit}


_services = FactoryGraphServices()


async def load_run(state: FactoryState) -> dict[str, object]:
    return await _services.load_run(state)


async def schedule(state: FactoryState) -> dict[str, object]:
    return await _services.schedule(state)


async def wait_or_finish(state: FactoryState) -> dict[str, object]:
    return await _services.wait_or_finish(state)
