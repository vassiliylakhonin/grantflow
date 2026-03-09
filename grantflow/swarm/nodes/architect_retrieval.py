from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple

from grantflow.core.config import config
from grantflow.memory_bank.vector_store import vector_store
from grantflow.swarm.citations import citation_traceability_status
from grantflow.swarm.citation_source import citation_label_from_metadata, citation_source_from_metadata
from grantflow.swarm.retrieval_query import build_stage_query_text, donor_query_preset_list
from grantflow.swarm.state_contract import state_donor_id, state_input_context, state_revision_hint

_TOKEN_RE = re.compile(r"[A-Za-z0-9]+")
_COMPACT_STOPWORDS = {
    "and",
    "for",
    "from",
    "into",
    "that",
    "the",
    "this",
    "through",
    "with",
}
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

    revision_hint = state_revision_hint(state).strip()

    return build_stage_query_text(
        state=state,
        stage="architect",
        project=project,
        country=country,
        revision_hint=revision_hint,
        toc_payload=(state.get("toc_draft") or {}).get("toc") if isinstance(state.get("toc_draft"), dict) else None,
        include_revision_hint=False,
    )


def _tokenize(text: Any) -> set[str]:
    return {m.group(0).lower() for m in _TOKEN_RE.finditer(str(text or "")) if len(m.group(0)) >= 3}


def _keyword_phrase(text: Any, *, max_words: int = 8) -> str:
    words: list[str] = []
    seen: set[str] = set()
    for match in _TOKEN_RE.finditer(str(text or "")):
        token = match.group(0).lower()
        if len(token) < 3 or token in _COMPACT_STOPWORDS or token in seen:
            continue
        seen.add(token)
        words.append(token)
        if len(words) >= max_words:
            break
    return " ".join(words)


def _compact_toc_clues(state: Dict[str, Any], *, max_items: int = 2) -> str:
    toc = (state.get("toc_draft") or {}).get("toc") if isinstance(state.get("toc_draft"), dict) else None
    if not isinstance(toc, dict):
        return ""
    hints: list[str] = []
    for key in (
        "project_goal",
        "project_development_objective",
        "program_goal",
        "programme_objective",
        "brief",
    ):
        phrase = _keyword_phrase(toc.get(key))
        if phrase:
            hints.append(phrase)
        if len(hints) >= max_items:
            break
    for key in ("objectives", "specific_objectives", "expected_outcomes", "results_chain"):
        if len(hints) >= max_items:
            break
        rows = toc.get(key)
        if not isinstance(rows, list):
            continue
        for row in rows[:2]:
            if not isinstance(row, dict):
                continue
            phrase = _keyword_phrase(
                row.get("title") or row.get("description") or row.get("expected_change") or row.get("indicator_focus")
            )
            if phrase:
                hints.append(phrase)
            if len(hints) >= max_items:
                break
    return " ".join(hints[:max_items])


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
    retrieval_confidence = float(hit.get("retrieval_confidence") or 0.0)
    rerank_score = float(hit.get("rerank_score") or 0.0)
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
        (0.55 * excerpt_overlap)
        + (0.12 * label_overlap)
        + (0.10 * rank_bonus)
        + (0.15 * retrieval_confidence)
        + (0.08 * rerank_score)
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


