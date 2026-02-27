from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple

from grantflow.core.config import config
from grantflow.memory_bank.vector_store import vector_store
from grantflow.swarm.citation_source import citation_label_from_metadata, citation_source_from_metadata
from grantflow.swarm.retrieval_query import build_stage_query_text
from grantflow.swarm.state_contract import state_input_context

_TOKEN_RE = re.compile(r"[A-Za-z0-9]+")
_GENERIC_EXCERPT_TOKENS = {
    "annex",
    "appendix",
    "budget",
    "compliance",
    "finance",
    "financial",
    "forms",
    "procurement",
    "reporting",
    "template",
    "templates",
}
_DONOR_PRIORITY_TOKENS: dict[str, set[str]] = {
    "usaid": {
        "activity",
        "indicator",
        "ir",
        "mel",
        "outcome",
        "results",
        "services",
        "usaid",
    },
    "worldbank": {
        "capacity",
        "delivery",
        "framework",
        "indicator",
        "institutional",
        "monitoring",
        "outcome",
        "performance",
        "reform",
        "results",
        "service",
    },
}


def build_architect_query_text(state: Dict[str, Any]) -> str:
    input_context = state_input_context(state)
    project = str(input_context.get("project") or "project").strip()
    country = str(input_context.get("country") or "").strip()

    critic_notes = state.get("critic_notes") or {}
    revision_hint = ""
    if isinstance(critic_notes, dict):
        revision_hint = str(critic_notes.get("revision_instructions") or "").strip()
    elif isinstance(critic_notes, str):
        revision_hint = critic_notes.strip()

    return build_stage_query_text(
        state=state,
        stage="architect",
        project=project,
        country=country,
        revision_hint=revision_hint,
        toc_payload=(state.get("toc_draft") or {}).get("toc") if isinstance(state.get("toc_draft"), dict) else None,
    )


def _tokenize(text: Any) -> set[str]:
    return {m.group(0).lower() for m in _TOKEN_RE.finditer(str(text or "")) if len(m.group(0)) >= 3}


def _statement_priority_tokens(statement_path: str | None) -> set[str]:
    path = str(statement_path or "").lower()
    extra: set[str] = set()
    if any(token in path for token in ("indicator", "mel", "monitoring")):
        extra.update({"indicator", "monitoring", "results"})
    if any(token in path for token in ("result", "outcome", "objective")):
        extra.update({"results", "outcome", "indicator"})
    if any(token in path for token in ("service", "delivery")):
        extra.update({"service", "delivery", "performance"})
    return extra


def score_architect_evidence_hit(
    statement: str,
    hit: Dict[str, Any],
    *,
    donor_id: str | None = None,
    statement_path: str | None = None,
) -> float:
    statement_tokens = _tokenize(statement)
    if not statement_tokens:
        return 0.0

    excerpt_tokens = _tokenize(hit.get("excerpt"))
    label_tokens = _tokenize(hit.get("label") or hit.get("source"))
    all_hit_tokens = excerpt_tokens | label_tokens

    excerpt_overlap = len(statement_tokens & excerpt_tokens) / max(1, len(statement_tokens))
    label_overlap = len(statement_tokens & label_tokens) / max(1, len(statement_tokens))

    rank = int(hit.get("rank") or 999)
    rank_bonus = max(0.0, 1.0 - (rank - 1) * 0.15)
    page_bonus = 0.05 if hit.get("page") is not None else 0.0
    source_bonus = 0.05 if hit.get("source") else 0.0
    donor_key = str(donor_id or "").strip().lower()
    priority_tokens = set(_DONOR_PRIORITY_TOKENS.get(donor_key, set()))
    priority_tokens.update(_statement_priority_tokens(statement_path))
    priority_overlap = len(priority_tokens & all_hit_tokens)
    priority_bonus = min(0.12, priority_overlap * 0.03)

    generic_overlap = len(_GENERIC_EXCERPT_TOKENS & excerpt_tokens)
    generic_penalty = 0.0
    if generic_overlap >= 2 and excerpt_overlap < 0.15:
        generic_penalty = min(0.1, generic_overlap * 0.02)

    score = (
        (0.65 * excerpt_overlap)
        + (0.15 * label_overlap)
        + (0.15 * rank_bonus)
        + page_bonus
        + source_bonus
        + priority_bonus
        - generic_penalty
    )
    return max(0.0, min(1.0, round(score, 4)))


