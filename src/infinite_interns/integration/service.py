"""Serialized integration service with regression-gated last-green advancement."""

import asyncio
import hashlib
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from uuid import uuid4

from sqlalchemy import text, update
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from infinite_interns.db.models import IntegrationStateRow
from infinite_interns.db.repositories import EventRepository, TaskRepository
from infinite_interns.domain.models import EventRecord


class IntegrationStatus(StrEnum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    CONFLICT = "conflict"


@dataclass(frozen=True)
class IntegrationState:
    run_id: str
    current_commit: str
    last_green_commit: str
    updated_at: datetime


@dataclass(frozen=True)
class IntegrationResult:
    status: IntegrationStatus
    current_commit: str
    last_green_commit: str
    candidate_commit: str
    reason: str | None = None


class IntegrationService:
    def __init__(
        self,
        engine: AsyncEngine,
        sessions: async_sessionmaker[AsyncSession],
        checkout: Path,
        regression_argv: tuple[str, ...],
    ) -> None:
        if not regression_argv:
            raise ValueError("regression_argv must be non-empty")
        self._engine = engine
        self._sessions = sessions
        self._checkout = checkout.resolve()
        self._regression_argv = regression_argv

    async def initialize(self, run_id: str, commit_sha: str, updated_at: datetime) -> None:
        self._require_aware(updated_at)
        self._validate_run_id(run_id)
        head = await self._git("rev-parse", "HEAD")
        if head != commit_sha:
            raise ValueError("integration checkout HEAD must match initial last-green commit")

        async with self._sessions() as session:
            existing = await session.get(IntegrationStateRow, run_id)
            if existing is not None:
                if existing.current_commit != commit_sha or existing.last_green_commit != commit_sha:
                    raise ValueError("integration state already initialized to a different commit")
                return
            session.add(
                IntegrationStateRow(
                    run_id=run_id,
                    current_commit=commit_sha,
                    last_green_commit=commit_sha,
                    updated_at=updated_at,
                )
            )
            await session.commit()

        await self._git("update-ref", self._integration_ref(run_id), commit_sha)

    async def state(self, run_id: str) -> IntegrationState:
        async with self._sessions() as session:
            row = await session.get(IntegrationStateRow, run_id)
            if row is None:
                raise KeyError(f"integration state is not initialized for {run_id}")
            return IntegrationState(
                run_id=row.run_id,
                current_commit=row.current_commit,
                last_green_commit=row.last_green_commit,
                updated_at=row.updated_at,
            )

    async def integrate(
        self,
        run_id: str,
        candidate_commit: str,
        expected_last_green: str,
        *,
        task_id: str | None = None,
        lease_epoch: int | None = None,
    ) -> IntegrationResult:
        self._validate_run_id(run_id)
        if not candidate_commit or not expected_last_green:
            raise ValueError("candidate and expected last-green commits must be non-empty")
        if (task_id is None) != (lease_epoch is None):
            raise ValueError("task_id and lease_epoch must be supplied together")
        if lease_epoch is not None and lease_epoch < 1:
            raise ValueError("lease_epoch must be positive")

        async with self._engine.connect() as lock_connection:
            await lock_connection.execute(
                text("SELECT pg_advisory_lock(hashtextextended(:run_id, 0))"),
                {"run_id": run_id},
            )
            await lock_connection.commit()
            try:
                return await self._integrate_locked(
                    run_id,
                    candidate_commit,
                    expected_last_green,
                    task_id=task_id,
                    lease_epoch=lease_epoch,
                )
            finally:
                await lock_connection.execute(
                    text("SELECT pg_advisory_unlock(hashtextextended(:run_id, 0))"),
                    {"run_id": run_id},
                )
                await lock_connection.commit()

    async def _integrate_locked(
        self,
        run_id: str,
        candidate_commit: str,
        expected_last_green: str,
        *,
        task_id: str | None,
        lease_epoch: int | None,
    ) -> IntegrationResult:
        state = await self.state(run_id)
        if state.last_green_commit != expected_last_green:
            return IntegrationResult(
                status=IntegrationStatus.CONFLICT,
                current_commit=state.current_commit,
                last_green_commit=state.last_green_commit,
                candidate_commit=candidate_commit,
                reason="expected last-green commit is stale",
            )

        head = await self._git("rev-parse", "HEAD")
        if head != expected_last_green:
            raise RuntimeError("integration checkout drifted from durable last-green commit")

        await self._git("switch", "--detach", expected_last_green)
        cherry_pick = await self._run_git("cherry-pick", candidate_commit, check=False)
        if cherry_pick.returncode != 0:
            await self._run_git("cherry-pick", "--abort", check=False)
            await self._git("switch", "--detach", expected_last_green)
            return await self._reject(
                run_id,
                candidate_commit,
                expected_last_green,
                "cherry-pick failed",
            )

        regression = await asyncio.to_thread(
            subprocess.run,
            list(self._regression_argv),
            cwd=self._checkout,
            text=True,
            capture_output=True,
            check=False,
        )
        if regression.returncode != 0:
            await self._git("switch", "--detach", expected_last_green)
            return await self._reject(
                run_id,
                candidate_commit,
                expected_last_green,
                "regression failed",
            )

        new_green = await self._git("rev-parse", "HEAD")
        integration_ref = self._integration_ref(run_id)
        await self._git(
            "update-ref",
            integration_ref,
            new_green,
            expected_last_green,
        )
        now = datetime.now(UTC)
        async with self._sessions() as session:
            statement = (
                update(IntegrationStateRow)
                .where(
                    IntegrationStateRow.run_id == run_id,
                    IntegrationStateRow.last_green_commit == expected_last_green,
                )
                .values(
                    current_commit=new_green,
                    last_green_commit=new_green,
                    updated_at=now,
                )
                .returning(IntegrationStateRow.run_id)
            )
            changed = (await session.execute(statement)).scalar_one_or_none()
            if changed is None:
                await session.rollback()
                await self._restore_git_anchor(integration_ref, expected_last_green, new_green)
                raise RuntimeError("last-green state changed while integration lock was held")

            if task_id is not None and lease_epoch is not None:
                completed = await TaskRepository(session).mark_done_after_integration(
                    run_id,
                    task_id,
                    lease_epoch,
                )
                if not completed:
                    await session.rollback()
                    await self._restore_git_anchor(integration_ref, expected_last_green, new_green)
                    raise RuntimeError("task is not an integration-eligible candidate")

            await session.commit()

        return IntegrationResult(
            status=IntegrationStatus.ACCEPTED,
            current_commit=new_green,
            last_green_commit=new_green,
            candidate_commit=candidate_commit,
        )

    async def _restore_git_anchor(
        self,
        integration_ref: str,
        expected_last_green: str,
        new_green: str,
    ) -> None:
        await self._git("update-ref", integration_ref, expected_last_green, new_green)
        await self._git("switch", "--detach", expected_last_green)

    async def _reject(
        self,
        run_id: str,
        candidate_commit: str,
        expected_last_green: str,
        reason: str,
    ) -> IntegrationResult:
        now = datetime.now(UTC)
        async with self._sessions() as session:
            await EventRepository(session).add(
                EventRecord(
                    event_id=f"evt_{uuid4().hex}",
                    run_id=run_id,
                    event_type="INTEGRATION_REJECTED",
                    entity_type="candidate",
                    entity_id=candidate_commit,
                    data={"reason": reason, "last_green_commit": expected_last_green},
                    occurred_at=now,
                )
            )
            await session.commit()
        return IntegrationResult(
            status=IntegrationStatus.REJECTED,
            current_commit=expected_last_green,
            last_green_commit=expected_last_green,
            candidate_commit=candidate_commit,
            reason=reason,
        )

    async def _git(self, *args: str) -> str:
        return (await self._run_git(*args, check=True)).stdout.strip()

    async def _run_git(
        self,
        *args: str,
        check: bool,
    ) -> subprocess.CompletedProcess[str]:
        return await asyncio.to_thread(
            subprocess.run,
            ["git", "-C", str(self._checkout), *args],
            text=True,
            capture_output=True,
            check=check,
        )

    @staticmethod
    def _integration_ref(run_id: str) -> str:
        digest = hashlib.sha256(run_id.encode()).hexdigest()[:24]
        return f"refs/infinite-interns/integration/{digest}"

    @staticmethod
    def _validate_run_id(run_id: str) -> None:
        if not run_id or "\x00" in run_id:
            raise ValueError("run_id must be non-empty and contain no NUL")

    @staticmethod
    def _require_aware(value: datetime) -> None:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("integration timestamps must be timezone-aware")
