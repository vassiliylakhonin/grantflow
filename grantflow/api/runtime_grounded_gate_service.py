from __future__ import annotations

from typing import Any, Dict

from grantflow.api.constants import GROUNDING_POLICY_MODES
from grantflow.core.config import config
from grantflow.swarm.citations import (
    citation_traceability_status,
    is_non_retrieval_citation_type,
    is_retrieval_grounded_citation_type,
)


def _normalize_grounding_policy_mode(raw_mode: Any) -> str:
    mode = str(raw_mode or "warn").strip().lower()
    if mode not in GROUNDING_POLICY_MODES:
        return "warn"
    return mode


def _configured_runtime_grounded_quality_gate_mode() -> str:
    runtime_mode = getattr(config.graph, "runtime_grounded_quality_gate_mode", None)
    if str(runtime_mode or "").strip():
        return _normalize_grounding_policy_mode(runtime_mode)
    return "strict"


def _runtime_grounded_quality_gate_thresholds() -> Dict[str, Any]:
    min_citations_raw = getattr(config.graph, "runtime_grounded_quality_gate_min_citations", 5)
    max_non_retrieval_rate_raw = getattr(
        config.graph,
        "runtime_grounded_quality_gate_max_non_retrieval_citation_rate",
        0.35,
    )
    min_retrieval_grounded_citations_raw = getattr(
        config.graph,
        "runtime_grounded_quality_gate_min_retrieval_grounded_citations",
        2,
    )

    try:
        min_citations = int(min_citations_raw)
    except (TypeError, ValueError):
        min_citations = 5
    try:
        max_non_retrieval_rate = float(max_non_retrieval_rate_raw)
    except (TypeError, ValueError):
        max_non_retrieval_rate = 0.35
    try:
        min_retrieval_grounded_citations = int(min_retrieval_grounded_citations_raw)
    except (TypeError, ValueError):
        min_retrieval_grounded_citations = 2

    min_citations = max(0, min(min_citations, 10000))
    max_non_retrieval_rate = max(0.0, min(max_non_retrieval_rate, 1.0))
    min_retrieval_grounded_citations = max(0, min(min_retrieval_grounded_citations, 10000))
    return {
        "min_citations_for_gate": min_citations,
        "max_non_retrieval_citation_rate": round(max_non_retrieval_rate, 4),
        "min_retrieval_grounded_citations": min_retrieval_grounded_citations,
    }


def _runtime_grounded_gate_section(citation: Dict[str, Any]) -> str:
    stage = str(citation.get("stage") or "").strip().lower()
    if stage == "architect":
        return "toc"
    if stage == "mel":
        return "logframe"

    statement_path = str(citation.get("statement_path") or "").strip().lower()
    if statement_path:
        if statement_path == "toc" or statement_path.startswith(
            ("goal", "objective", "outcome", "output", "assumption", "activity")
        ):
            return "toc"
        return "toc"

    used_for = str(citation.get("used_for") or "").strip().lower()
    if used_for.startswith(("ind", "mel", "logframe", "lf_")):
        return "logframe"
    return "general"


def _runtime_grounded_gate_evidence_row(citation: Dict[str, Any]) -> Dict[str, Any]:
    row: Dict[str, Any] = {}
    allowed_keys = (
        "stage",
        "citation_type",
        "doc_id",
        "source",
        "page",
        "retrieval_rank",
        "retrieval_confidence",
        "statement_path",
        "used_for",
        "label",
    )
    for key in allowed_keys:
        value = citation.get(key)
        if value in (None, ""):
            continue
        if isinstance(value, (str, int, float, bool)):
            row[key] = value
        else:
            row[key] = str(value)
    row["traceability_status"] = citation_traceability_status(citation)
    return row


