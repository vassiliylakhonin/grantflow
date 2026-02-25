# grantflow/swarm/nodes/mel_specialist.py

from __future__ import annotations

from typing import Any, Dict

from grantflow.core.config import config
from grantflow.memory_bank.vector_store import vector_store
from grantflow.swarm.citations import append_citations
from grantflow.swarm.versioning import append_draft_version


def _build_query_text(state: Dict[str, Any]) -> str:
    input_context = state.get("input") or state.get("input_context") or {}
    project = input_context.get("project", "project")
    country = input_context.get("country", "")
    toc = state.get("toc_draft", {}) or {}
    brief = ((toc.get("toc") or {}).get("brief") if isinstance(toc, dict) else "") or ""
    parts = [str(project), str(country), str(brief)]
    return " | ".join([p for p in parts if p])


def mel_assign_indicators(state: Dict[str, Any]) -> Dict[str, Any]:
    """Назначает MEL индикаторы к ToC c RAG-запросом в namespace донора."""
    strategy = state.get("donor_strategy") or state.get("strategy")
    if not strategy:
        state.setdefault("errors", []).append("MEL cannot run without donor_strategy")
        return state

    namespace = strategy.get_rag_collection()
    query_text = _build_query_text(state)
    top_k = max(1, min(int(config.rag.default_top_k or 3), 3))

    indicators: list[dict[str, Any]] = []
    citation_records: list[dict[str, Any]] = []
    rag_trace: Dict[str, Any] = {
        "namespace": namespace,
        "query": query_text,
        "top_k": top_k,
        "used_results": 0,
    }

    try:
        result = vector_store.query(namespace=namespace, query_texts=[query_text], n_results=top_k)
        docs = ((result or {}).get("documents") or [[]])[0]
        metas = ((result or {}).get("metadatas") or [[]])[0]

        for idx, doc in enumerate(docs):
            meta = metas[idx] if idx < len(metas) and isinstance(metas[idx], dict) else {}
            citation = meta.get("citation") or meta.get("source") or f"{namespace}"
            indicators.append(
                {
                    "indicator_id": meta.get("indicator_id", f"IND_{idx+1:03d}"),
                    "name": meta.get("name", f"Indicator from {namespace} #{idx+1}"),
                    "justification": (
                        "Selected from donor-specific RAG collection " f"'{namespace}' based on project query."
                    ),
                    "citation": citation,
                    "baseline": meta.get("baseline", "TBD"),
                    "target": meta.get("target", "TBD"),
                    "evidence_excerpt": str(doc)[:240],
                }
            )
            citation_records.append(
                {
                    "stage": "mel",
                    "citation_type": "rag_result",
                    "namespace": namespace,
                    "source": meta.get("source"),
                    "page": meta.get("page"),
                    "page_start": meta.get("page_start"),
                    "page_end": meta.get("page_end"),
                    "chunk": meta.get("chunk"),
                    "chunk_id": meta.get("chunk_id"),
                    "label": citation,
                    "used_for": meta.get("indicator_id", f"IND_{idx+1:03d}"),
                    "excerpt": str(doc)[:240],
                    "citation_confidence": 0.8,
                    "evidence_score": 0.8,
                    "evidence_rank": idx + 1,
                }
            )
        rag_trace["used_results"] = len(indicators)
    except Exception as exc:
        state.setdefault("errors", []).append(f"MEL RAG query failed: {exc}")
        rag_trace["error"] = str(exc)

    if not indicators:
        indicators = [
            {
                "indicator_id": "IND_001",
                "name": "Project Output Indicator",
                "justification": ("Fallback indicator used because donor-specific RAG collection returned no results."),
                "citation": namespace,
                "baseline": "TBD",
                "target": "TBD",
            }
        ]
        citation_records.append(
            {
                "stage": "mel",
                "citation_type": "fallback_namespace",
                "namespace": namespace,
                "label": namespace,
                "used_for": "IND_001",
                "citation_confidence": 0.1,
                "evidence_score": 0.1,
            }
        )

    rag_trace["citation_count"] = len(citation_records)
    mel = {"indicators": indicators, "rag_trace": rag_trace, "citations": citation_records}
    state["mel"] = mel
    state["logframe_draft"] = mel
    append_draft_version(
        state,
        section="logframe",
        content=state["logframe_draft"],
        node="mel_specialist",
        iteration=int(state.get("iteration", state.get("iteration_count", 0)) or 0),
    )
    append_citations(state, citation_records)
    return state
