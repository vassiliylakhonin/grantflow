from __future__ import annotations

from typing import Any, Dict, List, Optional

ADVISORY_LLM_FINDING_LABELS = {
    "BASELINE_TARGET_MISSING",
    "INDICATOR_EVIDENCE_EXCERPTS",
    "OBJECTIVE_SPECIFICITY",
    "CAUSAL_LINK_DETAIL",
    "ASSUMPTION_EVIDENCE",
    "CROSS_CUTTING_INTEGRATION",
}

LLM_FINDING_LABEL_SEVERITY_POLICY = {
    "BASELINE_TARGET_MISSING": "advisory",
    "INDICATOR_EVIDENCE_EXCERPTS": "advisory",
    "OBJECTIVE_SPECIFICITY": "advisory",
    "CAUSAL_LINK_DETAIL": "advisory",
    "ASSUMPTION_EVIDENCE": "advisory",
    "CROSS_CUTTING_INTEGRATION": "advisory",
}

LLM_FINDING_LABEL_DONOR_POLICY_OVERRIDES: Dict[str, Dict[str, str]] = {
    "usaid": {},
    "worldbank": {},
    "eu": {},
    "giz": {},
    "state_department": {},
    "us_state_department": {},
}


def classify_llm_finding_label(msg: str, section: Optional[str] = None) -> str:
    lowered = str(msg or "").lower()
    if "baseline" in lowered and "target" in lowered and "indicator" in lowered:
        return "BASELINE_TARGET_MISSING"
    if "evidence excerpt" in lowered and "indicator" in lowered:
        return "INDICATOR_EVIDENCE_EXCERPTS"
    if "objective" in lowered and ("specific" in lowered or "measurable" in lowered):
        return "OBJECTIVE_SPECIFICITY"
    if ("weak causal link" in lowered or "weak causal links" in lowered) and (
        "output" in lowered or "outputs" in lowered
    ):
        return "CAUSAL_LINK_DETAIL"
    if "unrealistic assumption" in lowered or "unrealistic assumptions" in lowered:
        return "ASSUMPTION_EVIDENCE"
    if (
        "cross-cutting" in lowered
        or "gender equality" in lowered
        or "climate resilience" in lowered
        or "cross-cutting theme" in lowered
    ):
        return "CROSS_CUTTING_INTEGRATION"
    if str(section or "").lower() == "toc":
        return "GENERIC_TOC_REVIEW_FLAG"
    if str(section or "").lower() == "logframe":
        return "GENERIC_LOGFRAME_REVIEW_FLAG"
    return "GENERIC_LLM_REVIEW_FLAG"


def is_advisory_llm_message(msg: str) -> bool:
    lowered = str(msg or "").lower()
    advisory_signals = (
        ("baseline" in lowered and "target" in lowered and "indicator" in lowered),
        ("evidence excerpt" in lowered and "indicator" in lowered),
        ("objective" in lowered and ("specific" in lowered or "measurable" in lowered)),
        (
            ("weak causal link" in lowered or "weak causal links" in lowered)
            and ("output" in lowered or "outputs" in lowered)
            and ("ir" in lowered or "intermediate result" in lowered)
        ),
        (
            ("unrealistic assumption" in lowered or "unrealistic assumptions" in lowered)
            and (
                "motivated to participate" in lowered
                or "motivation" in lowered
                or "without clear evidence" in lowered
                or "without evidence" in lowered
                or "logical explanation" in lowered
            )
        ),
        (
            "missing cross-cutting" in lowered
            or ("cross-cutting" in lowered and "lacks a detailed plan" in lowered)
            or (
                "gender equality" in lowered
                and ("missing detailed strateg" in lowered or "lacks a detailed plan" in lowered)
            )
            or (
                "climate resilience" in lowered
                and ("cross-cutting theme" in lowered or "lack of integration" in lowered)
            )
        ),
    )
    return any(advisory_signals)


def llm_finding_policy_class(item: Dict[str, Any], *, donor_id: Optional[str] = None) -> str:
    label = str(item.get("label") or "").strip().upper()
    if label:
        donor_key = str(donor_id or "").strip().lower()
        donor_overrides = LLM_FINDING_LABEL_DONOR_POLICY_OVERRIDES.get(donor_key, {})
        if label in donor_overrides:
            return str(donor_overrides[label] or "default")
        return str(LLM_FINDING_LABEL_SEVERITY_POLICY.get(label) or "default")
    return "advisory" if is_advisory_llm_message(str(item.get("message") or "")) else "default"


def is_advisory_llm_finding(item: Dict[str, Any], *, donor_id: Optional[str] = None) -> bool:
    label = str(item.get("label") or "").strip().upper()
    if label and llm_finding_policy_class(item, donor_id=donor_id) == "advisory":
        return True
    return is_advisory_llm_message(str(item.get("message") or ""))


def build_llm_advisory_diagnostics(
    *,
    llm_fatal_flaw_items: List[Dict[str, Any]],
    advisory_ctx: Dict[str, Any],
    donor_id: Optional[str] = None,
) -> Dict[str, Any]:
    label_counts: Dict[str, int] = {}
    advisory_candidate_labels: List[str] = []
    advisory_candidate_count = 0
    valid_items = [i for i in llm_fatal_flaw_items if isinstance(i, dict)]
    for item in valid_items:
        label = str(item.get("label") or "GENERIC_LLM_REVIEW_FLAG").strip() or "GENERIC_LLM_REVIEW_FLAG"
        label_counts[label] = int(label_counts.get(label, 0)) + 1
        if llm_finding_policy_class(item, donor_id=donor_id) == "advisory":
            advisory_candidate_count += 1
            advisory_candidate_labels.append(label)
    return {
        "llm_finding_count": len(valid_items),
        "candidate_label_counts": label_counts,
        "advisory_candidate_count": advisory_candidate_count,
        "advisory_candidate_labels": sorted(set(advisory_candidate_labels)),
        "advisory_applies": bool(advisory_ctx.get("applies")),
        "advisory_rejected_reason": None if advisory_ctx.get("applies") else str(advisory_ctx.get("reason") or ""),
        "architect_threshold_hit_rate": advisory_ctx.get("architect_threshold_hit_rate"),
        "architect_rag_low_ratio": advisory_ctx.get("architect_rag_low_ratio"),
        "donor_id": str(donor_id or "").strip().lower() or None,
    }
