from datetime import UTC, datetime, timedelta

import pytest

from infinite_interns.config import SchedulerSettings
from infinite_interns.domain.enums import RiskClass, TaskStatus
from infinite_interns.scheduler.service import Scheduler, SchedulerCandidate, SchedulerSnapshot


class StaticSource:
    def __init__(self, snapshot: SchedulerSnapshot) -> None:
        self.snapshot = snapshot

    async def load(self, run_id: str) -> SchedulerSnapshot:
        assert run_id == "run1"
        return self.snapshot


@pytest.mark.asyncio
async def test_scheduler_respects_capacity_dependencies_and_resource_locks() -> None:
    now = datetime.now(UTC)
    snapshot = SchedulerSnapshot(
        candidates=(
            SchedulerCandidate(
                task_id="A",
                status=TaskStatus.PLANNED,
                parents=(),
                critical_path=True,
                blocks_count=2,
                risk=RiskClass.HIGH,
                waiting_since=now - timedelta(minutes=5),
                exclusive_resources=("db-schema",),
            ),
            SchedulerCandidate(
                task_id="B",
                status=TaskStatus.PLANNED,
                parents=(),
                critical_path=False,
                blocks_count=5,
                risk=RiskClass.MEDIUM,
                waiting_since=now - timedelta(minutes=20),
                exclusive_resources=(),
            ),
            SchedulerCandidate(
                task_id="C",
                status=TaskStatus.PLANNED,
                parents=("A", "B"),
                critical_path=True,
                blocks_count=0,
                risk=RiskClass.HIGH,
                waiting_since=now - timedelta(minutes=30),
                exclusive_resources=(),
            ),
            SchedulerCandidate(
                task_id="D",
                status=TaskStatus.PLANNED,
                parents=(),
                critical_path=True,
                blocks_count=1,
                risk=RiskClass.CRITICAL,
                waiting_since=now - timedelta(minutes=1),
                exclusive_resources=("db-schema",),
            ),
        ),
        active_task_ids=("RUNNING-1",),
        active_resource_locks=("db-schema",),
    )
    scheduler = Scheduler(StaticSource(snapshot), SchedulerSettings(max_swe_workers=2))
    decision = await scheduler.tick("run1", now)
    assert decision.selected_task_ids == ("B",)


@pytest.mark.asyncio
async def test_priority_is_deterministic_and_critical_path_wins() -> None:
    now = datetime.now(UTC)
    snapshot = SchedulerSnapshot(
        candidates=(
            SchedulerCandidate("A", TaskStatus.PLANNED, (), False, 99, RiskClass.CRITICAL, now, ()),
            SchedulerCandidate("B", TaskStatus.PLANNED, (), True, 1, RiskClass.LOW, now, ()),
            SchedulerCandidate("C", TaskStatus.PLANNED, (), True, 1, RiskClass.LOW, now, ()),
        ),
        active_task_ids=(),
        active_resource_locks=(),
    )
    scheduler = Scheduler(StaticSource(snapshot), SchedulerSettings(max_swe_workers=2))
    decision = await scheduler.tick("run1", now)
    assert decision.selected_task_ids == ("B", "C")
