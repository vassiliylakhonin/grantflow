from __future__ import annotations

from typing import Any, Dict, Optional

from grantflow.api.grounding_policy_service import (
    _configured_export_grounding_policy_mode,
    _evaluate_mel_grounding_policy_from_state,
)
from grantflow.core.config import config
from grantflow.exporters.donor_contracts import (
    evaluate_export_contract_gate,
    normalize_export_contract_policy_mode,
)
from grantflow.swarm.findings import state_critic_findings, write_state_critic_findings
from grantflow.swarm.state_contract import state_donor_id


def _configured_export_contract_policy_mode() -> str:
    contract_mode = getattr(config.graph, "export_contract_policy_mode", None)
    if str(contract_mode or "").strip():
        return normalize_export_contract_policy_mode(contract_mode)
    return _configured_export_grounding_policy_mode()


def _attach_export_contract_gate(state: Any) -> Dict[str, Any]:
    state_dict: dict[str, Any] = state if isinstance(state, dict) else {}
    donor_id = state_donor_id(state_dict, default="grantflow")
    raw_toc = state_dict.get("toc_draft")
    toc_draft = raw_toc if isinstance(raw_toc, dict) else {}
    if not toc_draft:
        raw_toc_fallback = state_dict.get("toc")
        if isinstance(raw_toc_fallback, dict):
            toc_draft = raw_toc_fallback
    gate = evaluate_export_contract_gate(
        donor_id=donor_id,
        toc_payload=toc_draft,
        policy_mode=_configured_export_contract_policy_mode(),
    )
    state_dict["export_contract_gate"] = gate
    return gate


def _state_grounding_gate(state: Any) -> Dict[str, Any]:
    if not isinstance(state, dict):
        return {}
    gate = state.get("grounding_gate")
    return gate if isinstance(gate, dict) else {}


def _state_runtime_grounded_quality_gate(state: Any) -> Dict[str, Any]:
    if not isinstance(state, dict):
        return {}
    gate = state.get("grounded_quality_gate")
    return gate if isinstance(gate, dict) else {}


def _append_runtime_grounded_quality_gate_finding(state: dict, gate: Dict[str, Any]) -> None:
    if not isinstance(state, dict):
        return
    reasons = gate.get("reasons") if isinstance(gate.get("reasons"), list) else []
    reason_details = gate.get("reason_details") if isinstance(gate.get("reason_details"), list) else []
    raw_failed_sections = gate.get("failed_sections")
    failed_sections: list[Any] = raw_failed_sections if isinstance(raw_failed_sections, list) else []
    related_sections = [
        token
        for token in [str(section or "").strip().lower() for section in failed_sections]
        if token in {"toc", "logframe", "general"}
    ]
    primary_section = related_sections[0] if related_sections else "general"
    thresholds = gate.get("thresholds") if isinstance(gate.get("thresholds"), dict) else {}
    non_retrieval_rate = gate.get("non_retrieval_citation_rate")
    retrieval_grounded_count = gate.get("retrieval_grounded_citation_count")
    citation_count = gate.get("citation_count")
    summary = str(gate.get("summary") or "").strip() or "runtime grounded quality gate failed"
    rationale = (
        f"{summary}; citation_count={citation_count}; "
        f"non_retrieval_rate={non_retrieval_rate}; "
        f"retrieval_grounded_count={retrieval_grounded_count}; "
        f"thresholds={thresholds}; reasons={reasons}; "
        f"reason_details={reason_details}; failed_sections={failed_sections}"
    )
    existing = state_critic_findings(state, default_source="rules")
    existing_codes = {str(item.get("code") or "").strip().upper() for item in existing if isinstance(item, dict)}
    if "RUNTIME_GROUNDED_QUALITY_GATE_BLOCK" in existing_codes:
        return
    new_finding = {
        "code": "RUNTIME_GROUNDED_QUALITY_GATE_BLOCK",
        "severity": "high",
        "section": primary_section,
        "related_sections": related_sections,
        "version_id": None,
        "message": "Grounded quality gate blocked finalization for LLM generation.",
        "rationale": rationale,
        "fix_suggestion": (
            "Upload additional donor/country evidence and rerun generation to increase retrieval-grounded citations "
            "and reduce non-retrieval citations."
        ),
        "fix_hint": "Use /ingest for relevant policy/context PDFs, then rerun /generate in grounded mode.",
        "source": "rules",
    }
    write_state_critic_findings(
        state,
        list(existing) + [new_finding],
        previous_items=existing,
        default_source="rules",
    )


def _grounding_gate_block_reason(state: Any) -> Optional[str]:
    gate = _state_grounding_gate(state)
    if not gate:
        return None
    if not bool(gate.get("blocking")):
        return None
    if str(gate.get("mode") or "").lower() != "strict":
        return None
    summary = str(gate.get("summary") or "").strip() or "weak grounding signals"
    return f"Grounding gate (strict) blocked finalization: {summary}"


def _runtime_grounded_quality_gate_block_reason(state: Any) -> Optional[str]:
    gate = _state_runtime_grounded_quality_gate(state)
    if not gate:
        return None
    if not bool(gate.get("blocking")):
        return None
    if str(gate.get("mode") or "").lower() != "strict":
        return None
    summary = str(gate.get("summary") or "").strip() or "runtime grounded signals not acceptable"
    return f"Grounded quality gate (strict) blocked finalization: {summary}"


def _mel_grounding_policy_block_reason(state: Any) -> Optional[str]:
    policy = _evaluate_mel_grounding_policy_from_state(state)
    state_dict = state if isinstance(state, dict) else {}
    state_dict["mel_grounding_policy"] = policy
    if not bool(policy.get("blocking")):
        return None
    summary = str(policy.get("summary") or "").strip() or "weak mel grounding signals"
    return f"MEL grounding policy (strict) blocked finalization: {summary}"
