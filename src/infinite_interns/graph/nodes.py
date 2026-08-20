"""Thin LangGraph node adapters for the parent factory graph."""

from datetime import UTC, datetime
from typing import Protocol

from infinite_interns.bootstrap.coordinator import BootstrapResult
from infinite_interns.graph.state import FactoryState
from infinite_interns.scheduler.service import Scheduler


class BootstrapEstablisher(Protocol):
    async def establish(self, run_id: str) -> BootstrapResult: ...


class MissingBaselineError(RuntimeError):
    """Raised when planning is attempted without a durable repository baseline."""


class FactoryGraphServices:
    """Typed service boundary used by graph nodes.

    Nodes route state through deterministic services. SQL, Docker lifecycle,
    model execution, and completion authority remain outside LangGraph nodes.
    """

    def __init__(
        self,
        scheduler: Scheduler | None = None,
        bootstrap_establisher: BootstrapEstablisher | None = None,
    ) -> None:
        self._scheduler = scheduler
        self._bootstrap = bootstrap_establisher

    async def load_run(self, state: FactoryState) -> dict[str, object]:
        return {"run_id": state.run_id}

    async def bootstrap(self, state: FactoryState) -> dict[str, object]:
        if self._bootstrap is None:
            if state.baseline_ref is not None:
                return {"baseline_ref": state.baseline_ref}
            raise MissingBaselineError("repository bootstrap must complete before specification")

        result = await self._bootstrap.establish(state.run_id)
        return {
            "baseline_ref": result.baseline_ref,
            "current_commit": result.base_commit,
            "last_green_commit": result.base_commit,
        }

    async def specification_pending(self, state: FactoryState) -> dict[str, object]:
        if state.baseline_ref is None:
            raise MissingBaselineError("specification entry requires a persisted baseline reference")
        return {"spec_version": state.spec_version}

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


async def bootstrap(state: FactoryState) -> dict[str, object]:
    return await _services.bootstrap(state)


async def specification_pending(state: FactoryState) -> dict[str, object]:
    return await _services.specification_pending(state)


async def schedule(state: FactoryState) -> dict[str, object]:
    return await _services.schedule(state)


async def wait_or_finish(state: FactoryState) -> dict[str, object]:
    return await _services.wait_or_finish(state)
