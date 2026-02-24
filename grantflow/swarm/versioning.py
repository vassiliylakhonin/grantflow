from __future__ import annotations

import copy
import json
from enum import Enum
from typing import Any, Dict, Iterable, Optional


def _jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return str(value)


def _canonical_json(value: Any) -> str:
    return json.dumps(_jsonable(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def append_draft_version(
    state: Dict[str, Any],
    *,
    section: str,
    content: Dict[str, Any],
    node: str,
    iteration: Optional[int] = None,
    max_items: int = 100,
) -> None:
    if not isinstance(content, dict):
        return

    versions = state.get("draft_versions")
    if not isinstance(versions, list):
        versions = []

    safe_content = _jsonable(copy.deepcopy(content))
    content_hash = _canonical_json(safe_content)

    # Avoid duplicate consecutive snapshots for the same section.
    for prev in reversed(versions):
        if not isinstance(prev, dict):
            continue
        if prev.get("section") != section:
            continue
        if prev.get("content_hash") == content_hash:
            return
        break

    sequence = 1 + max(
        [int(v.get("sequence", 0)) for v in versions if isinstance(v, dict)],
        default=0,
    )
    section_count = 1 + sum(1 for v in versions if isinstance(v, dict) and v.get("section") == section)

    versions.append(
        {
            "version_id": f"{section}_v{section_count}",
            "sequence": sequence,
            "section": section,
            "node": node,
            "iteration": int(iteration) if iteration is not None else None,
            "content": safe_content,
            "content_hash": content_hash,
        }
    )

    if len(versions) > max_items:
        versions = versions[-max_items:]
    state["draft_versions"] = versions


def filter_versions(versions: Iterable[Dict[str, Any]], section: Optional[str] = None) -> list[Dict[str, Any]]:
    filtered = [v for v in versions if isinstance(v, dict)]
    if section:
        filtered = [v for v in filtered if str(v.get("section") or "") == section]
    filtered.sort(key=lambda v: (int(v.get("sequence", 0)), str(v.get("version_id", ""))))
    return filtered
