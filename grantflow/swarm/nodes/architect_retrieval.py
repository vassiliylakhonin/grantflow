from __future__ import annotations

from typing import Any, Dict, List, Tuple

from grantflow.core.config import config
from grantflow.memory_bank.vector_store import vector_store


def build_architect_query_text(state: Dict[str, Any]) -> str:
    input_context = state.get("input") or state.get("input_context") or {}
    project = str(input_context.get("project") or "project").strip()
    country = str(input_context.get("country") or "").strip()
    donor_id = str(state.get("donor") or state.get("donor_id") or "donor").strip()

    critic_notes = state.get("critic_notes") or {}
    revision_hint = ""
    if isinstance(critic_notes, dict):
        revision_hint = str(critic_notes.get("revision_instructions") or "").strip()
    elif isinstance(critic_notes, str):
        revision_hint = critic_notes.strip()

    parts = [project, country, donor_id, revision_hint]
    return " | ".join([p for p in parts if p])


def retrieve_architect_evidence(state: Dict[str, Any], namespace: str) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    enabled = bool(state.get("architect_rag_enabled", True))
    top_k = max(1, min(int(config.rag.default_top_k or 3), 3))
    query_text = build_architect_query_text(state)

    summary: Dict[str, Any] = {
        "enabled": enabled,
        "namespace": namespace,
        "query": query_text,
        "top_k": top_k,
        "hits_count": 0,
        "used_results": 0,
    }
    if not enabled:
        return summary, []

    hits: List[Dict[str, Any]] = []
    try:
        result = vector_store.query(namespace=namespace, query_texts=[query_text], n_results=top_k)
        docs = ((result or {}).get("documents") or [[]])[0]
        metas = ((result or {}).get("metadatas") or [[]])[0]
        ids = ((result or {}).get("ids") or [[]])[0]

        for idx, doc in enumerate(docs):
            meta = metas[idx] if idx < len(metas) and isinstance(metas[idx], dict) else {}
            hits.append(
                {
                    "rank": idx + 1,
                    "chunk_id": meta.get("chunk_id") or (ids[idx] if idx < len(ids) else None),
                    "source": meta.get("source"),
                    "page": meta.get("page"),
                    "page_start": meta.get("page_start"),
                    "page_end": meta.get("page_end"),
                    "chunk": meta.get("chunk"),
                    "label": meta.get("citation") or meta.get("source") or f"{namespace}#{idx+1}",
                    "excerpt": str(doc)[:320],
                }
            )
        summary["hits_count"] = len(hits)
        summary["used_results"] = len(hits)
    except Exception as exc:
        summary["error"] = str(exc)
    return summary, hits