def _bounded_int(value: Any, *, default: int, low: int, high: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(low, min(high, parsed))


def _bounded_float(value: Any, *, default: float, low: float, high: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = default
    return max(low, min(high, parsed))


def _query_variants(state: Dict[str, Any], base_query: str, *, max_variants: int) -> list[str]:
    input_context = state_input_context(state)
    project = str(input_context.get("project") or "").strip()
    country = str(input_context.get("country") or "").strip()
    donor_id = state_donor_id(state, default="donor")
    sector = str(input_context.get("sector") or "").strip()
    theme = str(input_context.get("theme") or "").strip()
    donor_terms = donor_query_preset_list(donor_id)
    donor_phrase = " ".join(donor_terms[:4])
    project_keywords = _keyword_phrase(project, max_words=6)
    sector_keywords = _keyword_phrase(f"{sector} {theme}", max_words=4)
    toc_keywords = _compact_toc_clues(state, max_items=2)

    candidates = [
        f"{project_keywords} {country} {donor_id} {donor_phrase}".strip(),
        f"{country} {donor_id} {sector_keywords} {donor_phrase}".strip(),
        f"{project_keywords} {country} {toc_keywords} {donor_phrase}".strip(),
        base_query.strip(),
    ]

    unique: list[str] = []
    seen: set[str] = set()
    for raw in candidates:
        query = str(raw or "").strip()
        if not query:
            continue
        marker = query.lower()
        if marker in seen:
            continue
        seen.add(marker)
        unique.append(query)
        if len(unique) >= max_variants:
            break
    return unique or [base_query]


def _rows(value: Any) -> list[list[Any]]:
    if not isinstance(value, list):
        return [[]]
    if value and not isinstance(value[0], list):
        return [value]
    return value


def _as_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _distance_confidence(raw_distance: Any, *, rank_index: int, row_distances: list[Any]) -> float:
    rank_prior = max(0.1, 1.0 - (max(0, rank_index) * 0.18))
    distance_value = _as_float(raw_distance)
    if distance_value is None:
        return round(rank_prior, 4)

    distance = max(0.0, distance_value)
    absolute_conf = 1.0 / (1.0 + (distance * 0.35))

    numeric_distances = [max(0.0, item) for item in (_as_float(v) for v in row_distances) if item is not None]
    if not numeric_distances:
        relative_conf = rank_prior
    else:
        min_distance = min(numeric_distances)
        max_distance = max(numeric_distances)
        span = max(max_distance - min_distance, 1e-9)
        relative_conf = 1.0 if span <= 1e-9 else 1.0 - ((distance - min_distance) / span)
        relative_conf = max(0.0, min(1.0, relative_conf))

    confidence = (absolute_conf * 0.35) + (relative_conf * 0.45) + (rank_prior * 0.2)
    return round(max(0.0, min(1.0, confidence)), 4)


def retrieve_architect_evidence(state: Dict[str, Any], namespace: str) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    enabled = bool(state.get("architect_rag_enabled", True))
    top_k = _bounded_int(
        getattr(config.rag, "architect_top_k", getattr(config.rag, "default_top_k", 5)),
        default=5,
        low=1,
        high=12,
    )
    rerank_pool_size = _bounded_int(
        getattr(config.rag, "architect_rerank_pool_size", max(top_k, 10)),
        default=max(top_k, 10),
        low=top_k,
        high=36,
    )
    query_variants_limit = _bounded_int(
        getattr(config.rag, "architect_query_variants", 3),
        default=3,
        low=1,
        high=6,
    )
    min_hit_confidence = _bounded_float(
        getattr(config.rag, "architect_min_hit_confidence", 0.25),
        default=0.25,
        low=0.0,
        high=1.0,
    )
    query_text = build_architect_query_text(state)
    query_variants = _query_variants(state, query_text, max_variants=query_variants_limit)
    namespace_trace = vector_store.namespace_trace(namespace)
    namespace_normalized = namespace_trace["namespace_normalized"]
    collection = namespace_trace["collection"]

    summary: Dict[str, Any] = {
        "enabled": enabled,
        "namespace": namespace,
        "namespace_normalized": namespace_normalized,
        "collection": collection,
        "query": query_text,
        "query_variants": query_variants,
        "query_variants_count": len(query_variants),
        "top_k": top_k,
        "rerank_pool_size": rerank_pool_size,
        "min_hit_confidence": round(min_hit_confidence, 3),
        "hits_count": 0,
        "candidate_hits_count": 0,
        "used_results": 0,
    }
    if not enabled:
        return summary, []

    hits: List[Dict[str, Any]] = []
    try:
        donor_id = state_donor_id(state, default="")
        result = vector_store.query(namespace=namespace, query_texts=query_variants, n_results=rerank_pool_size)
        result_payload = result if isinstance(result, dict) else {}
        docs_rows = _rows((result_payload or {}).get("documents"))
        metas_rows = _rows((result_payload or {}).get("metadatas"))
        ids_rows = _rows((result_payload or {}).get("ids"))
        distances_rows = _rows((result_payload or {}).get("distances"))

        best_by_signature: dict[tuple[Any, ...], Dict[str, Any]] = {}
        for q_idx, query_variant in enumerate(query_variants):
            docs = docs_rows[q_idx] if q_idx < len(docs_rows) else []
            metas = metas_rows[q_idx] if q_idx < len(metas_rows) else []
            ids = ids_rows[q_idx] if q_idx < len(ids_rows) else []
            distances = distances_rows[q_idx] if q_idx < len(distances_rows) else []
            for idx, doc in enumerate(docs):
                meta = metas[idx] if idx < len(metas) and isinstance(metas[idx], dict) else {}
                source = citation_source_from_metadata(meta)
                retrieval_rank = idx + 1
                raw_doc_id = meta.get("doc_id") or meta.get("chunk_id") or (ids[idx] if idx < len(ids) else None)
                raw_chunk_id = meta.get("chunk_id") or raw_doc_id
                doc_id = str(raw_doc_id or "").strip()
                chunk_id = str(raw_chunk_id or "").strip()
                if not doc_id and chunk_id:
                    doc_id = chunk_id
                if not chunk_id and doc_id:
                    chunk_id = doc_id
                if not doc_id:
                    doc_id = f"{namespace_normalized}#q{q_idx + 1}-hit-{retrieval_rank}"
                if not chunk_id:
                    chunk_id = doc_id

                source = str(source or "").strip() or None
                page = meta.get("page")
                raw_distance = distances[idx] if idx < len(distances) else None
                parsed_distance = _as_float(raw_distance)
                retrieval_distance = round(parsed_distance, 6) if parsed_distance is not None else None
                retrieval_confidence = _distance_confidence(raw_distance, rank_index=idx, row_distances=distances)

                candidate: Dict[str, Any] = {
                    "rank": retrieval_rank,
                    "retrieval_rank": retrieval_rank,
                    "query_variant_index": q_idx + 1,
                    "query_variant": query_variant,
                    "doc_id": doc_id,
                    "chunk_id": chunk_id,
                    "source": source,
                    "page": page,
                    "page_start": meta.get("page_start"),
                    "page_end": meta.get("page_end"),
                    "chunk": meta.get("chunk"),
                    "label": citation_label_from_metadata(meta, namespace=namespace, rank=retrieval_rank),
                    "excerpt": str(doc)[:320],
                    "retrieval_confidence": retrieval_confidence,
                    "retrieval_distance": retrieval_distance,
                    "namespace": namespace,
                    "namespace_normalized": namespace_normalized,
                    "collection": collection,
                }
                traceability_status = citation_traceability_status(candidate)
                candidate["traceability_status"] = traceability_status
                candidate["traceability_complete"] = traceability_status == "complete"
                query_tokens = _tokenize(query_variant)
                hit_tokens = _tokenize(candidate.get("excerpt")) | _tokenize(
                    candidate.get("label") or candidate.get("source")
                )
                query_overlap = len(query_tokens & hit_tokens) / max(1, len(query_tokens))
                base_score = score_architect_evidence_hit(
                    query_text,
                    candidate,
                    donor_id=donor_id,
                    statement_path="toc",
                )
                rerank_score = round(max(0.0, min(1.0, (base_score * 0.75) + (query_overlap * 0.25))), 4)
                candidate["rerank_score"] = rerank_score

                signature = (doc_id, chunk_id, source, page)
                current = best_by_signature.get(signature)
                if current is None:
                    best_by_signature[signature] = candidate
                    continue
                current_key = (
                    float(current.get("rerank_score") or 0.0),
                    float(current.get("retrieval_confidence") or 0.0),
                    -int(current.get("retrieval_rank") or 999),
                )
                candidate_key = (
                    float(candidate.get("rerank_score") or 0.0),
                    float(candidate.get("retrieval_confidence") or 0.0),
                    -int(candidate.get("retrieval_rank") or 999),
                )
                if candidate_key > current_key:
                    best_by_signature[signature] = candidate

        ranked_candidates = sorted(
            best_by_signature.values(),
            key=lambda hit: (
                float(hit.get("rerank_score") or 0.0),
                float(hit.get("retrieval_confidence") or 0.0),
                -int(hit.get("retrieval_rank") or 999),
                -int(hit.get("query_variant_index") or 999),
            ),
            reverse=True,
        )
        summary["candidate_hits_count"] = len(ranked_candidates)

        filtered = [
            hit
            for hit in ranked_candidates
            if float(hit.get("retrieval_confidence") or 0.0) >= min_hit_confidence
            or float(hit.get("rerank_score") or 0.0) >= min_hit_confidence
        ]
        if not filtered and ranked_candidates:
            filtered = ranked_candidates[:1]
        summary["filtered_out_low_confidence"] = max(0, len(ranked_candidates) - len(filtered))
        hits = filtered[:top_k]

        traceability_counts = {"complete": 0, "partial": 0, "missing": 0}
        for idx, hit in enumerate(hits):
            hit["rank"] = idx + 1
            traceability_status = citation_traceability_status(hit)
            hit["traceability_status"] = traceability_status
            hit["traceability_complete"] = traceability_status == "complete"
            traceability_counts[traceability_status] = int(traceability_counts.get(traceability_status, 0)) + 1

        summary["hits_count"] = len(hits)
        summary["used_results"] = len(hits)
        summary["traceability_counts"] = traceability_counts
        if hits:
            summary["hit_labels"] = [str(h.get("label") or "") for h in hits[:3]]
            summary["avg_retrieval_confidence"] = round(
                sum(float(h.get("retrieval_confidence") or 0.0) for h in hits) / len(hits),
                4,
            )
            summary["avg_rerank_score"] = round(sum(float(h.get("rerank_score") or 0.0) for h in hits) / len(hits), 4)
            summary["hits"] = [
                {
                    "retrieval_rank": int(h.get("retrieval_rank") or 0),
                    "query_variant_index": int(h.get("query_variant_index") or 0),
                    "doc_id": h.get("doc_id"),
                    "source": h.get("source"),
                    "page": h.get("page"),
                    "chunk_id": h.get("chunk_id"),
                    "retrieval_confidence": h.get("retrieval_confidence"),
                    "retrieval_distance": h.get("retrieval_distance"),
                    "rerank_score": h.get("rerank_score"),
                    "traceability_status": h.get("traceability_status"),
                    "traceability_complete": h.get("traceability_complete"),
                    "namespace": h.get("namespace"),
                    "namespace_normalized": h.get("namespace_normalized"),
                    "collection": h.get("collection"),
                }
                for h in hits[:5]
            ]
    except Exception as exc:
        summary["error"] = str(exc)
    return summary, hits
