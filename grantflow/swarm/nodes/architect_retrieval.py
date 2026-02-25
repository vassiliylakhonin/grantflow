from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple

from grantflow.core.config import config
from grantflow.memory_bank.vector_store import vector_store


_TOKEN_RE = re.compile(r"[A-Za-z0-9]+")


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


def _tokenize(text: Any) -> set[str]:
    return {m.group(0).lower() for m in _TOKEN_RE.finditer(str(text or "")) if len(m.group(0)) >= 3}


def score_architect_evidence_hit(statement: str, hit: Dict[str, Any]) -> float:
    statement_tokens = _tokenize(statement)
    if not statement_tokens:
        return 0.0

    excerpt_tokens = _tokenize(hit.get("excerpt"))
    label_tokens = _tokenize(hit.get("label") or hit.get("source"))

    excerpt_overlap = len(statement_tokens & excerpt_tokens) / max(1, len(statement_tokens))
    label_overlap = len(statement_tokens & label_tokens) / max(1, len(statement_tokens))

    rank = int(hit.get("rank") or 999)
    rank_bonus = max(0.0, 1.0 - (rank - 1) * 0.15)
    page_bonus = 0.05 if hit.get("page") is not None else 0.0
    source_bonus = 0.05 if hit.get("source") else 0.0

    score = (0.65 * excerpt_overlap) + (0.15 * label_overlap) + (0.15 * rank_bonus) + page_bonus + source_bonus
    return max(0.0, min(1.0, round(score, 4)))


def pick_best_architect_evidence_hit(statement: str, hits: List[Dict[str, Any]]) -> tuple[Dict[str, Any], float]:
    if not hits:
        return {}, 0.0
    best_hit = hits[0]
    best_score = score_architect_evidence_hit(statement, best_hit)
    for hit in hits[1:]:
        score = score_architect_evidence_hit(statement, hit)
        if score > best_score:
            best_hit = hit
            best_score = score
    return best_hit, best_score


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
        if hits:
            summary["hit_labels"] = [str(h.get("label") or "") for h in hits[:3]]
    except Exception as exc:
        summary["error"] = str(exc)
    return summary, hits
