import pytest

from infinite_interns.config import Settings


def test_overnight_defaults_match_architecture() -> None:
    settings = Settings()
    assert settings.scheduler.lease_ttl_seconds == 90
    assert settings.scheduler.heartbeat_seconds == 30
    assert settings.scheduler.max_swe_workers == 4
    assert settings.scheduler.max_browser_workers == 2
    assert settings.scheduler.max_heavy_test_workers == 2
    assert settings.scheduler.max_integrations == 1
    assert settings.budget.deadline_hours == 8
    assert settings.budget.soft_model_usd == 200
    assert settings.budget.hard_model_usd == 300


def test_hard_budget_cannot_be_below_soft_budget() -> None:
    with pytest.raises(ValueError):
        Settings(budget={"soft_model_usd": 300, "hard_model_usd": 200})


def test_lease_ttl_must_exceed_two_heartbeat_intervals() -> None:
    with pytest.raises(ValueError):
        Settings(scheduler={"lease_ttl_seconds": 60, "heartbeat_seconds": 30})
