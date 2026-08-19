# Task 3 brief — configuration profiles and validation

Implement Stage 1 Task 3 from `2026-08-18-stage-1-deterministic-foundation.md`.

Required interfaces:

- `Settings`
- `SchedulerSettings`
- `BudgetSettings`
- `SecuritySettings`
- `ModelSettings`
- `load_settings(path: Path | None) -> Settings`

Required overnight defaults:

- lease TTL: 90 seconds
- heartbeat: 30 seconds
- max SWE workers: 4
- max browser workers: 2
- max heavy-test workers: 2
- max integrations: 1
- deadline: 8 hours
- soft model budget: $200
- hard model budget: $300

Validation:

- hard model budget must be >= soft model budget
- lease TTL must be greater than 2x heartbeat interval

Configuration remains declarative; no scheduler or model authority belongs in this module.
