# grantflow/swarm/graph.py

from __future__ import annotations

from langgraph.graph import END, StateGraph

from grantflow.swarm.nodes.architect import draft_toc
from grantflow.swarm.nodes.critic import red_team_critic
from grantflow.swarm.nodes.discovery import validate_input_richness
from grantflow.swarm.nodes.mel_specialist import mel_assign_indicators
from grantflow.swarm.state_contract import normalize_state_contract


def _start_node(state: dict) -> dict:
    return state


def _resolve_start_node(state: dict) -> str:
    start_at = str(state.get("_start_at") or "start").strip().lower()
    if start_at in {"start", "discovery"}:
        return "discovery"
    if start_at in {"architect", "mel", "critic"}:
        return start_at
    return "discovery"


def _toc_hitl_gate(state: dict) -> dict:
    normalize_state_contract(state)
    if not bool(state.get("hitl_enabled", False)):
        state["hitl_pending"] = False
        state.pop("hitl_checkpoint_stage", None)
        state.pop("hitl_resume_from", None)
        return state

    state["hitl_pending"] = True
    state["hitl_checkpoint_stage"] = "toc"
    state["hitl_resume_from"] = "mel"
    return state


def _route_after_toc_gate(state: dict):
    if bool(state.get("hitl_pending", False)):
        return END
    return "mel"


def _logframe_hitl_gate(state: dict) -> dict:
    normalize_state_contract(state)
    if not bool(state.get("hitl_enabled", False)):
        state["hitl_pending"] = False
        state.pop("hitl_checkpoint_stage", None)
        state.pop("hitl_resume_from", None)
        return state

    state["hitl_pending"] = True
    state["hitl_checkpoint_stage"] = "logframe"
    state["hitl_resume_from"] = "critic"
    return state


def _route_after_logframe_gate(state: dict):
    if bool(state.get("hitl_pending", False)):
        return END
    return "critic"


def build_graph():
    g = StateGraph(dict)

    g.add_node("start", _start_node)
    g.add_node("discovery", validate_input_richness)
    g.add_node("architect", draft_toc)
    g.add_node("toc_hitl_gate", _toc_hitl_gate)
    g.add_node("mel", mel_assign_indicators)
    g.add_node("logframe_hitl_gate", _logframe_hitl_gate)
    g.add_node("critic", red_team_critic)

    g.set_entry_point("start")
    g.add_conditional_edges(
        "start",
        _resolve_start_node,
        {
            "discovery": "discovery",
            "architect": "architect",
            "mel": "mel",
            "critic": "critic",
        },
    )

    g.add_edge("discovery", "architect")
    g.add_edge("architect", "toc_hitl_gate")
    g.add_conditional_edges(
        "toc_hitl_gate",
        _route_after_toc_gate,
        {
            "mel": "mel",
            END: END,
        },
    )

    g.add_edge("mel", "logframe_hitl_gate")
    g.add_conditional_edges(
        "logframe_hitl_gate",
        _route_after_logframe_gate,
        {
            "critic": "critic",
            END: END,
        },
    )

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
