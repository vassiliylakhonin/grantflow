# grantflow/swarm/nodes/architect.py

from __future__ import annotations

from typing import Dict, Any

from grantflow.swarm.citations import append_citations
from grantflow.swarm.versioning import append_draft_version


def draft_toc(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Создаёт черновик Theory of Change.
    """
    strategy = state.get("donor_strategy") or state.get("strategy")
    iteration = int(state.get("iteration", state.get("iteration_count", 0)) or 0)
    donor_id = state.get("donor") or state.get("donor_id")
    input_context = state.get("input") or state.get("input_context") or {}
    critic_notes = state.get("critic_notes")

    if not strategy:
        state.setdefault("errors", []).append("Architect cannot run without donor_strategy")
        return state

    revision_hint = ""
    if isinstance(critic_notes, dict):
        revision_hint = str(critic_notes.get("revision_instructions", ""))
    elif isinstance(critic_notes, str):
        revision_hint = critic_notes

    toc = {
        "brief": f"ToC draft for {donor_id} (pass {iteration + 1})",
        "project": input_context.get("project", "TBD project"),
        "country": input_context.get("country", "TBD"),
        "objectives": [
            {
                "title": "Objective 1",
                "description": f"Deliver results aligned to {donor_id} guidance.",
                "citation": strategy.get_rag_collection(),
            }
        ],
        "revision_basis": revision_hint,
    }

    state["strategy"] = strategy
    state["toc"] = toc
    state["toc_draft"] = {
        "toc": toc,
        "citation": f"Based on {strategy.get_rag_collection()}",
    }
    append_draft_version(
        state,
        section="toc",
        content=state["toc_draft"],
        node="architect",
        iteration=iteration + 1,
    )
    append_citations(
        state,
        [
            {
                "stage": "architect",
                "citation_type": "strategy_namespace",
                "namespace": strategy.get_rag_collection(),
                "label": f"Based on {strategy.get_rag_collection()}",
                "used_for": "toc_draft",
            }
        ],
    )
    return state
