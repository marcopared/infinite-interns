from typer.testing import CliRunner

from infinite_interns.cli import app

runner = CliRunner()


def test_cli_exposes_doctor_and_status_commands() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "doctor" in result.stdout
    assert "status" in result.stdout


def test_status_requires_run_option() -> None:
    result = runner.invoke(app, ["status"])
    assert result.exit_code != 0
