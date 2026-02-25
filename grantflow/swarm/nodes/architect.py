# grantflow/swarm/nodes/architect.py

from __future__ import annotations

from typing import Any, Dict

from grantflow.swarm.citations import append_citations
from grantflow.swarm.nodes.architect_generation import generate_toc_under_contract
from grantflow.swarm.nodes.architect_retrieval import retrieve_architect_evidence
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

    namespace = strategy.get_rag_collection()
    retrieval_summary, retrieval_hits = retrieve_architect_evidence(state, namespace)

    try:
        toc, validation, generation_meta, claim_citations = generate_toc_under_contract(
            state=state,
            strategy=strategy,
            evidence_hits=retrieval_hits,
        )
    except Exception as exc:
        state.setdefault("errors", []).append(f"Architect ToC generation failed: {exc}")
        state["toc_validation"] = {
            "valid": False,
            "schema_name": getattr(getattr(strategy, "get_toc_schema", lambda: object)(), "__name__", "TOCSchema"),
            "error_count": 1,
            "errors": [str(exc)],
        }
        # Keep legacy-shaped fallback to avoid breaking downstream nodes in hard-failure scenarios.
        toc = {
            "brief": f"ToC draft for {donor_id} (pass {iteration + 1})",
            "project": input_context.get("project", "TBD project"),
            "country": input_context.get("country", "TBD"),
            "objectives": [
                {
                    "title": "Objective 1",
                    "description": f"Deliver results aligned to {donor_id} guidance.",
                    "citation": namespace,
                }
            ],
            "revision_basis": revision_hint,
        }
        generation_meta = {
            "engine": "fallback:legacy_template",
            "llm_used": False,
            "retrieval_used": bool(retrieval_hits),
            "llm_fallback_reason": str(exc),
        }
        claim_citations = [
            {
                "stage": "architect",
                "citation_type": "strategy_namespace",
                "namespace": namespace,
                "label": f"Based on {namespace}",
                "used_for": "toc_draft",
                "statement_path": "toc",
            }
        ]
        validation = state["toc_validation"]

    state["strategy"] = strategy
    state["toc"] = toc
    state["toc_validation"] = validation
    state["architect_retrieval"] = retrieval_summary
    state["toc_generation_meta"] = generation_meta
    state["toc_draft"] = {
        "toc": toc,
        "citation": f"Based on {namespace}",
        "generation_meta": generation_meta,
        "validation": validation,
        "architect_retrieval": retrieval_summary,
    }
    append_draft_version(
        state,
        section="toc",
        content=state["toc_draft"],
        node="architect",
        iteration=iteration + 1,
    )
    append_citations(state, claim_citations)
    return state
