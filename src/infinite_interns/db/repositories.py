"""Repository boundary between SQLAlchemy rows and immutable domain records."""

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from infinite_interns.domain.enums import (
    EvidenceResult,
    RequirementStatus,
    RiskClass,
    RunStatus,
    TaskStatus,
)
from infinite_interns.domain.models import (
    EventRecord,
    EvidenceRecord,
    RequirementRecord,
    RunRecord,
    TaskRecord,
)

from .models import EventRow, EvidenceRow, RequirementRow, RunRow, TaskRow


class RunRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, record: RunRecord) -> None:
        self._session.add(
            RunRow(
                run_id=record.run_id,
                repo=record.repo,
                base_commit=record.base_commit,
                status=record.status.value,
                started_at=record.started_at,
            )
        )
        await self._session.flush()

    async def get(self, run_id: str) -> RunRecord | None:
        row = await self._session.get(RunRow, run_id)
        if row is None:
            return None
        return RunRecord(
            run_id=row.run_id,
            repo=row.repo,
            base_commit=row.base_commit,
            status=RunStatus(row.status),
            started_at=row.started_at,
        )


class RequirementRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, record: RequirementRecord) -> None:
        if record.status is not RequirementStatus.UNVERIFIED:
            raise ValueError("new requirements must be UNVERIFIED")
        self._session.add(
            RequirementRow(
                run_id=record.run_id,
                requirement_id=record.requirement_id,
                text=record.text,
                criticality=record.criticality.value,
                status=record.status.value,
            )
        )
        await self._session.flush()

    async def get(self, run_id: str, requirement_id: str) -> RequirementRecord | None:
        row = await self._session.get(RequirementRow, (run_id, requirement_id))
        if row is None:
            return None
        return RequirementRecord(
            requirement_id=row.requirement_id,
            run_id=row.run_id,
            text=row.text,
            criticality=RiskClass(row.criticality),
            status=RequirementStatus(row.status),
        )


class TaskRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, record: TaskRecord) -> None:
        self._session.add(
            TaskRow(
                run_id=record.run_id,
                task_id=record.task_id,
                title=record.title,
                status=record.status.value,
                risk=record.risk.value,
            )
        )
        await self._session.flush()

    async def get(self, run_id: str, task_id: str) -> TaskRecord | None:
        row = await self._session.get(TaskRow, (run_id, task_id))
        if row is None:
            return None
        return TaskRecord(
            task_id=row.task_id,
            run_id=row.run_id,
            title=row.title,
            status=TaskStatus(row.status),
            risk=RiskClass(row.risk),
        )

    async def publish_candidate_if_active_lease(
        self,
        run_id: str,
        task_id: str,
        expected_epoch: int,
        candidate_commit: str,
    ) -> bool:
        statement = (
            update(TaskRow)
            .where(
                TaskRow.run_id == run_id,
                TaskRow.task_id == task_id,
                TaskRow.lease_epoch == expected_epoch,
                TaskRow.lease_expires_at.is_not(None),
                TaskRow.lease_expires_at > func.now(),
                TaskRow.status.in_(
                    (
                        TaskStatus.CLAIMED.value,
                        TaskStatus.RUNNING.value,
                        TaskStatus.VERIFYING.value,
                        TaskStatus.REVIEWING.value,
                        TaskStatus.REPAIR.value,
                    )
                ),
            )
            .values(
                status=TaskStatus.CANDIDATE.value,
                candidate_commit=candidate_commit,
                lease_owner=None,
                lease_expires_at=None,
            )
            .returning(TaskRow.task_id)
        )
        changed = (await self._session.execute(statement)).scalar_one_or_none()
        return changed is not None

    async def mark_done_after_integration(
        self,
        run_id: str,
        task_id: str,
        expected_epoch: int,
        expected_candidate_commit: str,
    ) -> bool:
        statement = (
            update(TaskRow)
            .where(
                TaskRow.run_id == run_id,
                TaskRow.task_id == task_id,
                TaskRow.lease_epoch == expected_epoch,
                TaskRow.status == TaskStatus.CANDIDATE.value,
                TaskRow.candidate_commit == expected_candidate_commit,
            )
            .values(status=TaskStatus.DONE.value)
            .returning(TaskRow.task_id)
        )
        changed = (await self._session.execute(statement)).scalar_one_or_none()
        return changed is not None


class EvidenceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, record: EvidenceRecord) -> None:
        self._session.add(
            EvidenceRow(
                evidence_id=record.evidence_id,
                run_id=record.run_id,
                requirement_id=record.requirement_id,
                gate_id=record.gate_id,
                result=record.result.value,
                commit_sha=record.commit_sha,
                environment_hash=record.environment_hash,
                producer=record.producer,
                verifier_version=record.verifier_version,
                artifact_uri=record.artifact_uri,
                created_at=record.created_at,
            )
        )
        await self._session.flush()

    async def for_requirement(self, run_id: str, requirement_id: str) -> list[EvidenceRecord]:
        result = await self._session.execute(
            select(EvidenceRow)
            .where(
                EvidenceRow.run_id == run_id,
                EvidenceRow.requirement_id == requirement_id,
            )
            .order_by(EvidenceRow.created_at, EvidenceRow.evidence_id)
        )
        return [self._to_record(row) for row in result.scalars()]

    @staticmethod
    def _to_record(row: EvidenceRow) -> EvidenceRecord:
        return EvidenceRecord(
            evidence_id=row.evidence_id,
            run_id=row.run_id,
            requirement_id=row.requirement_id,
            gate_id=row.gate_id,
            result=EvidenceResult(row.result),
            commit_sha=row.commit_sha,
            environment_hash=row.environment_hash,
            producer=row.producer,
            verifier_version=row.verifier_version,
            artifact_uri=row.artifact_uri,
            created_at=row.created_at,
        )


class EventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, record: EventRecord) -> None:
        self._session.add(
            EventRow(
                event_id=record.event_id,
                run_id=record.run_id,
                event_type=record.event_type,
                entity_type=record.entity_type,
                entity_id=record.entity_id,
                data=record.data,
                occurred_at=record.occurred_at,
            )
        )
        await self._session.flush()

    async def for_run(self, run_id: str) -> list[EventRecord]:
        result = await self._session.execute(
            select(EventRow)
            .where(EventRow.run_id == run_id)
            .order_by(EventRow.occurred_at, EventRow.event_id)
        )
        return [
            EventRecord(
                event_id=row.event_id,
                run_id=row.run_id,
                event_type=row.event_type,
                entity_type=row.entity_type,
                entity_id=row.entity_id,
                data=row.data,
                occurred_at=row.occurred_at,
            )
            for row in result.scalars()
        ]
