# grantflow/swarm/nodes/discovery.py

from __future__ import annotations

from typing import Any, Dict

from grantflow.core.strategies.factory import DonorFactory


def validate_input_richness(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Валидирует входные данные и загружает стратегию донора.
    """
    state.setdefault("errors", [])

    donor_id = state.get("donor") or state.get("donor_id")
    input_context = state.get("input") or state.get("input_context") or {}

    if not donor_id:
        state["errors"].append("Missing donor_id/donor")
        return state

    state["donor"] = donor_id
    state["donor_id"] = donor_id
    state["input"] = input_context
    state["input_context"] = input_context
    state.setdefault("iteration", int(state.get("iteration_count", 0) or 0))
    state.setdefault("quality_score", float(state.get("critic_score") or 0.0))
    state.setdefault("critic_notes", [])
    state.setdefault("needs_revision", False)
    state.setdefault("hitl_pending", False)

    try:
        if state.get("donor_strategy") is None:
            state["donor_strategy"] = DonorFactory.get_strategy(donor_id)
        # Backward compatibility for older nodes/tests.
        state["strategy"] = state["donor_strategy"]
    except ValueError as e:
        state["errors"].append(str(e))

    if not input_context.get("project"):
        state["errors"].append("Missing project description in input_context")

    return state
