from __future__ import annotations

from typing import Any, Dict

from grantflow.swarm.state_contract import state_donor_id

_DONOR_QUERY_PRESETS: dict[str, list[str]] = {
    "usaid": [
        "development objectives",
        "intermediate results",
        "outputs",
        "mel indicators",
        "results framework",
    ],
    "eu": [
        "intervention logic",
        "overall objective",
        "specific objectives",
        "expected outcomes",
        "results framework",
    ],
    "worldbank": [
        "project development objective",
        "results chain",
        "results framework",
        "indicator focus",
        "service delivery",
    ],
    "giz": [
        "technical cooperation",
        "partner roles",
        "sustainability factors",
        "implementation outcomes",
    ],
    "state_department": [
        "strategic context",
        "stakeholder map",
        "risk mitigation",
        "program outcomes",
    ],
    "us_state_department": [
        "strategic context",
        "stakeholder map",
        "risk mitigation",
        "program outcomes",
    ],
}

_CONTEXT_HINT_KEYS = (
    "project",
    "country",
    "sector",
    "theme",
    "problem_statement",
    "target_population",
    "target_beneficiaries",
    "budget",
    "duration_months",
)


def donor_query_preset_terms(donor_id: str) -> str:
    donor_key = str(donor_id or "").strip().lower()
    terms = _DONOR_QUERY_PRESETS.get(donor_key, ["institutional donor guidance", "results framework", "indicators"])
    return " | ".join(terms)


def context_query_hints(input_context: Dict[str, Any] | None, *, max_items: int = 5) -> str:
    ctx = input_context if isinstance(input_context, dict) else {}
    hints: list[str] = []
    for key in _CONTEXT_HINT_KEYS:
        if len(hints) >= max_items:
            break
        value = ctx.get(key)
        if value is None:
            continue
        if isinstance(value, (int, float)):
            hints.append(f"{key}: {value}")
            continue
        if isinstance(value, str):
            clean = value.strip()
            if clean:
                hints.append(f"{key}: {clean}")
            continue
        if isinstance(value, list):
            parts = [str(v).strip() for v in value if str(v or "").strip()]
            if parts:
                hints.append(f"{key}: {', '.join(parts[:3])}")
            continue
    return " | ".join(hints)


def toc_query_hints(toc_payload: Any, *, max_items: int = 3) -> str:
    if not isinstance(toc_payload, dict):
        return ""
    hints: list[str] = []
    for key in ("project_goal", "project_development_objective", "brief"):
        raw = toc_payload.get(key)
        text = str(raw or "").strip()
        if text:
            hints.append(text)
        if len(hints) >= max_items:
            break
    objectives = toc_payload.get("objectives")
    if len(hints) < max_items and isinstance(objectives, list):
        for row in objectives[:2]:
            if not isinstance(row, dict):
                continue
            title = str(row.get("title") or "").strip()
            if title:
                hints.append(title)
            if len(hints) >= max_items:
                break
    return " | ".join(hints)


def build_stage_query_text(
    *,
    state: Dict[str, Any],
    stage: str,
    project: str,
    country: str,
    revision_hint: str = "",
    toc_payload: Any = None,
) -> str:
    donor_id = state_donor_id(state, default="donor")
    input_context = state.get("input_context")
    context_hints = context_query_hints(input_context)
    donor_terms = donor_query_preset_terms(donor_id)
    toc_hints = toc_query_hints(toc_payload)
    parts: list[str] = [
        str(stage or "").strip(),
        str(project or "").strip(),
        str(country or "").strip(),
        donor_id,
        context_hints,
        toc_hints,
        revision_hint.strip(),
        donor_terms,
    ]
    deduped: list[str] = []
    seen: set[str] = set()
    for item in parts:
        text = str(item or "").strip()
        if not text:
            continue
        norm = text.lower()
        if norm in seen:
            continue
        deduped.append(text)
        seen.add(norm)
    return " | ".join(deduped)
