"""Pure task dependency graph validation and readiness calculation."""

import heapq
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType

from infinite_interns.domain.enums import TaskStatus


class DagCycleError(ValueError):
    """Raised when a task dependency graph contains a cycle."""


@dataclass(frozen=True)
class TaskDag:
    """Immutable directed acyclic task graph.

    Edges are expressed as ``(dependency, dependent)``. The graph contains no
    persistence behavior; callers decide how READY state is materialized.
    """

    parents_by_task: Mapping[str, frozenset[str]]
    children_by_task: Mapping[str, frozenset[str]]

    @classmethod
    def from_edges(cls, edges: Sequence[tuple[str, str]]) -> "TaskDag":
        parents: dict[str, set[str]] = {}
        children: dict[str, set[str]] = {}

        for dependency, dependent in edges:
            if not dependency or not dependent:
                raise ValueError("task IDs in DAG edges must be non-empty")
            parents.setdefault(dependency, set())
            parents.setdefault(dependent, set()).add(dependency)
            children.setdefault(dependency, set()).add(dependent)
            children.setdefault(dependent, set())

        return cls(
            parents_by_task=MappingProxyType(
                {task: frozenset(values) for task, values in parents.items()}
            ),
            children_by_task=MappingProxyType(
                {task: frozenset(values) for task, values in children.items()}
            ),
        )

    @property
    def task_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self.parents_by_task))

    def validate_acyclic(self) -> None:
        """Validate the graph with Kahn's algorithm using deterministic ordering."""

        indegree = {task: len(parents) for task, parents in self.parents_by_task.items()}
        ready = [task for task, degree in indegree.items() if degree == 0]
        heapq.heapify(ready)
        visited = 0

        while ready:
            task = heapq.heappop(ready)
            visited += 1
            for child in sorted(self.children_by_task[task]):
                indegree[child] -= 1
                if indegree[child] == 0:
                    heapq.heappush(ready, child)

        if visited != len(indegree):
            cyclic = tuple(sorted(task for task, degree in indegree.items() if degree > 0))
            raise DagCycleError(f"task DAG contains a cycle involving: {', '.join(cyclic)}")

    def ready_tasks(self, status_by_task: Mapping[str, TaskStatus]) -> tuple[str, ...]:
        """Return dependency-safe work candidates in lexical order.

        Only PLANNED/READY tasks are candidates. Every upstream dependency must
        already be DONE or VERIFIED. This function never mutates task state.
        """

        self.validate_acyclic()
        missing = tuple(sorted(set(self.parents_by_task) - set(status_by_task)))
        if missing:
            raise KeyError(f"missing task statuses for: {', '.join(missing)}")

        satisfied = {TaskStatus.DONE, TaskStatus.VERIFIED}
        eligible = {TaskStatus.PLANNED, TaskStatus.READY}
        ready: list[str] = []

        for task in sorted(self.parents_by_task):
            if status_by_task[task] not in eligible:
                continue
            parents = self.parents_by_task[task]
            if all(status_by_task[parent] in satisfied for parent in parents):
                ready.append(task)

        return tuple(ready)
