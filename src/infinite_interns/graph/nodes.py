"""Thin LangGraph node adapters for the parent factory graph."""

from datetime import UTC, datetime

from infinite_interns.graph.state import FactoryState
from infinite_interns.scheduler.service import Scheduler


class FactoryGraphServices:
    """Typed service boundary used by graph nodes.

    Nodes route state through deterministic services. SQL, Docker lifecycle,
    model execution, and completion authority remain outside LangGraph nodes.
    """

    def __init__(self, scheduler: Scheduler | None = None) -> None:
        self._scheduler = scheduler

    async def load_run(self, state: FactoryState) -> dict[str, object]:
        return {"run_id": state.run_id}

    async def schedule(self, state: FactoryState) -> dict[str, object]:
        if self._scheduler is None:
            return {"ready_task_ids": list(state.ready_task_ids)}
        decision = await self._scheduler.tick(state.run_id, datetime.now(UTC))
        return {"ready_task_ids": list(decision.selected_task_ids)}

    async def wait_or_finish(self, state: FactoryState) -> dict[str, object]:
        return {"current_commit": state.current_commit}


_services = FactoryGraphServices()


def configure_services(services: FactoryGraphServices) -> None:
    global _services
    _services = services


async def load_run(state: FactoryState) -> dict[str, object]:
    return await _services.load_run(state)


async def schedule(state: FactoryState) -> dict[str, object]:
    return await _services.schedule(state)


async def wait_or_finish(state: FactoryState) -> dict[str, object]:
    return await _services.wait_or_finish(state)