def pick_best_architect_evidence_hit(
    statement: str,
    hits: List[Dict[str, Any]],
    *,
    donor_id: str | None = None,
    statement_path: str | None = None,
) -> tuple[Dict[str, Any], float]:
    if not hits:
        return {}, 0.0
    best_hit = hits[0]
    best_score = score_architect_evidence_hit(statement, best_hit, donor_id=donor_id, statement_path=statement_path)
    for hit in hits[1:]:
        score = score_architect_evidence_hit(statement, hit, donor_id=donor_id, statement_path=statement_path)
        if score > best_score:
            best_hit = hit
            best_score = score
    return best_hit, best_score


def _hit_traceability_status(*, doc_id: str, chunk_id: str, source: str, page: Any) -> str:
    if doc_id and source:
        return "complete"
    if doc_id or chunk_id or source or page is not None:
        return "partial"
    return "missing"


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
        distances = ((result or {}).get("distances") or [[]])[0]
        seen_signatures: set[tuple[Any, ...]] = set()
        traceability_counts = {"complete": 0, "partial": 0, "missing": 0}

        for idx, doc in enumerate(docs):
            meta = metas[idx] if idx < len(metas) and isinstance(metas[idx], dict) else {}
            source = citation_source_from_metadata(meta)
            rank = idx + 1
            raw_doc_id = meta.get("doc_id") or meta.get("chunk_id") or (ids[idx] if idx < len(ids) else None)
            raw_chunk_id = meta.get("chunk_id") or raw_doc_id
            doc_id = str(raw_doc_id or "").strip()
            chunk_id = str(raw_chunk_id or "").strip()
            if not doc_id and chunk_id:
                doc_id = chunk_id
            if not chunk_id and doc_id:
                chunk_id = doc_id
            if not doc_id:
                doc_id = f"{namespace}#hit-{rank}"
            if not chunk_id:
                chunk_id = doc_id
            source = str(source or "").strip() or None
            page = meta.get("page")
            signature = (doc_id, chunk_id, source, page)
            if signature in seen_signatures:
                continue
            seen_signatures.add(signature)
            raw_distance = distances[idx] if idx < len(distances) else None
            if isinstance(raw_distance, (int, float)):
                retrieval_confidence = round(max(0.0, min(1.0, 1.0 / (1.0 + float(raw_distance)))), 4)
            else:
                retrieval_confidence = round(max(0.1, 1.0 - (idx * 0.2)), 4)
            traceability_status = _hit_traceability_status(
                doc_id=doc_id,
                chunk_id=chunk_id,
                source=str(source or ""),
                page=page,
            )
            traceability_counts[traceability_status] = int(traceability_counts.get(traceability_status, 0)) + 1
            hits.append(
                {
                    "rank": rank,
                    "retrieval_rank": rank,
                    "doc_id": doc_id,
                    "chunk_id": chunk_id,
                    "source": source,
                    "page": page,
                    "page_start": meta.get("page_start"),
                    "page_end": meta.get("page_end"),
                    "chunk": meta.get("chunk"),
                    "label": citation_label_from_metadata(meta, namespace=namespace, rank=rank),
                    "excerpt": str(doc)[:320],
                    "retrieval_confidence": retrieval_confidence,
                    "namespace": namespace,
                    "traceability_status": traceability_status,
                }
            )
        summary["hits_count"] = len(hits)
        summary["used_results"] = len(hits)
        summary["traceability_counts"] = traceability_counts
        if hits:
            summary["hit_labels"] = [str(h.get("label") or "") for h in hits[:3]]
            summary["avg_retrieval_confidence"] = round(
                sum(float(h.get("retrieval_confidence") or 0.0) for h in hits) / len(hits),
                4,
            )
            summary["hits"] = [
                {
                    "retrieval_rank": int(h.get("retrieval_rank") or 0),
                    "doc_id": h.get("doc_id"),
                    "source": h.get("source"),
                    "page": h.get("page"),
                    "chunk_id": h.get("chunk_id"),
                    "retrieval_confidence": h.get("retrieval_confidence"),
                    "traceability_status": h.get("traceability_status"),
                    "namespace": h.get("namespace"),
                }
                for h in hits[:5]
            ]
    except Exception as exc:
        summary["error"] = str(exc)
    return summary, hits