def _evaluate_runtime_grounded_quality_gate_from_state(state: Any) -> Dict[str, Any]:
    mode = _configured_runtime_grounded_quality_gate_mode()
    thresholds = _runtime_grounded_quality_gate_thresholds()
    min_citations_for_gate = int(thresholds["min_citations_for_gate"])
    max_non_retrieval_citation_rate = float(thresholds["max_non_retrieval_citation_rate"])
    min_retrieval_grounded_citations = int(thresholds["min_retrieval_grounded_citations"])

    state_dict = state if isinstance(state, dict) else {}
    llm_mode = bool(state_dict.get("llm_mode"))
    architect_rag_enabled = bool(state_dict.get("architect_rag_enabled", True))
    raw_architect_retrieval = state_dict.get("architect_retrieval")
    architect_retrieval = raw_architect_retrieval if isinstance(raw_architect_retrieval, dict) else {}
    retrieval_expected = (
        bool(architect_retrieval.get("enabled"))
        if isinstance(architect_retrieval.get("enabled"), bool)
        else architect_rag_enabled
    )
    applicable = bool(llm_mode and architect_rag_enabled and retrieval_expected)

    raw_citations = state_dict.get("citations")
    citations = [item for item in raw_citations if isinstance(item, dict)] if isinstance(raw_citations, list) else []
    citation_count = len(citations)
    non_retrieval_citation_count = 0
    retrieval_grounded_citation_count = 0
    section_counters: Dict[str, Dict[str, int]] = {
        "toc": {
            "citation_count": 0,
            "non_retrieval_citation_count": 0,
            "retrieval_grounded_citation_count": 0,
            "traceability_complete_citation_count": 0,
            "traceability_gap_citation_count": 0,
        },
        "logframe": {
            "citation_count": 0,
            "non_retrieval_citation_count": 0,
            "retrieval_grounded_citation_count": 0,
            "traceability_complete_citation_count": 0,
            "traceability_gap_citation_count": 0,
        },
        "general": {
            "citation_count": 0,
            "non_retrieval_citation_count": 0,
            "retrieval_grounded_citation_count": 0,
            "traceability_complete_citation_count": 0,
            "traceability_gap_citation_count": 0,
        },
    }
    section_evidence: Dict[str, list[Dict[str, Any]]] = {"toc": [], "logframe": [], "general": []}

    for citation in citations:
        section = _runtime_grounded_gate_section(citation)
        if section not in section_counters:
            section = "general"
        section_row = section_counters[section]
        section_row["citation_count"] += 1
        citation_type = citation.get("citation_type")
        if is_non_retrieval_citation_type(citation_type):
            non_retrieval_citation_count += 1
            section_row["non_retrieval_citation_count"] += 1
        if is_retrieval_grounded_citation_type(citation_type):
            retrieval_grounded_citation_count += 1
            section_row["retrieval_grounded_citation_count"] += 1
        if citation_traceability_status(citation) == "complete":
            section_row["traceability_complete_citation_count"] += 1
        else:
            section_row["traceability_gap_citation_count"] += 1
        if len(section_evidence[section]) < 3:
            section_evidence[section].append(_runtime_grounded_gate_evidence_row(citation))

    non_retrieval_citation_rate = round(non_retrieval_citation_count / citation_count, 4) if citation_count else None
    retrieval_grounded_citation_rate = (
        round(retrieval_grounded_citation_count / citation_count, 4) if citation_count else None
    )
    section_signals: Dict[str, Dict[str, Any]] = {}
    for section, counters in section_counters.items():
        section_total = int(counters.get("citation_count") or 0)
        section_non_retrieval = int(counters.get("non_retrieval_citation_count") or 0)
        section_retrieval_grounded = int(counters.get("retrieval_grounded_citation_count") or 0)
        section_traceability_complete = int(counters.get("traceability_complete_citation_count") or 0)
        section_traceability_gap = int(counters.get("traceability_gap_citation_count") or 0)
        section_signals[section] = {
            "citation_count": section_total,
            "non_retrieval_citation_count": section_non_retrieval,
            "retrieval_grounded_citation_count": section_retrieval_grounded,
            "traceability_complete_citation_count": section_traceability_complete,
            "traceability_gap_citation_count": section_traceability_gap,
            "non_retrieval_citation_rate": (round(section_non_retrieval / section_total, 4) if section_total else None),
            "retrieval_grounded_citation_rate": (
                round(section_retrieval_grounded / section_total, 4) if section_total else None
            ),
            "traceability_complete_citation_rate": (
                round(section_traceability_complete / section_total, 4) if section_total else None
            ),
            "traceability_gap_citation_rate": (
                round(section_traceability_gap / section_total, 4) if section_total else None
            ),
        }

    reasons: list[str] = []
    reason_details: list[Dict[str, Any]] = []
    failed_sections: set[str] = set()

    def _append_reason_detail(
        *,
        code: str,
        message: str,
        section: str = "overall",
        observed: Any = None,
        threshold: Any = None,
    ) -> None:
        row: Dict[str, Any] = {"code": code, "message": message, "section": section}
        if observed is not None:
            row["observed"] = observed
        if threshold is not None:
            row["threshold"] = threshold
        reason_details.append(row)
        if section in {"toc", "logframe"}:
            failed_sections.add(section)

    if applicable and mode != "off":
        if citation_count < min_citations_for_gate:
            reasons.append("insufficient_citations_for_runtime_grounded_gate")
            _append_reason_detail(
                code="insufficient_citations_for_runtime_grounded_gate",
                message="Total citation count is below runtime grounded gate minimum.",
                section="overall",
                observed=citation_count,
                threshold=min_citations_for_gate,
            )
        if non_retrieval_citation_rate is None or non_retrieval_citation_rate > max_non_retrieval_citation_rate:
            reasons.append("non_retrieval_citation_rate_above_max")
            _append_reason_detail(
                code="non_retrieval_citation_rate_above_max",
                message="Non-retrieval citations exceed allowed maximum rate.",
                section="overall",
                observed=non_retrieval_citation_rate,
                threshold=max_non_retrieval_citation_rate,
            )
            for section in ("toc", "logframe"):
                section_rate = section_signals.get(section, {}).get("non_retrieval_citation_rate")
                section_count = int(section_signals.get(section, {}).get("citation_count") or 0)
                if section_count <= 0 or section_rate is None:
                    continue
                if float(section_rate) > max_non_retrieval_citation_rate:
                    _append_reason_detail(
                        code="section_non_retrieval_citation_rate_above_max",
                        message=f"{section} non-retrieval citation rate exceeds allowed maximum.",
                        section=section,
                        observed=section_rate,
                        threshold=max_non_retrieval_citation_rate,
                    )
        if retrieval_grounded_citation_count < min_retrieval_grounded_citations:
            reasons.append("retrieval_grounded_citation_count_below_min")
            _append_reason_detail(
                code="retrieval_grounded_citation_count_below_min",
                message="Retrieval-grounded citations are below required minimum.",
                section="overall",
                observed=retrieval_grounded_citation_count,
                threshold=min_retrieval_grounded_citations,
            )
            for section in ("toc", "logframe"):
                section_count = int(section_signals.get(section, {}).get("citation_count") or 0)
                section_grounded = int(section_signals.get(section, {}).get("retrieval_grounded_citation_count") or 0)
                if section_count > 0 and section_grounded <= 0:
                    _append_reason_detail(
                        code="section_missing_retrieval_grounding",
                        message=f"{section} has citations but none are retrieval-grounded.",
                        section=section,
                        observed=section_grounded,
                        threshold=1,
                    )

    if not applicable:
        passed = True
        blocking = False
        summary = "not_applicable_for_non_llm_or_retrieval_disabled"
        risk_level = "none"
    elif mode == "off":
        passed = True
        blocking = False
        summary = "runtime_grounded_quality_gate_off"
        risk_level = "none"
    else:
        passed = not reasons
        blocking = mode == "strict" and not passed
        summary = "runtime_grounded_signals_ok" if passed else ",".join(reasons)
        risk_level = "low" if passed else "high"

    failed_section_list = sorted(failed_sections)
    evidence_sections = failed_section_list or [section for section in ("toc", "logframe") if section_evidence[section]]
    evidence = {
        "sample_citations_by_section": {
            section: list(section_evidence.get(section) or [])[:3] for section in evidence_sections
        },
        "failed_sections": failed_section_list,
    }

    return {
        "mode": mode,
        "applicable": applicable,
        "passed": passed,
        "blocking": blocking,
        "go_ahead": not blocking,
        "risk_level": risk_level,
        "summary": summary,
        "reasons": reasons,
        "llm_mode": llm_mode,
        "architect_rag_enabled": architect_rag_enabled,
        "retrieval_expected": retrieval_expected,
        "citation_count": citation_count,
        "non_retrieval_citation_count": non_retrieval_citation_count,
        "retrieval_grounded_citation_count": retrieval_grounded_citation_count,
        "non_retrieval_citation_rate": non_retrieval_citation_rate,
        "retrieval_grounded_citation_rate": retrieval_grounded_citation_rate,
        "reason_details": reason_details,
        "section_signals": section_signals,
        "failed_sections": failed_section_list,
        "evidence": evidence,
        "thresholds": thresholds,
    }
