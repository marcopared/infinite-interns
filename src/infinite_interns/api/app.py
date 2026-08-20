"""Custom HTTP routes and runtime composition for the LangGraph Agent Server."""

import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from infinite_interns.artifacts.filesystem import FilesystemArtifactStore
from infinite_interns.bootstrap.coordinator import BootstrapCoordinator
from infinite_interns.config import Settings
from infinite_interns.db.engine import create_engine, create_session_factory
from infinite_interns.graph.nodes import FactoryGraphServices, configure_services


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None]:
    database_url = os.environ.get("INFINITE_INTERNS_DATABASE_URL")
    if not database_url:
        raise RuntimeError("INFINITE_INTERNS_DATABASE_URL is required")

    engine = create_engine(database_url)
    sessions = create_session_factory(engine)
    artifact_root = Path(
        os.environ.get("INFINITE_INTERNS_ARTIFACT_ROOT", ".infinite-interns/artifacts")
    )
    coordinator = BootstrapCoordinator(
        sessions,
        FilesystemArtifactStore(artifact_root),
        Settings(),
    )
    configure_services(FactoryGraphServices(bootstrap_establisher=coordinator))
    try:
        yield
    finally:
        configure_services(FactoryGraphServices())
        await engine.dispose()


app = FastAPI(lifespan=lifespan)


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
