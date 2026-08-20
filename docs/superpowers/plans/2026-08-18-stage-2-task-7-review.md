# Stage 2 Task 7 review

## Spec compliance

**PASS.**

Integration is single-writer per run, anchored to durable `last_green_commit`, regression-gated, and stale expected anchors fail closed. A regression-failing candidate cannot move the durable green anchor or leave the checkout on the failed candidate.

## Code quality

**PASS.**

- long integration serialization uses a dedicated PostgreSQL advisory-lock connection rather than holding a row lock or persistence transaction across regression execution;
- persistence writes remain short transactions;
- stale concurrent submissions become explicit `CONFLICT` results;
- candidate application uses argv-only Git commands;
- rejection restores by switching detached HEAD to the previous green SHA rather than destructive reset;
- run-specific Git refs keep accepted detached commits reachable;
- DB advancement uses a compare-on-expected-last-green update.

## Findings

Minor — Git and PostgreSQL cannot be updated atomically. The current ordering can leave the auxiliary integration ref ahead of DB state if a database failure occurs after ref advancement. This cannot create a false green because PostgreSQL remains authoritative; subsequent integration detects checkout/DB drift and stops. A later recovery-hardening pass should reconcile the auxiliary ref from the DB anchor automatically.

Minor — initialization persists DB state before creating the auxiliary ref. A ref-creation failure similarly cannot produce false success, but should become repairable recovery state later.

No Critical or Important findings.

## Verdict

Spec: PASS.

Quality: PASS.

Ready for Stage 2 Task 8 certification.
