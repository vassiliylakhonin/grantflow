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
    return normalized


def _citation_key(record: Dict[str, Any]) -> tuple[Any, ...]:
    return (
        record.get("stage"),
        record.get("citation_type"),
        record.get("namespace"),
        record.get("source"),
        record.get("page"),
        record.get("page_start"),
        record.get("page_end"),
        record.get("chunk"),
        record.get("chunk_id"),
        record.get("used_for"),
        record.get("label"),
    )


def append_citations(state: Dict[str, Any], citations: Iterable[Dict[str, Any]], max_items: int = 200) -> None:
    incoming = [normalize_citation(c) for c in citations if isinstance(c, dict)]
    if not incoming:
        return

    existing = state.get("citations")
    if not isinstance(existing, list):
        existing = []

    normalized_existing = [normalize_citation(c) for c in existing if isinstance(c, dict)]
    seen = {_citation_key(c) for c in normalized_existing}
    merged = list(normalized_existing)

    for record in incoming:
        key = _citation_key(record)
        if key in seen:
            continue
        merged.append(record)
        seen.add(key)

    if len(merged) > max_items:
        merged = merged[-max_items:]
    state["citations"] = merged
