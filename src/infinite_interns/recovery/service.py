"""Heartbeat and semantic-progress recovery decisions."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Protocol


class RecoveryActionKind(StrEnum):
    NONE = "none"
    EXPIRE_LEASE = "expire_lease"
    PROBE = "probe"
    STALLED = "stalled"


@dataclass(frozen=True)
class ProgressSnapshot:
    last_heartbeat: datetime
    last_agent_event: datetime
    last_semantic_progress: datetime


@dataclass(frozen=True)
class RecoveryAction:
    task_id: str
    kind: RecoveryActionKind
    reason: str


class RecoverySource(Protocol):
    async def snapshots(self) -> tuple[tuple[str, ProgressSnapshot], ...]: ...

    async def expire(self, task_id: str, now: datetime) -> None: ...


class RecoveryService:
    heartbeat_timeout = timedelta(seconds=90)
    agent_event_timeout = timedelta(minutes=10)
    semantic_progress_timeout = timedelta(minutes=20)

    def __init__(self, source: RecoverySource | None = None) -> None:
        self._source = source

    @classmethod
    def classify(
        cls,
        task_id: str,
        snapshot: ProgressSnapshot,
        now: datetime,
    ) -> RecoveryAction:
        cls._require_aware(now)
        for value in (
            snapshot.last_heartbeat,
            snapshot.last_agent_event,
            snapshot.last_semantic_progress,
        ):
            cls._require_aware(value)

        if now - snapshot.last_heartbeat > cls.heartbeat_timeout:
            return RecoveryAction(task_id, RecoveryActionKind.EXPIRE_LEASE, "worker heartbeat expired")
        if now - snapshot.last_semantic_progress > cls.semantic_progress_timeout:
            return RecoveryAction(task_id, RecoveryActionKind.STALLED, "no semantic progress")
        if now - snapshot.last_agent_event > cls.agent_event_timeout:
            return RecoveryAction(task_id, RecoveryActionKind.PROBE, "agent event stream is quiet")
        return RecoveryAction(task_id, RecoveryActionKind.NONE, "worker is progressing")

    async def expire_stale_leases(self, now: datetime) -> list[RecoveryAction]:
        if self._source is None:
            raise RuntimeError("RecoveryService requires a source for lease expiration")
        actions: list[RecoveryAction] = []
        for task_id, snapshot in await self._source.snapshots():
            action = self.classify(task_id, snapshot, now)
            if action.kind is RecoveryActionKind.EXPIRE_LEASE:
                await self._source.expire(task_id, now)
                actions.append(action)
        return actions

    @staticmethod
    def _require_aware(value: datetime) -> None:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("recovery timestamps must be timezone-aware")
