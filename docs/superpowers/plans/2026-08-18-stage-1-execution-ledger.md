# Stage 1 execution ledger

Plan: `docs/superpowers/plans/2026-08-18-stage-1-deterministic-foundation.md`
Branch: `impl/stage-1-deterministic-foundation`

This tracked ledger is a portability fallback because the current ChatGPT execution environment cannot maintain the skill's normal git-ignored local `.superpowers/sdd/.../progress.md` workspace. It records task/review state without storing model chain-of-thought.

## Preflight

- Architecture source reachable: yes.
- Stage 1 is deterministic and contains no live-model dependency.
- Task 1 requires TDD for `__version__`; CI is used as the executable test environment because the local container cannot resolve GitHub.
- Ruling: `uv.lock` will be generated as soon as an execution environment capable of running `uv lock` is available. Until then CI uses `uv sync --dev` rather than `--locked`; this does not weaken Stage 1 behavioral authority, but it is a reproducibility debt that must be closed before Stage 1 completion.

## Progress

Task 1: RED pending — smoke test and CI scaffolding committed; `__version__` intentionally absent.
