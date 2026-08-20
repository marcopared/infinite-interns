from infinite_interns.planning.traceability import (
    TraceCriterion,
    TraceJustificationKind,
    TraceOracleGate,
    TraceTask,
    TraceabilityErrorCode,
    TraceabilityGraph,
)


def _codes(graph: TraceabilityGraph) -> set[TraceabilityErrorCode]:
    return {error.code for error in graph.validate()}


def test_required_requirement_needs_criteria_oracle_and_task() -> None:
    graph = TraceabilityGraph(requirement_ids=("REQ-JOBS-001",))

    assert _codes(graph) == {
        TraceabilityErrorCode.REQUIREMENT_WITHOUT_CRITERIA,
        TraceabilityErrorCode.REQUIREMENT_WITHOUT_ORACLE,
        TraceabilityErrorCode.REQUIREMENT_WITHOUT_TASK,
    }


def test_unknown_links_are_reported_not_silently_accepted() -> None:
    graph = TraceabilityGraph(
        requirement_ids=("REQ-JOBS-001",),
        criteria=(TraceCriterion(criterion_id="AC-1", requirement_id="REQ-MISSING"),),
        oracle_gates=(
            TraceOracleGate(
                gate_id="GATE-1",
                requirement_id="REQ-JOBS-001",
                criterion_ids=("AC-MISSING",),
            ),
        ),
        tasks=(
            TraceTask(
                task_id="TASK-1",
                requirement_ids=("REQ-MISSING",),
                verification_gate_ids=("GATE-MISSING",),
            ),
        ),
    )

    assert TraceabilityErrorCode.UNKNOWN_REFERENCE in _codes(graph)


def test_task_without_requirement_or_explicit_architecture_release_justification_is_rejected() -> None:
    graph = TraceabilityGraph(
        requirement_ids=("REQ-JOBS-001",),
        criteria=(TraceCriterion(criterion_id="AC-1", requirement_id="REQ-JOBS-001"),),
        oracle_gates=(
            TraceOracleGate(
                gate_id="GATE-1",
                requirement_id="REQ-JOBS-001",
                criterion_ids=("AC-1",),
            ),
        ),
        tasks=(TraceTask(task_id="TASK-ORPHAN"),),
    )

    assert TraceabilityErrorCode.TASK_WITHOUT_JUSTIFICATION in _codes(graph)


def test_release_task_can_be_explicitly_justified_without_product_requirement() -> None:
    graph = TraceabilityGraph(
        requirement_ids=("REQ-JOBS-001",),
        criteria=(TraceCriterion(criterion_id="AC-1", requirement_id="REQ-JOBS-001"),),
        oracle_gates=(
            TraceOracleGate(
                gate_id="GATE-1",
                requirement_id="REQ-JOBS-001",
                criterion_ids=("AC-1",),
            ),
        ),
        tasks=(
            TraceTask(
                task_id="TASK-FEATURE",
                requirement_ids=("REQ-JOBS-001",),
                verification_gate_ids=("GATE-1",),
            ),
            TraceTask(
                task_id="TASK-RELEASE",
                justification_kind=TraceJustificationKind.RELEASE,
            ),
        ),
    )

    assert graph.validate() == ()
