import os
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from infinite_interns.api.app import app
from infinite_interns.artifacts.filesystem import FilesystemArtifactStore
from infinite_interns.bootstrap.coordinator import (
    BootstrapCoordinator,
    BootstrapResult,
)
from infinite_interns.bootstrap.models import BaselineSummary, RepositoryKind
from infinite_interns.bootstrap.service import BootstrapService
from infinite_interns.config import Settings
from infinite_interns.db.engine import create_engine, create_session_factory
from infinite_interns.db.repositories import RunRepository
from infinite_interns.domain.enums import RunStatus
from infinite_interns.domain.models import RunRecord
from infinite_interns.graph.factory import graph
from infinite_interns.graph.nodes import (
    FactoryGraphServices,
    MissingBaselineError,
    configure_services,
)
from infinite_interns.graph.state import FactoryState


@pytest.mark.asyncio
async def test_bootstrap_persists_compact_baseline_reference(tmp_path: Path) -> None:
    repo = tmp_path / "product"
    repo.mkdir()
    run_id = f"run_{uuid4().hex}"
    store = FilesystemArtifactStore(tmp_path / "artifacts")
    engine = create_engine(os.environ["INFINITE_INTERNS_DATABASE_URL"])
    sessions = create_session_factory(engine)

    try:
        async with sessions() as session:
            await RunRepository(session).add(
                RunRecord(
                    run_id=run_id,
                    repo=str(repo),
                    base_commit="pending-bootstrap",
                    status=RunStatus.CREATED,
                    started_at=datetime.now(UTC),
                )
            )
            await session.commit()

        result = await BootstrapCoordinator(sessions, store, Settings()).establish(run_id)

        async with sessions() as session:
            stored = await RunRepository(session).get(run_id)

        assert stored is not None
        assert stored.baseline_ref == result.baseline_ref
        assert stored.base_commit == result.base_commit
        summary = BaselineSummary.model_validate_json(store.get(result.baseline_ref))
        assert summary.repo_kind is RepositoryKind.GREENFIELD
        assert summary.base_commit == result.base_commit
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_bootstrap_retry_recovers_artifact_written_before_db_commit(tmp_path: Path) -> None:
    repo = tmp_path / "crash-product"
    repo.mkdir()
    run_id = f"run_{uuid4().hex}"
    store = FilesystemArtifactStore(tmp_path / "artifacts")
    settings = Settings()
    engine = create_engine(os.environ["INFINITE_INTERNS_DATABASE_URL"])
    sessions = create_session_factory(engine)

    try:
        async with sessions() as session:
            await RunRepository(session).add(
                RunRecord(
                    run_id=run_id,
                    repo=str(repo),
                    base_commit="pending-bootstrap",
                    status=RunStatus.CREATED,
                    started_at=datetime.now(UTC),
                )
            )
            await session.commit()

        service = BootstrapService(store)
        orphaned_summary = service.run(repo, run_id, settings)
        orphaned_ref = service.persist_summary(run_id, orphaned_summary)

        result = await BootstrapCoordinator(sessions, store, settings).establish(run_id)

        async with sessions() as session:
            stored = await RunRepository(session).get(run_id)

        assert result.baseline_ref == orphaned_ref
        assert result.base_commit == orphaned_summary.base_commit
        assert stored is not None
        assert stored.baseline_ref == orphaned_ref
        assert stored.base_commit == orphaned_summary.base_commit
    finally:
        await engine.dispose()


class _FakeBootstrap:
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def establish(self, run_id: str) -> BootstrapResult:
        self.calls.append(run_id)
        return BootstrapResult(
            baseline_ref="artifact://runs/run_graph/baseline/summary-abc",
            base_commit="abc",
        )


@pytest.mark.asyncio
async def test_parent_graph_bootstraps_before_specification_entry() -> None:
    fake = _FakeBootstrap()
    configure_services(FactoryGraphServices(bootstrap_establisher=fake))
    try:
        result = await graph.ainvoke(  # pyright: ignore[reportUnknownMemberType]
            FactoryState(run_id="run_graph")
        )
    finally:
        configure_services(FactoryGraphServices())

    assert fake.calls == ["run_graph"]
    assert result["baseline_ref"] == "artifact://runs/run_graph/baseline/summary-abc"
    assert result["current_commit"] == "abc"


@pytest.mark.asyncio
async def test_specification_entry_refuses_missing_baseline() -> None:
    services = FactoryGraphServices()
    with pytest.raises(MissingBaselineError):
        await services.specification_pending(FactoryState(run_id="run_missing"))


@pytest.mark.asyncio
async def test_agent_server_lifespan_wires_real_bootstrap(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "runtime-product"
    repo.mkdir()
    run_id = f"run_{uuid4().hex}"
    artifact_root = tmp_path / "runtime-artifacts"
    monkeypatch.setenv("INFINITE_INTERNS_ARTIFACT_ROOT", str(artifact_root))

    engine = create_engine(os.environ["INFINITE_INTERNS_DATABASE_URL"])
    sessions = create_session_factory(engine)
    try:
        async with sessions() as session:
            await RunRepository(session).add(
                RunRecord(
                    run_id=run_id,
                    repo=str(repo),
                    base_commit="pending-bootstrap",
                    status=RunStatus.CREATED,
                    started_at=datetime.now(UTC),
                )
            )
            await session.commit()

        async with app.router.lifespan_context(app):
            result = await graph.ainvoke(  # pyright: ignore[reportUnknownMemberType]
                FactoryState(run_id=run_id)
            )

        async with sessions() as session:
            stored = await RunRepository(session).get(run_id)

        assert stored is not None
        assert stored.baseline_ref == result["baseline_ref"]
        assert stored.base_commit == result["current_commit"]
        assert artifact_root.exists()
    finally:
        await engine.dispose()
