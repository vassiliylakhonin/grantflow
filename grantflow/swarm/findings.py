from __future__ import annotations

import uuid
from typing import Any, Dict, Iterable, Optional

_VALID_SEVERITIES = {"low", "medium", "high"}
_VALID_SECTIONS = {"toc", "logframe", "general"}
_VALID_STATUSES = {"open", "acknowledged", "resolved"}


def _coerce_section(value: Any, *, message: str = "") -> str:
    section = str(value or "").strip().lower()
    if section in _VALID_SECTIONS:
        return section
    lowered = message.lower()
    if any(k in lowered for k in ("indicator", "mel", "logframe")):
        return "logframe"
    if any(k in lowered for k in ("toc", "objective", "assumption", "causal")):
        return "toc"
    return "general"


def _coerce_severity(value: Any) -> str:
    severity = str(value or "").strip().lower()
    return severity if severity in _VALID_SEVERITIES else "medium"


def _coerce_status(value: Any) -> str:
    status = str(value or "open").strip().lower()
    return status if status in _VALID_STATUSES else "open"


def finding_identity_key(item: Dict[str, Any]) -> tuple[str, str, str, str, str]:
    return (
        str(item.get("code") or ""),
        str(item.get("section") or ""),
        str(item.get("version_id") or ""),
        str(item.get("message") or ""),
        str(item.get("source") or ""),
    )


def normalize_finding_item(
    item: Any,
    *,
    default_source: str = "rules",
) -> Optional[Dict[str, Any]]:
    if isinstance(item, str):
        message = item.strip()
        if not message:
            return None
        section = _coerce_section(None, message=message)
        normalized: Dict[str, Any] = {
            "finding_id": str(uuid.uuid4()),
            "code": "LEGACY_UNSTRUCTURED_FINDING",
            "severity": "medium",
            "section": section,
            "status": "open",
            "version_id": None,
            "message": message,
            "rationale": "Converted from legacy unstructured finding text.",
            "fix_suggestion": "Rewrite finding as structured object with code/severity/section fields.",
            "fix_hint": "Rewrite finding as structured object with code/severity/section fields.",
            "source": default_source,
        }
        return normalized

    if not isinstance(item, dict):
        return None

    current = dict(item)
    message = str(current.get("message") or current.get("detail") or "").strip()
    if not message:
        return None

    section = _coerce_section(current.get("section"), message=message)
    severity = _coerce_severity(current.get("severity"))
    status = _coerce_status(current.get("status"))
    source = str(current.get("source") or "").strip() or default_source
    code = str(current.get("code") or "").strip() or "FINDING_UNSPECIFIED"
    finding_id = str(current.get("finding_id") or "").strip() or str(uuid.uuid4())
    rationale = str(current.get("rationale") or "").strip() or None
    fix_suggestion = str(current.get("fix_suggestion") or current.get("fix_hint") or "").strip() or None

    normalized = dict(current)
    normalized["finding_id"] = finding_id
    normalized["code"] = code
    normalized["severity"] = severity
    normalized["section"] = section
    normalized["status"] = status
    normalized["message"] = message
    normalized["source"] = source
    normalized["rationale"] = rationale
    normalized["fix_suggestion"] = fix_suggestion
    normalized["fix_hint"] = fix_suggestion

    if status != "acknowledged":
        normalized.pop("acknowledged_at", None)
    if status != "resolved":
        normalized.pop("resolved_at", None)
    return normalized


def normalize_findings(
    items: Iterable[Any],
    *,
    previous_items: Optional[Iterable[Any]] = None,
    default_source: str = "rules",
) -> list[Dict[str, Any]]:
    previous_by_key: Dict[tuple[str, str, str, str, str], Dict[str, Any]] = {}
    for prev in previous_items or []:
        normalized_prev = normalize_finding_item(prev, default_source=default_source)
        if normalized_prev is None:
            continue
        previous_by_key[finding_identity_key(normalized_prev)] = normalized_prev

    normalized_items: list[Dict[str, Any]] = []
    for item in items:
        normalized = normalize_finding_item(item, default_source=default_source)
        if normalized is None:
            continue

        prior = previous_by_key.get(finding_identity_key(normalized))
        if prior:
            raw = item if isinstance(item, dict) else {}
            for key in ("finding_id", "status", "acknowledged_at", "resolved_at"):
                raw_has_value = isinstance(raw, dict) and raw.get(key) not in (None, "")
                if not raw_has_value and prior.get(key) is not None:
                    normalized[key] = prior.get(key)

        normalized_items.append(normalized)
    return normalized_items
