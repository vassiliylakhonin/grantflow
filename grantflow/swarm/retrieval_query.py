from __future__ import annotations

import re
from typing import Any, Dict

from grantflow.swarm.state_contract import state_donor_id, state_input_context

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
        "logframe",
        "action document",
        "means of verification",
    ],
    "worldbank": [
        "project development objective",
        "results chain",
        "results framework",
        "indicator focus",
        "service delivery",
        "implementation status results report",
        "project development objective indicators",
        "intermediate results indicators",
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
    "proposal_mode",
    "project",
    "country",
    "sector",
    "theme",
    "problem_statement",
    "target_population",
    "target_beneficiaries",
    "budget",
    "duration_months",
    "evaluation_purpose",
    "methods",
    "evaluation_methods",
    "deliverables",
)

_REVISION_NOISE_PATTERNS = (
    re.compile(r"^\s*address the following issues\b.*$", re.IGNORECASE),
    re.compile(r"^\s*grounding gate warning\b.*$", re.IGNORECASE),
    re.compile(r"^\s*critic\b.*$", re.IGNORECASE),
    re.compile(r"^\s*warning\b.*$", re.IGNORECASE),
    re.compile(r"^\s*issue\b.*$", re.IGNORECASE),
)
_REVISION_DROP_PHRASES = (
    "architect_retrieval_no_hits",
    "fallback_dominant",
    "low_confidence",
    "traceability_gap",
    "replace repeated boilerplate",
    "reviewer-ready",
    "next draft",
)


def donor_query_preset_list(donor_id: str) -> list[str]:
    donor_key = str(donor_id or "").strip().lower()
    terms = _DONOR_QUERY_PRESETS.get(donor_key, ["institutional donor guidance", "results framework", "indicators"])
    return list(terms)


def donor_query_preset_terms(donor_id: str) -> str:
    return " | ".join(donor_query_preset_list(donor_id))


def _proposal_mode_query_terms(input_context: Dict[str, Any] | None) -> str:
    ctx = input_context if isinstance(input_context, dict) else {}
    proposal_mode = str(ctx.get("proposal_mode") or "").strip().lower()
    if proposal_mode != "evaluation_rfq":
        return ""
    return "evaluation questions | methodology | sampling | deliverables | inception report | final evaluation report"


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


def toc_query_hints(toc_payload: Any, *, max_items: int = 4) -> str:
    if not isinstance(toc_payload, dict):
        return ""
    hints: list[str] = []
    for key in ("project_goal", "project_development_objective", "program_goal", "programme_objective", "brief"):
        raw = toc_payload.get(key)
        text = str(raw or "").strip()
        if text:
            hints.append(text)
        if len(hints) >= max_items:
            break
    overall_objective = toc_payload.get("overall_objective")
    if len(hints) < max_items and isinstance(overall_objective, dict):
        for key in ("title", "rationale"):
            text = str(overall_objective.get(key) or "").strip()
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
    specific_objectives = toc_payload.get("specific_objectives")
    if len(hints) < max_items and isinstance(specific_objectives, list):
        for row in specific_objectives[:2]:
            if not isinstance(row, dict):
                continue
            title = str(row.get("title") or "").strip()
            if title:
                hints.append(title)
            if len(hints) >= max_items:
                break
    expected_outcomes = toc_payload.get("expected_outcomes")
    if len(hints) < max_items and isinstance(expected_outcomes, list):
        for row in expected_outcomes[:2]:
            if not isinstance(row, dict):
                continue
            text = str(row.get("expected_change") or row.get("title") or "").strip()
            if text:
                hints.append(text)
            if len(hints) >= max_items:
                break
    results_chain = toc_payload.get("results_chain")
    if len(hints) < max_items and isinstance(results_chain, list):
        for row in results_chain[:2]:
            if not isinstance(row, dict):
                continue
            text = str(row.get("description") or row.get("title") or row.get("indicator_focus") or "").strip()
            if text:
                hints.append(text)
            if len(hints) >= max_items:
                break
    return " | ".join(hints)


def sanitize_revision_hint_for_query(revision_hint: str, *, max_items: int = 2, max_chars: int = 180) -> str:
    raw = str(revision_hint or "").strip()
    if not raw:
        return ""
    candidates: list[str] = []
    for chunk in re.split(r"[\n\r]+|[;|]+", raw):
        text = " ".join(str(chunk or "").split()).strip(" -:.")
        if not text:
            continue
        lowered = text.lower()
        if any(pattern.match(text) for pattern in _REVISION_NOISE_PATTERNS):
            continue
        if any(phrase in lowered for phrase in _REVISION_DROP_PHRASES):
            continue
        if len(text) < 12:
            continue
        candidates.append(text)
        if len(candidates) >= max_items:
            break
    joined = " | ".join(candidates)
    return joined[:max_chars].strip()


def build_stage_query_text(
    *,
    state: Dict[str, Any],
    stage: str,
    project: str,
    country: str,
    revision_hint: str = "",
    toc_payload: Any = None,
    include_revision_hint: bool = True,
) -> str:
    donor_id = state_donor_id(state, default="donor")
    input_context = state_input_context(state)
    context_hints = context_query_hints(input_context)
    donor_terms = donor_query_preset_terms(donor_id)
    proposal_mode_terms = _proposal_mode_query_terms(input_context)
    toc_hints = toc_query_hints(toc_payload)
    query_revision_hint = sanitize_revision_hint_for_query(revision_hint) if include_revision_hint else ""
    parts: list[str] = [
        str(stage or "").strip(),
        str(project or "").strip(),
        str(country or "").strip(),
        donor_id,
        context_hints,
        proposal_mode_terms,
        toc_hints,
        query_revision_hint,
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
