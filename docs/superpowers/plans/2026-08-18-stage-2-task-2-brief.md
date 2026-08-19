# Stage 2 Task 2 brief — deterministic DAG validation and readiness

Implement Task 2 from `2026-08-18-stage-2-orchestration-execution.md`.

Required outcomes:

- represent directed task dependencies as an immutable `TaskDag`;
- reject cycles using deterministic Kahn topological validation;
- return READY candidates in lexical order;
- consider upstream work satisfied only when every parent is `DONE` or `VERIFIED`;
- never mutate database/task state from DAG calculation;
- reject incomplete status maps rather than guessing;
- keep the graph representation deeply immutable after construction.
