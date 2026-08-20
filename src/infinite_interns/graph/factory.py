"""Compiled parent graph exported to the LangGraph Agent Server."""

# LangGraph currently ships this public module without a complete Pyright stub surface.
# Keep that untyped boundary confined to this adapter; factory services and state remain strict.
# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false

from langgraph.graph import END, START, StateGraph

from infinite_interns.graph.nodes import bootstrap, specification_pending
from infinite_interns.graph.state import FactoryState

_builder = StateGraph(FactoryState)
_builder.add_node("bootstrap", bootstrap)
_builder.add_node("specification_pending", specification_pending)
_builder.add_edge(START, "bootstrap")
_builder.add_edge("bootstrap", "specification_pending")
_builder.add_edge("specification_pending", END)

graph = _builder.compile()
