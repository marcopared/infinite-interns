"""Fenced publication of authoritative worker results."""

import re
from datetime import datetime
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from infinite_interns.db.repositories import EventRepository, TaskRepository
from infinite_interns.domain.models import EventRecord

_FULL_GIT_OBJECT_ID = re.compile(r"(?:[0-9a-fA-F]{40}|[0-9a-fA-F]{64})\Z")


class WorkerResultService:
    def __init__(self, session: AsyncSession, run_id: str) -> None:
        self._session = session
        self._run_id = run_id

    async def accept(
        self,
        task_id: str,
        lease_epoch: int,
        candidate_commit: str,
        occurred_at: datetime,
    ) -> bool:
        self._require_aware(occurred_at)
        if lease_epoch < 1:
            raise ValueError("lease_epoch must be positive")
        if _FULL_GIT_OBJECT_ID.fullmatch(candidate_commit) is None:
            raise ValueError("candidate commit must be a full 40- or 64-character Git object ID")

        changed = await TaskRepository(self._session).publish_candidate_if_active_lease(
            self._run_id,
            task_id,
            lease_epoch,
            candidate_commit.lower(),
            occurred_at,
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
                data={"lease_epoch": lease_epoch, "candidate_commit": candidate_commit.lower()},
                occurred_at=occurred_at,
            )
        )
        return False

    @staticmethod
    def _require_aware(value: datetime) -> None:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("worker result timestamps must be timezone-aware")
