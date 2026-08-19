"""Fenced publication of authoritative worker results."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from infinite_interns.db.repositories import EventRepository, TaskRepository
from infinite_interns.domain.enums import TaskStatus
from infinite_interns.domain.models import EventRecord


class WorkerResultService:
    def __init__(self, session: AsyncSession, run_id: str) -> None:
        self._session = session
        self._run_id = run_id

    async def accept(
        self,
        task_id: str,
        lease_epoch: int,
        status: TaskStatus,
        occurred_at: datetime,
    ) -> bool:
        self._require_aware(occurred_at)
        if lease_epoch < 1:
            raise ValueError("lease_epoch must be positive")

        changed = await TaskRepository(self._session).set_status_if_epoch(
            self._run_id,
            task_id,
            lease_epoch,
            status,
        )
        if changed:
            return True

        await EventRepository(self._session).add(
            EventRecord(
                event_id=f"evt_{uuid4().hex}",
                run_id=self._run_id,
                event_type="STALE_WORKER_WRITE_REJECTED",
                entity_type="task",
                entity_id=task_id,
                data={"lease_epoch": lease_epoch, "requested_status": status.value},
                occurred_at=occurred_at,
            )
        )
        return False

    @staticmethod
    def _require_aware(value: datetime) -> None:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("worker result timestamps must be timezone-aware")
