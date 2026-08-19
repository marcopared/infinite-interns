"""Deterministic, model-free task selection policy."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from infinite_interns.config import SchedulerSettings
from infinite_interns.domain.enums import RiskClass, TaskStatus


@dataclass(frozen=True)
class SchedulerCandidate:
    task_id: str
    status: TaskStatus
    parents: tuple[str, ...]
    critical_path: bool
    blocks_count: int
    risk: RiskClass
    waiting_since: datetime
    exclusive_resources: tuple[str, ...]


@dataclass(frozen=True)
class SchedulerSnapshot:
    candidates: tuple[SchedulerCandidate, ...]
    active_task_ids: tuple[str, ...]
    active_resource_locks: tuple[str, ...]


@dataclass(frozen=True)
class SchedulerDecision:
    selected_task_ids: tuple[str, ...]


class SchedulerSource(Protocol):
    async def load(self, run_id: str) -> SchedulerSnapshot: ...


_RISK_RANK = {
    RiskClass.LOW: 0,
    RiskClass.MEDIUM: 1,
    RiskClass.HIGH: 2,
    RiskClass.CRITICAL: 3,
}


class Scheduler:
    def __init__(self, source: SchedulerSource, settings: SchedulerSettings) -> None:
        self._source = source
        self._settings = settings

    async def tick(self, run_id: str, now: datetime) -> SchedulerDecision:
        self._require_aware(now)
        snapshot = await self._source.load(run_id)
        capacity = max(0, self._settings.max_swe_workers - len(snapshot.active_task_ids))
        if capacity == 0:
            return SchedulerDecision(())

        by_id = {candidate.task_id: candidate for candidate in snapshot.candidates}
        if len(by_id) != len(snapshot.candidates):
            raise ValueError("scheduler snapshot contains duplicate task IDs")

        ready = [
            candidate
            for candidate in snapshot.candidates
            if candidate.status in {TaskStatus.PLANNED, TaskStatus.READY}
            and self._dependencies_satisfied(candidate, by_id)
        ]
        ready.sort(key=lambda candidate: self._priority_key(candidate, now))

        held_resources = set(snapshot.active_resource_locks)
        selected: list[str] = []
        for candidate in ready:
            resources = set(candidate.exclusive_resources)
            if held_resources.intersection(resources):
                continue
            selected.append(candidate.task_id)
            held_resources.update(resources)
            if len(selected) >= capacity:
                break

        return SchedulerDecision(tuple(selected))

    @staticmethod
    def _dependencies_satisfied(
        candidate: SchedulerCandidate,
        by_id: dict[str, SchedulerCandidate],
    ) -> bool:
        satisfied = {TaskStatus.DONE, TaskStatus.VERIFIED}
        for parent_id in candidate.parents:
            parent = by_id.get(parent_id)
            if parent is None or parent.status not in satisfied:
                return False
        return True

    @staticmethod
    def _priority_key(candidate: SchedulerCandidate, now: datetime) -> tuple[int, int, int, float, str]:
        Scheduler._require_aware(candidate.waiting_since)
        waiting_seconds = max(0.0, (now - candidate.waiting_since).total_seconds())
        return (
            -int(candidate.critical_path),
            -candidate.blocks_count,
            -_RISK_RANK[candidate.risk],
            -waiting_seconds,
            candidate.task_id,
        )

    @staticmethod
    def _require_aware(value: datetime) -> None:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("scheduler timestamps must be timezone-aware")
