# grantflow/swarm/nodes/discovery.py

from __future__ import annotations

from typing import Any, Dict

from grantflow.core.strategies.factory import DonorFactory
from grantflow.swarm.state_contract import normalize_state_contract, state_donor_id, state_input_context


def validate_input_richness(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Валидирует входные данные и загружает стратегию донора.
    """
    normalize_state_contract(state)
    donor_id = state_donor_id(state)
    input_context = state_input_context(state)

    if not donor_id:
        state["errors"].append("Missing donor_id/donor")
        return state

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
