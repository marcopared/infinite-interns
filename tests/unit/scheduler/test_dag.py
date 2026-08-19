import pytest

from infinite_interns.domain.enums import TaskStatus
from infinite_interns.scheduler.dag import DagCycleError, TaskDag


def test_cycle_is_rejected() -> None:
    dag = TaskDag.from_edges((('A', 'B'), ('B', 'C'), ('C', 'A')))
    with pytest.raises(DagCycleError):
        dag.validate_acyclic()


def test_roots_are_ready_in_lexical_order() -> None:
    dag = TaskDag.from_edges((('B', 'C'), ('A', 'C')))
    statuses = {'A': TaskStatus.PLANNED, 'B': TaskStatus.PLANNED, 'C': TaskStatus.PLANNED}
    assert dag.ready_tasks(statuses) == ('A', 'B')


def test_downstream_waits_for_every_dependency() -> None:
    dag = TaskDag.from_edges((('A', 'C'), ('B', 'C')))
    statuses = {'A': TaskStatus.DONE, 'B': TaskStatus.RUNNING, 'C': TaskStatus.PLANNED}
    assert 'C' not in dag.ready_tasks(statuses)


def test_done_and_verified_dependencies_satisfy_readiness() -> None:
    dag = TaskDag.from_edges((('A', 'C'), ('B', 'C')))
    statuses = {'A': TaskStatus.DONE, 'B': TaskStatus.VERIFIED, 'C': TaskStatus.PLANNED}
    assert dag.ready_tasks(statuses) == ('C',)
