from __future__ import annotations

from typing import Optional

ARCHITECT_CITATION_HIGH_CONFIDENCE_THRESHOLD = 0.35
ARCHITECT_CITATION_DONOR_THRESHOLD_OVERRIDES: dict[str, float] = {
    "usaid": 0.38,
    "state_department": 0.4,
    "us_state_department": 0.4,
    "worldbank": 0.34,
    "eu": 0.34,
    "giz": 0.32,
}


def architect_donor_prompt_constraints(donor_id: str) -> str:
    donor_key = str(donor_id or "").strip().lower()
    common = (
        "Return a schema-valid object only. Use concise, concrete statements. "
        "Do not invent citations, codes, or official labels unless clearly grounded by provided evidence."
    )
    donor_rules = {
        "usaid": (
            "Use strict USAID hierarchy language and preserve logical cascade "
            "(Goal -> DO -> IR -> Outputs). Keep assumptions explicit and realistic."
        ),
        "eu": (
            "Follow EU intervention logic phrasing. Keep objective titles short and make rationale concrete "
            "and implementation-oriented."
        ),
        "giz": (
            "Emphasize implementation feasibility, partner roles, and sustainability factors. "
            "Avoid vague institutional-change claims without operational detail."
        ),
        "worldbank": (
            "Use implementation- and results-chain language suitable for development operations. "
            "Keep risks and assumptions specific to delivery constraints."
        ),
        "state_department": (
            "Prioritize context realism, stakeholder mapping, and risk-sensitive change pathways. "
            "Avoid overclaiming politically sensitive outcomes."
        ),
        "us_state_department": (
            "Prioritize context realism, stakeholder mapping, and risk-sensitive change pathways. "
            "Avoid overclaiming politically sensitive outcomes."
        ),
    }
    extra = donor_rules.get(donor_key)
    return f"{common} {extra}".strip() if extra else common


def sanitize_validation_error_hint(raw_hint: Optional[str], *, max_chars: int = 420) -> Optional[str]:
    if not raw_hint:
        return None
    lines = [line.strip() for line in str(raw_hint).splitlines() if line.strip()]
    if not lines:
        return None
    compact = " | ".join(lines[:4])
    return compact[:max_chars]


def architect_claim_confidence_threshold(*, donor_id: str, statement_path: str) -> float:
    donor_key = str(donor_id or "").strip().lower()
    threshold = ARCHITECT_CITATION_DONOR_THRESHOLD_OVERRIDES.get(
        donor_key, ARCHITECT_CITATION_HIGH_CONFIDENCE_THRESHOLD
    )
    path = str(statement_path or "").lower()
    if donor_key == "worldbank" and ".objectives[" in path and (path.endswith(".title") or path.endswith(".description")):
        return 0.25
    if any(token in path for token in ("assumption", "risk")):
        threshold += 0.12
    elif any(token in path for token in ("goal", "objective", "outcome", "result")):
        threshold += 0.05
    elif any(token in path for token in ("description", "rationale")):
        threshold += 0.02
    return round(max(0.1, min(threshold, 0.95)), 2)
