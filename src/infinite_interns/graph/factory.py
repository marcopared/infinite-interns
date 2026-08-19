"""Compiled parent graph exported to the LangGraph Agent Server."""

from infinite_interns.graph.nodes import load_run, schedule, wait_or_finish
from infinite_interns.graph.state import FactoryState
from langgraph.graph import END, START, StateGraph


_builder = StateGraph(FactoryState)
_builder.add_node("load_run", load_run)
_builder.add_node("schedule", schedule)
_builder.add_node("wait_or_finish", wait_or_finish)
_builder.add_edge(START, "load_run")
_builder.add_edge("load_run", "schedule")
_builder.add_edge("schedule", "wait_or_finish")
_builder.add_edge("wait_or_finish", END)

graph = _builder.compile()
