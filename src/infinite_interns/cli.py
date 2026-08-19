"""Operator CLI for InfiniteInterns."""

import asyncio
import os
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from infinite_interns.db.engine import create_engine, create_session_factory
from infinite_interns.db.repositories import RunRepository
from infinite_interns.doctor import DoctorReport, run_doctor
from infinite_interns.domain.models import RunRecord

app = typer.Typer(no_args_is_help=True)
console = Console()


@app.command()
def doctor() -> None:
    """Check whether the local environment is ready for InfiniteInterns."""
    report = run_doctor()
    _render_doctor(report)
    if not report.ready:
        raise typer.Exit(code=1)


@app.command()
def status(run: Annotated[str, typer.Option("--run", help="Run identifier")]) -> None:
    """Display durable status for one factory run."""
    database_url = os.environ.get("INFINITE_INTERNS_DATABASE_URL")
    if not database_url:
        console.print("[red]INFINITE_INTERNS_DATABASE_URL is not set[/red]")
        raise typer.Exit(code=2)

    record = asyncio.run(_load_run(database_url, run))
    if record is None:
        console.print(f"[red]Run not found:[/red] {run}")
        raise typer.Exit(code=3)

    table = Table(title=f"InfiniteInterns run {record.run_id}")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("status", record.status.value)
    table.add_row("repo", record.repo)
    table.add_row("base commit", record.base_commit)
    table.add_row("started", record.started_at.isoformat())
    console.print(table)


async def _load_run(database_url: str, run_id: str) -> RunRecord | None:
    engine = create_engine(database_url)
    sessions = create_session_factory(engine)
    try:
        async with sessions() as session:
            return await RunRepository(session).get(run_id)
    finally:
        await engine.dispose()


def _render_doctor(report: DoctorReport) -> None:
    table = Table(title="InfiniteInterns doctor")
    table.add_column("Check")
    table.add_column("Status")
    table.add_column("Detail")
    for result in report.results:
        table.add_row(result.name, "PASS" if result.ok else "FAIL", result.detail)
    console.print(table)
