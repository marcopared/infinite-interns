"""Validated declarative configuration for InfiniteInterns."""

from pathlib import Path
from typing import Any, Literal, cast

import yaml  # pyright: ignore[reportMissingTypeStubs]
from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class StrictConfigModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SchedulerSettings(StrictConfigModel):
    lease_ttl_seconds: int = 90
    heartbeat_seconds: int = 30
    max_swe_workers: int = 4
    max_browser_workers: int = 2
    max_heavy_test_workers: int = 2
    max_integrations: int = 1

    @model_validator(mode="after")
    def validate_lease_timing(self) -> "SchedulerSettings":
        if self.lease_ttl_seconds <= self.heartbeat_seconds * 2:
            raise ValueError("lease TTL must exceed two heartbeat intervals")
        return self


class BudgetSettings(StrictConfigModel):
    deadline_hours: int = 8
    soft_model_usd: float = 200.0
    hard_model_usd: float = 300.0

    @model_validator(mode="after")
    def validate_budget_order(self) -> "BudgetSettings":
        if self.hard_model_usd < self.soft_model_usd:
            raise ValueError("hard model budget must be >= soft model budget")
        return self


class SecuritySettings(StrictConfigModel):
    profile: Literal["locked", "overnight", "trusted-production"] = "overnight"


class ModelSettings(StrictConfigModel):
    implementer: str = "codex"
    reviewer: str = "codex"
    adversary: str = "kimi-k3"
    diagnostician: str = "deepseek-v4-pro"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="INFINITE_INTERNS_",
        env_nested_delimiter="__",
        extra="forbid",
    )

    scheduler: SchedulerSettings = Field(default_factory=SchedulerSettings)
    budget: BudgetSettings = Field(default_factory=BudgetSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    models: ModelSettings = Field(default_factory=ModelSettings)


def load_settings(path: Path | None = None) -> Settings:
    if path is None:
        return Settings()

    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if loaded is None:
        return Settings()
    if not isinstance(loaded, dict):
        raise TypeError("configuration root must be a mapping")

    data = cast(dict[str, Any], loaded)
    return Settings.model_validate(data)
