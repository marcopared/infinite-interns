# Task 7 brief — doctor/status CLI and Stage 1 acceptance

Implement Stage 1 Task 7 from `2026-08-18-stage-1-deterministic-foundation.md`.

Required operator surface:

- `interns doctor`
- `interns status --run <id>`

Doctor checks Python version, Git executable, Docker executable, PostgreSQL connectivity, and artifact-root writability. The doctor core must accept injected checks for deterministic unit tests.

Stage 1 acceptance must:

1. create one run and two requirements;
2. persist the release-policy artifact outside PostgreSQL;
3. add current green evidence for all but one mandatory gate and prove release is not PASS;
4. add the final current mandatory evidence and prove release becomes PASS;
5. change the current commit identity without regenerating evidence and prove release becomes non-PASS with stale evidence reported.

This task may display status but may not introduce any write of `RunStatus.DONE`.
