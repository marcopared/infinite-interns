from datetime import UTC, datetime, timedelta

from infinite_interns.recovery.service import (
    ProgressSnapshot,
    RecoveryActionKind,
    RecoveryService,
)


def test_missing_heartbeat_expires_before_other_stall_rules() -> None:
    now = datetime.now(UTC)
    snapshot = ProgressSnapshot(
        last_heartbeat=now - timedelta(seconds=91),
        last_agent_event=now - timedelta(minutes=15),
        last_semantic_progress=now - timedelta(minutes=30),
    )
    action = RecoveryService.classify("TASK-1", snapshot, now)
    assert action.kind is RecoveryActionKind.EXPIRE_LEASE


def test_live_worker_without_agent_event_gets_probe() -> None:
    now = datetime.now(UTC)
    snapshot = ProgressSnapshot(
        last_heartbeat=now - timedelta(seconds=10),
        last_agent_event=now - timedelta(minutes=11),
        last_semantic_progress=now - timedelta(minutes=5),
    )
    action = RecoveryService.classify("TASK-1", snapshot, now)
    assert action.kind is RecoveryActionKind.PROBE


def test_no_semantic_progress_routes_to_stall_escalation() -> None:
    now = datetime.now(UTC)
    snapshot = ProgressSnapshot(
        last_heartbeat=now - timedelta(seconds=10),
        last_agent_event=now - timedelta(minutes=2),
        last_semantic_progress=now - timedelta(minutes=21),
    )
    action = RecoveryService.classify("TASK-1", snapshot, now)
    assert action.kind is RecoveryActionKind.STALLED
