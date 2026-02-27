from __future__ import annotations

from typing import Any, Dict, Optional

from grantflow.swarm.citations import citation_traceability_status


def evaluate_grounding_gate(
    state: Dict[str, Any],
    *,
    mode: str = "warn",
    min_citations_for_calibration: int = 5,
    max_weak_rag_or_fallback_ratio: float = 0.6,
    max_low_confidence_ratio: float = 0.75,
    max_traceability_gap_ratio: float = 0.6,
) -> Dict[str, Any]:
    mode_normalized = str(mode or "warn").strip().lower()
    if mode_normalized not in {"off", "warn", "strict"}:
        mode_normalized = "warn"

    raw_citations = state.get("citations")
    citations = raw_citations if isinstance(raw_citations, list) else []
    citation_count = 0
    low_confidence_count = 0
    rag_low_confidence_count = 0
    fallback_namespace_count = 0
    traceability_complete_count = 0
    traceability_partial_count = 0
    traceability_missing_count = 0

    for citation in citations:
        if not isinstance(citation, dict):
            continue
        citation_count += 1
        citation_type = str(citation.get("citation_type") or "")
        if citation_type == "rag_low_confidence":
            rag_low_confidence_count += 1
        if citation_type == "fallback_namespace":
            fallback_namespace_count += 1
        traceability_status = citation_traceability_status(citation)
        if traceability_status == "complete":
            traceability_complete_count += 1
        elif traceability_status == "partial":
            traceability_partial_count += 1
        else:
            traceability_missing_count += 1
        confidence = citation.get("citation_confidence")
        try:
            conf_value = float(confidence) if confidence is not None else None
        except (TypeError, ValueError):
            conf_value = None
        if conf_value is not None and conf_value < 0.3:
            low_confidence_count += 1

    raw_architect_retrieval = state.get("architect_retrieval")
    architect_retrieval = raw_architect_retrieval if isinstance(raw_architect_retrieval, dict) else {}
    architect_retrieval_enabled = bool(architect_retrieval.get("enabled")) if architect_retrieval else False
    try:
        architect_retrieval_hits_count: Optional[int] = (
            int(architect_retrieval.get("hits_count")) if architect_retrieval.get("hits_count") is not None else None
        )
    except (TypeError, ValueError):
        architect_retrieval_hits_count = None

    weak_rag_or_fallback_count = rag_low_confidence_count + fallback_namespace_count
    weak_rag_or_fallback_ratio = (
        round(weak_rag_or_fallback_count / citation_count, 4) if citation_count and weak_rag_or_fallback_count else 0.0
    )
    low_confidence_ratio = (
        round(low_confidence_count / citation_count, 4) if citation_count and low_confidence_count else 0.0
    )
    traceability_gap_count = traceability_partial_count + traceability_missing_count
    traceability_gap_ratio = (
        round(traceability_gap_count / citation_count, 4) if citation_count and traceability_gap_count else 0.0
    )

    reasons: list[str] = []
    if architect_retrieval_enabled and architect_retrieval_hits_count == 0:
        reasons.append("architect_retrieval_no_hits")

    if citation_count >= min_citations_for_calibration:
        if weak_rag_or_fallback_ratio >= max_weak_rag_or_fallback_ratio:
            reasons.append("fallback_or_low_rag_citations_dominate")
        if low_confidence_ratio >= max_low_confidence_ratio:
            reasons.append("low_confidence_citations_dominate")
        if traceability_gap_ratio >= max_traceability_gap_ratio:
            reasons.append("citation_traceability_gaps_dominate")

    passed = mode_normalized == "off" or not reasons
    blocking = mode_normalized == "strict" and not passed
    severity = "high" if blocking else ("medium" if not passed else "none")
    summary = "ok" if passed else "; ".join(reasons)

    return {
        "mode": mode_normalized,
        "passed": passed,
        "blocking": blocking,
        "severity": severity,
        "summary": summary,
        "reasons": reasons,
        "citation_count": citation_count,
        "low_confidence_citation_count": low_confidence_count,
        "rag_low_confidence_citation_count": rag_low_confidence_count,
        "fallback_namespace_citation_count": fallback_namespace_count,
        "traceability_complete_citation_count": traceability_complete_count,
        "traceability_partial_citation_count": traceability_partial_count,
        "traceability_missing_citation_count": traceability_missing_count,
        "traceability_gap_citation_count": traceability_gap_count,
        "traceability_gap_ratio": traceability_gap_ratio,
        "weak_rag_or_fallback_ratio": weak_rag_or_fallback_ratio,
        "low_confidence_ratio": low_confidence_ratio,
        "architect_retrieval_enabled": architect_retrieval_enabled,
        "architect_retrieval_hits_count": architect_retrieval_hits_count,
        "thresholds": {
            "min_citations_for_calibration": min_citations_for_calibration,
            "max_weak_rag_or_fallback_ratio": max_weak_rag_or_fallback_ratio,
            "max_low_confidence_ratio": max_low_confidence_ratio,
            "max_traceability_gap_ratio": max_traceability_gap_ratio,
        },
    }
