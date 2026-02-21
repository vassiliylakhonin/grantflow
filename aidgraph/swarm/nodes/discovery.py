# aidgraph/swarm/nodes/discovery.py

from __future__ import annotations

from typing import Dict, Any
from aidgraph.core.strategies.factory import strategy_factory

def validate_input_richness(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Валидирует входные данные и загружает стратегию донора.
    """
    donor_id = state.get("donor_id")
    input_context = state.get("input_context", {})
    
    if not donor_id:
        state["errors"].append("Missing donor_id")
        return state
    
    try:
        strategy = strategy_factory(donor_id)
        state["strategy"] = strategy
    except ValueError as e:
        state["errors"].append(str(e))
    
    if not input_context.get("project"):
        state["errors"].append("Missing project description in input_context")
    
    return state
