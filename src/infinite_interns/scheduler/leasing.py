"""Short-lived PostgreSQL task leases with monotonic fencing epochs."""

from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from infinite_interns.db.models import TaskRow
from infinite_interns.domain.enums import TaskStatus


class StaleLeaseError(RuntimeError):
    """Raised when a worker attempts an authoritative action with stale ownership."""


@dataclass(frozen=True)
class TaskLease:
    task_id: str
    owner: str
    epoch: int
    expires_at: datetime


class LeaseService:
    """Lease tasks within exactly one factory run.

    Each operation owns only a short database transaction. No caller should
    retain the row lock while executing an engineering task.
    """

    def __init__(
        self,
        session: AsyncSession,
        run_id: str,
        *,
        lease_ttl: timedelta = timedelta(seconds=90),
    ) -> None:
        if lease_ttl <= timedelta(0):
            raise ValueError("lease_ttl must be positive")
        self._session = session
        self._run_id = run_id
        self._lease_ttl = lease_ttl

    async def claim_ready_task(self, worker_id: str, now: datetime) -> TaskLease | None:
        if not worker_id:
            raise ValueError("worker_id must be non-empty")
        self._require_aware(now)

        claimable_expired = and_(
            TaskRow.status.in_((TaskStatus.CLAIMED.value, TaskStatus.RUNNING.value)),
            TaskRow.lease_expires_at.is_not(None),
            TaskRow.lease_expires_at <= now,
        )
        statement = (
            select(TaskRow)
            .where(
                TaskRow.run_id == self._run_id,
                or_(TaskRow.status == TaskStatus.READY.value, claimable_expired),
            )
            .order_by(TaskRow.task_id)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        row = (await self._session.execute(statement)).scalar_one_or_none()
        if row is None:
            await self._session.rollback()
            return None

        row.lease_epoch += 1
        row.lease_owner = worker_id
        row.lease_expires_at = now + self._lease_ttl
        row.status = TaskStatus.CLAIMED.value
        await self._session.flush()
        lease = self._to_lease(row)
        await self._session.commit()
        return lease

    async def renew(
        self,
        task_id: str,
        owner: str,
        epoch: int,
        now: datetime,
    ) -> TaskLease:
        self._require_aware(now)
        row = await self._locked_task(task_id)
        if (
            row.lease_owner != owner
            or row.lease_epoch != epoch
            or row.lease_expires_at is None
            or row.lease_expires_at <= now
        ):
            await self._session.rollback()
            raise StaleLeaseError(f"task {task_id} lease is stale")

        row.lease_expires_at = now + self._lease_ttl
        await self._session.flush()
        lease = self._to_lease(row)
        await self._session.commit()
        return lease

    async def assert_epoch(self, task_id: str, epoch: int) -> None:
        statement = select(TaskRow.lease_epoch).where(
            TaskRow.run_id == self._run_id,
            TaskRow.task_id == task_id,
        )
        current = (await self._session.execute(statement)).scalar_one_or_none()
        if current is None or current != epoch:
            raise StaleLeaseError(f"task {task_id} epoch {epoch} is stale")

    async def _locked_task(self, task_id: str) -> TaskRow:
        statement = (
            select(TaskRow)
            .where(TaskRow.run_id == self._run_id, TaskRow.task_id == task_id)
            .with_for_update()
        )
        row = (await self._session.execute(statement)).scalar_one_or_none()
        if row is None:
            await self._session.rollback()
            raise StaleLeaseError(f"task {task_id} does not exist")
        return row

    @staticmethod
    def _to_lease(row: TaskRow) -> TaskLease:
        if row.lease_owner is None or row.lease_expires_at is None:
            raise RuntimeError("claimed task row is missing lease data")
        return TaskLease(
            task_id=row.task_id,
            owner=row.lease_owner,
            epoch=row.lease_epoch,
            expires_at=row.lease_expires_at,
        )

    @staticmethod
    def _require_aware(value: datetime) -> None:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("lease timestamps must be timezone-aware")
