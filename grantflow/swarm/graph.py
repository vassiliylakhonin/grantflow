# grantflow/swarm/graph.py

from __future__ import annotations

from langgraph.graph import END, StateGraph

from grantflow.swarm.nodes.architect import draft_toc
from grantflow.swarm.nodes.critic import red_team_critic
from grantflow.swarm.nodes.discovery import validate_input_richness
from grantflow.swarm.nodes.mel_specialist import mel_assign_indicators


def build_graph():
    g = StateGraph(dict)

    g.add_node("discovery", validate_input_richness)
    g.add_node("architect", draft_toc)
    g.add_node("mel", mel_assign_indicators)
    g.add_node("critic", red_team_critic)

    g.set_entry_point("discovery")
    g.add_edge("discovery", "architect")
    g.add_edge("architect", "mel")
    g.add_edge("mel", "critic")

    def route_after_critic(state: dict):
        if state.get("needs_revision"):
            return "architect"
        return END

    g.add_conditional_edges(
        "critic",
        route_after_critic,
        {
            "architect": "architect",
            END: END,
        },
    )

    return g.compile()


def build_grantflow_graph():
    return build_graph()


grantflow_graph = build_graph()
