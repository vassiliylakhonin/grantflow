# grantflow/swarm/nodes/mel_specialist.py

from __future__ import annotations

from typing import Any, Dict

from grantflow.core.config import config
from grantflow.memory_bank.vector_store import vector_store
from grantflow.swarm.citation_source import citation_label_from_metadata, citation_source_from_metadata
from grantflow.swarm.citations import append_citations
from grantflow.swarm.state_contract import normalize_state_contract, state_input_context
from grantflow.swarm.versioning import append_draft_version


def _build_query_text(state: Dict[str, Any]) -> str:
    input_context = state_input_context(state)
    project = input_context.get("project", "project")
    country = input_context.get("country", "")
    toc = state.get("toc_draft", {}) or {}
    brief = ((toc.get("toc") or {}).get("brief") if isinstance(toc, dict) else "") or ""
    parts = [str(project), str(country), str(brief)]
    return " | ".join([p for p in parts if p])


def mel_assign_indicators(state: Dict[str, Any]) -> Dict[str, Any]:
    """Назначает MEL индикаторы к ToC c RAG-запросом в namespace донора."""
    normalize_state_contract(state)
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
        ids = ((result or {}).get("ids") or [[]])[0]
        distances = ((result or {}).get("distances") or [[]])[0]

        for idx, doc in enumerate(docs):
            meta = metas[idx] if idx < len(metas) and isinstance(metas[idx], dict) else {}
            rank = idx + 1
            doc_id = meta.get("doc_id") or meta.get("chunk_id") or (ids[idx] if idx < len(ids) else None)
            raw_distance = distances[idx] if idx < len(distances) else None
            if isinstance(raw_distance, (int, float)):
                retrieval_confidence = round(max(0.0, min(1.0, 1.0 / (1.0 + float(raw_distance)))), 4)
            else:
                retrieval_confidence = round(max(0.1, 1.0 - (idx * 0.2)), 4)
            source = citation_source_from_metadata(meta)
            citation = citation_label_from_metadata(meta, namespace=namespace, rank=rank)
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
            rag_trace.setdefault("hits", []).append(
                {
                    "retrieval_rank": rank,
                    "doc_id": doc_id,
                    "source": source,
                    "page": meta.get("page"),
                    "chunk_id": meta.get("chunk_id") or doc_id,
                    "retrieval_confidence": retrieval_confidence,
                }
            )
            citation_records.append(
                {
                    "stage": "mel",
                    "citation_type": "rag_result",
                    "namespace": namespace,
                    "doc_id": doc_id,
                    "source": source,
                    "page": meta.get("page"),
                    "page_start": meta.get("page_start"),
                    "page_end": meta.get("page_end"),
                    "chunk": meta.get("chunk"),
                    "chunk_id": meta.get("chunk_id") or doc_id,
                    "label": citation,
                    "used_for": meta.get("indicator_id", f"IND_{idx+1:03d}"),
                    "excerpt": str(doc)[:240],
                    "citation_confidence": retrieval_confidence,
                    "evidence_score": retrieval_confidence,
                    "evidence_rank": rank,
                    "retrieval_rank": rank,
                    "retrieval_confidence": retrieval_confidence,
                }
            )
        rag_trace["used_results"] = len(indicators)
        if indicators:
            rag_trace["avg_retrieval_confidence"] = round(
                sum(float(c.get("retrieval_confidence") or 0.0) for c in citation_records) / len(citation_records),
                4,
            )
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
                "retrieval_confidence": 0.1,
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
