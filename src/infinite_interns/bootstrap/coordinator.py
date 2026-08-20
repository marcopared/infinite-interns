"""Durable coordination boundary for repository bootstrap."""

from pathlib import Path

from pydantic import Field
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from infinite_interns.artifacts.filesystem import FilesystemArtifactStore
from infinite_interns.config import Settings
from infinite_interns.db.repositories import RunRepository

from .models import BootstrapModel
from .service import BootstrapService


class BootstrapResult(BootstrapModel):
    baseline_ref: str = Field(min_length=1)
    base_commit: str = Field(min_length=1)


class BootstrapCoordinator:
    """Establish one immutable baseline artifact and bind it to a durable run."""

    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        artifact_store: FilesystemArtifactStore,
        settings: Settings,
    ) -> None:
        self._sessions = sessions
        self._artifacts = artifact_store
        self._settings = settings

    async def establish(self, run_id: str) -> BootstrapResult:
        async with self._sessions() as session:
            run = await RunRepository(session).get(run_id)

        if run is None:
            raise KeyError(f"unknown run: {run_id}")
        if run.baseline_ref is not None:
            return BootstrapResult(
                baseline_ref=run.baseline_ref,
                base_commit=run.base_commit,
            )

        service = BootstrapService(self._artifacts)
        summary = service.run(Path(run.repo), run_id, self._settings)
        baseline_ref = service.persist_summary(run_id, summary)

        async with self._sessions() as session:
            repository = RunRepository(session)
            await repository.set_baseline(run_id, baseline_ref, summary.base_commit)
            await session.commit()

        return BootstrapResult(
            baseline_ref=baseline_ref,
            base_commit=summary.base_commit,
        )
