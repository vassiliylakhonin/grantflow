from __future__ import annotations

from typing import Any, Dict, Iterable


def _jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def normalize_citation(record: Dict[str, Any]) -> Dict[str, Any]:
    normalized: Dict[str, Any] = {}
    for key, value in record.items():
        normalized[str(key)] = _jsonable(value)
    doc_id = str(normalized.get("doc_id") or "").strip()
    chunk_id = str(normalized.get("chunk_id") or "").strip()
    if not doc_id and chunk_id:
        normalized["doc_id"] = chunk_id
    elif doc_id and not chunk_id:
        normalized["chunk_id"] = doc_id

    if normalized.get("retrieval_rank") in (None, ""):
        fallback_rank = normalized.get("rank")
        try:
            normalized_rank = int(fallback_rank) if fallback_rank is not None else None
        except (TypeError, ValueError):
            normalized_rank = None
        if normalized_rank is not None:
            normalized["retrieval_rank"] = normalized_rank

    if normalized.get("retrieval_confidence") in (None, ""):
        fallback_conf = normalized.get("citation_confidence")
        try:
            normalized_conf = float(fallback_conf) if fallback_conf is not None else None
        except (TypeError, ValueError):
            normalized_conf = None
        if normalized_conf is not None:
            normalized["retrieval_confidence"] = normalized_conf
    return normalized


def _citation_key(record: Dict[str, Any]) -> tuple[Any, ...]:
    return (
        record.get("stage"),
        record.get("citation_type"),
        record.get("namespace"),
        record.get("doc_id"),
        record.get("source"),
        record.get("page"),
        record.get("page_start"),
        record.get("page_end"),
        record.get("chunk"),
        record.get("chunk_id"),
        record.get("used_for"),
        record.get("statement_path"),
        record.get("label"),
    )


def _traceability_weight(record: Dict[str, Any]) -> int:
    status = citation_traceability_status(record)
    if status == "complete":
        return 2
    if status == "partial":
        return 1
    return 0


def _float_or_default(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _int_or_default(value: Any, default: int = 999) -> int:
    try:
        token = int(value)
    except (TypeError, ValueError):
        return default
    return token if token > 0 else default


def _citation_quality_key(record: Dict[str, Any]) -> tuple[float, float, float, float]:
    return (
        float(_traceability_weight(record)),
        _float_or_default(record.get("citation_confidence"), default=0.0),
        _float_or_default(record.get("retrieval_confidence"), default=0.0),
        -float(_int_or_default(record.get("retrieval_rank"), default=999)),
    )


def _merge_citation_records(current: Dict[str, Any], incoming: Dict[str, Any]) -> Dict[str, Any]:
    current_key = _citation_quality_key(current)
    incoming_key = _citation_quality_key(incoming)
    preferred = dict(incoming) if incoming_key >= current_key else dict(current)
    fallback = current if incoming_key >= current_key else incoming
    for key, value in fallback.items():
        if preferred.get(key) in (None, "") and value not in (None, ""):
            preferred[key] = value
    return preferred


def append_citations(state: Dict[str, Any], citations: Iterable[Dict[str, Any]], max_items: int = 200) -> None:
    incoming = [normalize_citation(c) for c in citations if isinstance(c, dict)]
    if not incoming:
        return

    existing = state.get("citations")
    if not isinstance(existing, list):
        existing = []

    normalized_existing = [normalize_citation(c) for c in existing if isinstance(c, dict)]
    merged = list(normalized_existing)
    seen: dict[tuple[Any, ...], int] = {}
    for idx, row in enumerate(merged):
        seen[_citation_key(row)] = idx

    for record in incoming:
        key = _citation_key(record)
        existing_idx = seen.get(key)
        if existing_idx is None:
            seen[key] = len(merged)
            merged.append(record)
            continue
        merged[existing_idx] = _merge_citation_records(merged[existing_idx], record)

    if len(merged) > max_items:
        merged = merged[-max_items:]
    state["citations"] = merged


def citation_traceability_status(record: Dict[str, Any]) -> str:
    status = str(record.get("traceability_status") or "").strip().lower()
    if status in {"complete", "partial", "missing"}:
        return status

    doc_id = str(record.get("doc_id") or record.get("chunk_id") or "").strip()
    source = str(record.get("source") or "").strip()
    page = record.get("page")
    page_start = record.get("page_start")
    page_end = record.get("page_end")
    chunk = record.get("chunk")

    if doc_id and source:
        return "complete"
    if doc_id or source or page is not None or page_start is not None or page_end is not None or chunk is not None:
        return "partial"
    return "missing"
