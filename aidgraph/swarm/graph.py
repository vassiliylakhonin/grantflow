# aidgraph/swarm/graph.py

from __future__ import annotations

from typing import Literal
from langgraph.graph import StateGraph, END
from aidgraph.core.state import AidGraphState

def should_loop(state: AidGraphState) -> Literal["architect", "mel_specialist"]:
    """
    Решает, продолжать ли цикл или идти к завершению.
    """
    score = state.get("critic_score")
    iterations = state.get("iteration_count", 0)
    max_iters = state.get("max_iterations", 3)
    
    if score is not None and score >= 8.0:
        return "mel_specialist"
    if iterations >= max_iters:
        return "mel_specialist"
    return "architect"

def build_aidgraph_graph() -> StateGraph:
    """
    Строит StateGraph для AidGraph с циклической обработкой.
    """
    graph = StateGraph(AidGraphState)
    
    # Добавляем узлы (заглушки — реальная логика в nodes/)
    graph.add_node("discovery", lambda s: s)
    graph.add_node("architect", lambda s: s)
    graph.add_node("mel_specialist", lambda s: s)
    graph.add_node("critic", lambda s: s)
    
    # Рёбра
    graph.set_entry_point("discovery")
    graph.add_edge("discovery", "architect")
    graph.add_conditional_edges(
        "architect",
        should_loop,
        {
            "architect": "architect",
            "mel_specialist": "mel_specialist"
        }
    )
    graph.add_edge("mel_specialist", "critic")
    graph.add_conditional_edges(
        "critic",
        should_loop,
        {
            "architect": "architect",
            "mel_specialist": "mel_specialist"
        }
    )
    graph.add_edge("critic", END)
    
    return graph.compile()

aidgraph_graph = build_aidgraph_graph()
