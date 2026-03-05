from __future__ import annotations

from typing import Any, Dict, Optional

from grantflow.api.constants import (
    GENERATE_PREFLIGHT_DEFAULT_DOC_FAMILIES,
    GROUNDING_POLICY_MODES,
    PREFLIGHT_CRITICAL_DOC_FAMILY_MIN_UPLOADS,
)
from grantflow.api.job_store_service import _ingest_inventory
from grantflow.api.public_views import public_ingest_inventory_payload
from grantflow.api.tenant import _normalize_tenant_candidate, _tenant_rag_namespace
from grantflow.core.config import config
from grantflow.memory_bank.vector_store import vector_store
from grantflow.swarm.citations import citation_traceability_status
from grantflow.swarm.nodes.architect_generation import generate_toc_under_contract
from grantflow.swarm.nodes.architect_retrieval import retrieve_architect_evidence
from grantflow.swarm.retrieval_query import donor_query_preset_list
from grantflow.swarm.state_contract import build_graph_state


def _dedupe_doc_families(values: list[Any]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for item in values:
        token = str(item or "").strip()
        if not token or token in seen:
            continue
        out.append(token)
        seen.add(token)
    return out


def _preflight_expected_doc_families(
    *,
    donor_id: str,
    client_metadata: Optional[Dict[str, Any]],
) -> list[str]:
    metadata = client_metadata if isinstance(client_metadata, dict) else {}
    raw_rag_readiness = metadata.get("rag_readiness")
    rag_readiness: Dict[str, Any] = raw_rag_readiness if isinstance(raw_rag_readiness, dict) else {}
    expected = rag_readiness.get("expected_doc_families")
    if isinstance(expected, list):
        deduped = _dedupe_doc_families(expected)
        if deduped:
            return deduped
    donor_key = str(donor_id or "").strip().lower()
    defaults = GENERATE_PREFLIGHT_DEFAULT_DOC_FAMILIES.get(donor_key)
    if defaults:
        return list(defaults)
    return ["donor_policy", "country_context"]


def _preflight_doc_family_min_uploads_map(
    *,
    expected_doc_families: list[str],
    client_metadata: Optional[Dict[str, Any]],
) -> Dict[str, int]:
    metadata = client_metadata if isinstance(client_metadata, dict) else {}
    raw_rag_readiness = metadata.get("rag_readiness")
    rag_readiness: Dict[str, Any] = raw_rag_readiness if isinstance(raw_rag_readiness, dict) else {}
    raw_map = rag_readiness.get("doc_family_min_uploads")
    override_map = raw_map if isinstance(raw_map, dict) else {}
    out: Dict[str, int] = {}
    for family in expected_doc_families:
        token = str(family or "").strip()
        if not token:
            continue
        raw_override = override_map.get(token)
        try:
            min_uploads = (
                int(raw_override)
                if raw_override is not None
                else int(PREFLIGHT_CRITICAL_DOC_FAMILY_MIN_UPLOADS.get(token, 1))
            )
        except (TypeError, ValueError):
            min_uploads = int(PREFLIGHT_CRITICAL_DOC_FAMILY_MIN_UPLOADS.get(token, 1))
        out[token] = max(1, min_uploads)
    return out


def _preflight_doc_family_depth_profile(
    *,
    expected_doc_families: list[str],
    doc_family_counts: Dict[str, Any],
    min_uploads_by_family: Dict[str, int],
) -> Dict[str, Any]:
    expected = _dedupe_doc_families(expected_doc_families)
    if not expected:
        return {
            "depth_ready_doc_families": [],
            "depth_gap_doc_families": [],
            "depth_ready_count": 0,
            "depth_gap_count": 0,
            "depth_coverage_rate": None,
        }
    depth_ready: list[str] = []
    depth_gap: list[str] = []
    for family in expected:
        try:
            count_value = int(doc_family_counts.get(family) or 0)
        except (TypeError, ValueError):
            count_value = 0
        min_required = int(min_uploads_by_family.get(family) or 1)
        if count_value >= max(1, min_required):
            depth_ready.append(family)
        else:
            depth_gap.append(family)
    expected_count = len(expected)
    depth_ready_count = len(depth_ready)
    depth_gap_count = len(depth_gap)
    depth_coverage_rate = round(depth_ready_count / expected_count, 4) if expected_count else None
    return {
        "depth_ready_doc_families": depth_ready,
        "depth_gap_doc_families": depth_gap,
        "depth_ready_count": depth_ready_count,
        "depth_gap_count": depth_gap_count,
        "depth_coverage_rate": depth_coverage_rate,
    }


def _preflight_input_context(client_metadata: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    metadata = client_metadata if isinstance(client_metadata, dict) else {}
    raw = metadata.get("_preflight_input_context")
    if isinstance(raw, dict):
        return dict(raw)
    return {}


def _preflight_severity_max(severities: list[str]) -> str:
    rank = {"none": 0, "low": 1, "medium": 2, "high": 3}
    best = "none"
    for raw in severities:
        level = str(raw or "").strip().lower()
        if rank.get(level, 0) > rank.get(best, 0):
            best = level
    return best


def _normalize_grounding_policy_mode(raw_mode: Any) -> str:
    mode = str(raw_mode or "warn").strip().lower()
    if mode not in GROUNDING_POLICY_MODES:
        return "warn"
    return mode


def _configured_preflight_grounding_policy_mode() -> str:
    preflight_mode = getattr(config.graph, "preflight_grounding_policy_mode", None)
    if str(preflight_mode or "").strip():
        return _normalize_grounding_policy_mode(preflight_mode)
    return _normalize_grounding_policy_mode(getattr(config.graph, "grounding_gate_mode", "warn"))


def _preflight_grounding_policy_thresholds() -> Dict[str, Any]:
    high_cov_raw = getattr(config.graph, "preflight_grounding_high_risk_coverage_threshold", 0.5)
    medium_cov_raw = getattr(config.graph, "preflight_grounding_medium_risk_coverage_threshold", 0.8)
    high_depth_cov_raw = getattr(config.graph, "preflight_grounding_high_risk_depth_coverage_threshold", 0.2)
    medium_depth_cov_raw = getattr(config.graph, "preflight_grounding_medium_risk_depth_coverage_threshold", 0.5)
    min_uploads_raw = getattr(config.graph, "preflight_grounding_min_uploads", 3)
    min_key_claim_coverage_raw = getattr(config.graph, "preflight_grounding_min_key_claim_coverage_rate", 0.6)
    max_fallback_claim_ratio_raw = getattr(config.graph, "preflight_grounding_max_fallback_claim_ratio", 0.8)
    max_traceability_gap_rate_raw = getattr(config.graph, "preflight_grounding_max_traceability_gap_rate", 0.6)
    min_threshold_hit_rate_raw = getattr(config.graph, "preflight_grounding_min_threshold_hit_rate", 0.4)

    try:
        high_cov = float(high_cov_raw)
    except (TypeError, ValueError):
        high_cov = 0.5
    try:
        medium_cov = float(medium_cov_raw)
    except (TypeError, ValueError):
        medium_cov = 0.8
    try:
        high_depth_cov = float(high_depth_cov_raw)
    except (TypeError, ValueError):
        high_depth_cov = 0.2
    try:
        medium_depth_cov = float(medium_depth_cov_raw)
    except (TypeError, ValueError):
        medium_depth_cov = 0.5
    try:
        min_uploads = int(min_uploads_raw)
    except (TypeError, ValueError):
        min_uploads = 3
    try:
        min_key_claim_coverage = float(min_key_claim_coverage_raw)
    except (TypeError, ValueError):
        min_key_claim_coverage = 0.6
    try:
        max_fallback_claim_ratio = float(max_fallback_claim_ratio_raw)
    except (TypeError, ValueError):
        max_fallback_claim_ratio = 0.8
    try:
        max_traceability_gap_rate = float(max_traceability_gap_rate_raw)
    except (TypeError, ValueError):
        max_traceability_gap_rate = 0.6
    try:
        min_threshold_hit_rate = float(min_threshold_hit_rate_raw)
    except (TypeError, ValueError):
        min_threshold_hit_rate = 0.4

    high_cov = max(0.0, min(high_cov, 1.0))
    medium_cov = max(0.0, min(medium_cov, 1.0))
    if medium_cov < high_cov:
        medium_cov = high_cov
    high_depth_cov = max(0.0, min(high_depth_cov, 1.0))
    medium_depth_cov = max(0.0, min(medium_depth_cov, 1.0))
    if medium_depth_cov < high_depth_cov:
        medium_depth_cov = high_depth_cov
    min_uploads = max(1, min_uploads)
    min_key_claim_coverage = max(0.0, min(min_key_claim_coverage, 1.0))
    max_fallback_claim_ratio = max(0.0, min(max_fallback_claim_ratio, 1.0))
    max_traceability_gap_rate = max(0.0, min(max_traceability_gap_rate, 1.0))
    min_threshold_hit_rate = max(0.0, min(min_threshold_hit_rate, 1.0))

    return {
        "high_risk_coverage_threshold": round(high_cov, 4),
        "medium_risk_coverage_threshold": round(medium_cov, 4),
        "high_risk_depth_coverage_threshold": round(high_depth_cov, 4),
        "medium_risk_depth_coverage_threshold": round(medium_depth_cov, 4),
        "min_uploads": min_uploads,
        "min_key_claim_coverage_rate": round(min_key_claim_coverage, 4),
        "max_fallback_claim_ratio": round(max_fallback_claim_ratio, 4),
        "max_traceability_gap_rate": round(max_traceability_gap_rate, 4),
        "min_threshold_hit_rate": round(min_threshold_hit_rate, 4),
    }


def _estimate_preflight_architect_claims(
    *,
    donor_id: str,
    strategy: Any,
    namespace: str,
    input_context: Optional[Dict[str, Any]],
    tenant_id: Optional[str] = None,
    architect_rag_enabled: bool = True,
) -> Dict[str, Any]:
    if not str(namespace or "").strip():
        return {
            "available": False,
            "reason": "namespace_missing",
            "retrieval_expected": bool(architect_rag_enabled),
        }
    if not isinstance(input_context, dict) or not input_context:
        return {
            "available": False,
            "reason": "input_context_missing",
            "retrieval_expected": bool(architect_rag_enabled),
        }

    state = build_graph_state(
        donor_id=donor_id,
        input_context=input_context,
        donor_strategy=strategy,
        tenant_id=tenant_id,
        rag_namespace=namespace,
        llm_mode=False,
        max_iterations=int(getattr(config.graph, "max_iterations", 3) or 3),
        extras={
            "architect_rag_enabled": bool(architect_rag_enabled),
        },
    )
    try:
        retrieval_summary, retrieval_hits = retrieve_architect_evidence(state, namespace)
        _toc, _validation, generation_meta, claim_citations = generate_toc_under_contract(
            state=state,
            strategy=strategy,
            evidence_hits=retrieval_hits,
        )
    except Exception as exc:
        return {
            "available": False,
            "reason": "estimation_error",
            "error": str(exc),
            "retrieval_expected": bool(architect_rag_enabled),
        }

    architect_claim_citations = [
        c
        for c in claim_citations
        if isinstance(c, dict) and str(c.get("used_for") or "") == "toc_claim" and str(c.get("statement_path") or "").strip()
    ]
    claim_coverage = generation_meta.get("claim_coverage") if isinstance(generation_meta, dict) else {}
    claim_coverage = claim_coverage if isinstance(claim_coverage, dict) else {}

    claim_count = len(architect_claim_citations)
    fallback_claim_count = sum(
        1 for c in architect_claim_citations if str(c.get("citation_type") or "") == "fallback_namespace"
    )
    traceability_complete_count = sum(
        1 for c in architect_claim_citations if citation_traceability_status(c) == "complete"
    )
    traceability_partial_count = sum(1 for c in architect_claim_citations if citation_traceability_status(c) == "partial")
    traceability_missing_count = sum(1 for c in architect_claim_citations if citation_traceability_status(c) == "missing")
    traceability_gap_count = traceability_partial_count + traceability_missing_count
    threshold_considered = 0
    threshold_hits = 0
    for citation in architect_claim_citations:
        threshold_raw = citation.get("confidence_threshold")
        confidence_raw = citation.get("citation_confidence")
        try:
            threshold = float(threshold_raw) if threshold_raw is not None else None
            confidence = float(confidence_raw) if confidence_raw is not None else None
        except (TypeError, ValueError):
            threshold = None
            confidence = None
        if threshold is None or confidence is None:
            continue
        threshold_considered += 1
        if confidence >= threshold:
            threshold_hits += 1

    def _safe_rate(numerator: int, denominator: int) -> Optional[float]:
        if denominator <= 0:
            return None
        return round(numerator / denominator, 4)

    key_claim_coverage_ratio = claim_coverage.get("key_claim_coverage_ratio")
    fallback_claim_ratio = claim_coverage.get("fallback_claim_ratio")
    try:
        key_claim_coverage_ratio = round(float(key_claim_coverage_ratio), 4) if key_claim_coverage_ratio is not None else None
    except (TypeError, ValueError):
        key_claim_coverage_ratio = None
    try:
        fallback_claim_ratio = round(float(fallback_claim_ratio), 4) if fallback_claim_ratio is not None else None
    except (TypeError, ValueError):
        fallback_claim_ratio = None

    if fallback_claim_ratio is None:
        fallback_claim_ratio = _safe_rate(fallback_claim_count, claim_count)

    return {
        "available": True,
        "reason": "ok",
        "claim_citation_count": claim_count,
        "key_claim_coverage_ratio": key_claim_coverage_ratio,
        "fallback_claim_ratio": fallback_claim_ratio,
        "threshold_hit_rate": _safe_rate(threshold_hits, threshold_considered),
        "traceability_complete_citation_count": traceability_complete_count,
        "traceability_partial_citation_count": traceability_partial_count,
        "traceability_missing_citation_count": traceability_missing_count,
        "traceability_gap_citation_count": traceability_gap_count,
        "traceability_gap_rate": _safe_rate(traceability_gap_count, claim_count),
        "retrieval_hits_count": int(retrieval_summary.get("hits_count") or 0) if isinstance(retrieval_summary, dict) else 0,
        "retrieval_expected": bool(architect_rag_enabled),
    }


def _build_preflight_grounding_policy(
    *,
    coverage_rate: Optional[float],
    depth_coverage_rate: Optional[float],
    namespace_empty: bool,
    inventory_total_uploads: int,
    missing_doc_families: list[str],
    depth_gap_doc_families: list[str],
    architect_claims: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    mode = _configured_preflight_grounding_policy_mode()
    thresholds = _preflight_grounding_policy_thresholds()
    high_risk_coverage_threshold = float(thresholds["high_risk_coverage_threshold"])
    medium_risk_coverage_threshold = float(thresholds["medium_risk_coverage_threshold"])
    high_risk_depth_coverage_threshold = float(thresholds["high_risk_depth_coverage_threshold"])
    medium_risk_depth_coverage_threshold = float(thresholds["medium_risk_depth_coverage_threshold"])
    min_uploads = int(thresholds["min_uploads"])
    min_key_claim_coverage_rate = float(thresholds["min_key_claim_coverage_rate"])
    max_fallback_claim_ratio = float(thresholds["max_fallback_claim_ratio"])
    max_traceability_gap_rate = float(thresholds["max_traceability_gap_rate"])
    min_threshold_hit_rate = float(thresholds["min_threshold_hit_rate"])
    reasons: list[str] = []
    risk_level = "low"

    if namespace_empty:
        reasons.append("namespace_empty")
        risk_level = "high"

    if coverage_rate is not None:
        if coverage_rate < high_risk_coverage_threshold:
            reasons.append("coverage_below_high_threshold")
            risk_level = "high"
        elif coverage_rate < medium_risk_coverage_threshold and risk_level != "high":
            reasons.append("coverage_below_medium_threshold")
            risk_level = "medium"

    if depth_coverage_rate is not None:
        if depth_coverage_rate < high_risk_depth_coverage_threshold:
            reasons.append("depth_coverage_below_high_threshold")
            risk_level = "high"
        elif depth_coverage_rate < medium_risk_depth_coverage_threshold and risk_level != "high":
            reasons.append("depth_coverage_below_medium_threshold")
            risk_level = "medium"

    if inventory_total_uploads > 0 and inventory_total_uploads < min_uploads and risk_level == "low":
        reasons.append("few_uploaded_documents")
        risk_level = "medium"

    if missing_doc_families and risk_level == "low":
        reasons.append("recommended_doc_families_missing")
        risk_level = "medium"
    if depth_gap_doc_families and risk_level == "low":
        reasons.append("recommended_doc_families_depth_gap")
        risk_level = "medium"

    architect_claims_payload = architect_claims if isinstance(architect_claims, dict) else {}
    architect_claims_available = bool(architect_claims_payload.get("available"))
    if architect_claims_available:
        claim_citation_count = int(architect_claims_payload.get("claim_citation_count") or 0)
        key_claim_coverage_ratio = architect_claims_payload.get("key_claim_coverage_ratio")
        fallback_claim_ratio = architect_claims_payload.get("fallback_claim_ratio")
        traceability_gap_rate = architect_claims_payload.get("traceability_gap_rate")
        threshold_hit_rate = architect_claims_payload.get("threshold_hit_rate")

        if claim_citation_count <= 0:
            reasons.append("architect_claim_citations_unavailable")
            risk_level = "high"
        try:
            key_claim_coverage_value = float(key_claim_coverage_ratio) if key_claim_coverage_ratio is not None else None
        except (TypeError, ValueError):
            key_claim_coverage_value = None
        if key_claim_coverage_value is None:
            reasons.append("architect_key_claim_coverage_unavailable")
            risk_level = "high"
        elif key_claim_coverage_value < min_key_claim_coverage_rate:
            reasons.append("architect_key_claim_coverage_below_min")
            risk_level = "high"

        try:
            fallback_claim_ratio_value = float(fallback_claim_ratio) if fallback_claim_ratio is not None else None
        except (TypeError, ValueError):
            fallback_claim_ratio_value = None
        if fallback_claim_ratio_value is None:
            reasons.append("architect_fallback_claim_ratio_unavailable")
            risk_level = "high"
        elif fallback_claim_ratio_value > max_fallback_claim_ratio:
            reasons.append("architect_fallback_claim_ratio_above_max")
            risk_level = "high"

        try:
            traceability_gap_rate_value = float(traceability_gap_rate) if traceability_gap_rate is not None else None
        except (TypeError, ValueError):
            traceability_gap_rate_value = None
        if traceability_gap_rate_value is None:
            reasons.append("architect_traceability_gap_rate_unavailable")
            risk_level = "high"
        elif traceability_gap_rate_value > max_traceability_gap_rate:
            reasons.append("architect_traceability_gap_rate_above_max")
            risk_level = "high"

        try:
            threshold_hit_rate_value = float(threshold_hit_rate) if threshold_hit_rate is not None else None
        except (TypeError, ValueError):
            threshold_hit_rate_value = None
        if threshold_hit_rate_value is None:
            reasons.append("architect_threshold_hit_rate_unavailable")
            risk_level = "high"
        elif threshold_hit_rate_value < min_threshold_hit_rate:
            reasons.append("architect_threshold_hit_rate_below_min")
            risk_level = "high"
    elif architect_claims_payload:
        reason = str(architect_claims_payload.get("reason") or "").strip().lower()
        if reason in {"input_context_missing", "estimation_error", "namespace_missing"} and risk_level == "low":
            reasons.append("architect_claim_policy_not_evaluated")
            risk_level = "medium"

    reasons = list(dict.fromkeys(reasons))
    if not reasons:
        reasons = ["grounding_signals_ok"]

    blocking = mode == "strict" and risk_level == "high"
    if risk_level == "high":
        summary = "grounding_signals_high_risk"
    elif risk_level == "medium":
        summary = "grounding_signals_partial"
    else:
        summary = "grounding_signals_ok"

    return {
        "mode": mode,
        "risk_level": risk_level,
        "reasons": reasons,
        "summary": summary,
        "blocking": blocking,
        "go_ahead": not blocking,
        "thresholds": thresholds,
        "architect_claims": architect_claims_payload if architect_claims_payload else None,
    }


def _build_generate_preflight(
    *,
    donor_id: str,
    strategy: Any,
    client_metadata: Optional[Dict[str, Any]],
    tenant_id: Optional[str] = None,
    architect_rag_enabled: bool = True,
) -> Dict[str, Any]:
    metadata = client_metadata if isinstance(client_metadata, dict) else {}
    input_context = _preflight_input_context(client_metadata)
    resolved_tenant_id = _normalize_tenant_candidate(tenant_id) or _normalize_tenant_candidate(
        metadata.get("tenant_id") or metadata.get("tenant")
    )
    base_namespace = str(getattr(strategy, "get_rag_collection", lambda: "")() or "").strip() or None
    namespace = _tenant_rag_namespace(base_namespace or "", resolved_tenant_id) if base_namespace else None
    namespace_normalized = vector_store.normalize_namespace(namespace or "")
    inventory_rows = _ingest_inventory(donor_id=donor_id or None, tenant_id=resolved_tenant_id)
    inventory_payload = public_ingest_inventory_payload(
        inventory_rows,
        donor_id=donor_id or None,
        tenant_id=resolved_tenant_id,
    )
    doc_family_counts_raw = inventory_payload.get("doc_family_counts")
    doc_family_counts = doc_family_counts_raw if isinstance(doc_family_counts_raw, dict) else {}
    inventory_total_uploads = int(inventory_payload.get("total_uploads") or 0)

    expected_doc_families = _preflight_expected_doc_families(donor_id=donor_id, client_metadata=client_metadata)
    doc_family_min_uploads = _preflight_doc_family_min_uploads_map(
        expected_doc_families=expected_doc_families,
        client_metadata=client_metadata,
    )
    present_doc_families = [doc for doc in expected_doc_families if int(doc_family_counts.get(doc) or 0) > 0]
    missing_doc_families = [doc for doc in expected_doc_families if int(doc_family_counts.get(doc) or 0) <= 0]
    depth_profile = _preflight_doc_family_depth_profile(
        expected_doc_families=expected_doc_families,
        doc_family_counts=doc_family_counts,
        min_uploads_by_family=doc_family_min_uploads,
    )
    depth_ready_doc_families = list(depth_profile.get("depth_ready_doc_families") or [])
    depth_gap_doc_families = list(depth_profile.get("depth_gap_doc_families") or [])
    depth_ready_count = int(depth_profile.get("depth_ready_count") or 0)
    depth_gap_count = int(depth_profile.get("depth_gap_count") or 0)
    depth_coverage_rate = depth_profile.get("depth_coverage_rate")
    try:
        depth_coverage_rate = float(depth_coverage_rate) if depth_coverage_rate is not None else None
    except (TypeError, ValueError):
        depth_coverage_rate = None
    expected_count = len(expected_doc_families)
    loaded_count = len(present_doc_families)
    coverage_rate = round(loaded_count / expected_count, 4) if expected_count else None
    architect_claims = _estimate_preflight_architect_claims(
        donor_id=donor_id,
        strategy=strategy,
        namespace=namespace or "",
        input_context=input_context,
        tenant_id=resolved_tenant_id,
        architect_rag_enabled=bool(architect_rag_enabled),
    )

    warnings: list[Dict[str, Any]] = []
    namespace_empty = inventory_total_uploads <= 0
    if namespace_empty:
        warnings.append(
            {
                "code": "NAMESPACE_EMPTY",
                "severity": "high",
                "message": "No donor documents are uploaded to the retrieval namespace.",
            }
        )
    if coverage_rate is not None and coverage_rate < 0.5:
        warnings.append(
            {
                "code": "LOW_DOC_COVERAGE",
                "severity": "high" if loaded_count == 0 else "medium",
                "message": f"Recommended document-family coverage is low ({loaded_count}/{expected_count}).",
            }
        )
    if depth_coverage_rate is not None and depth_coverage_rate < 0.5:
        warnings.append(
            {
                "code": "LOW_DOC_DEPTH_COVERAGE",
                "severity": "high" if depth_ready_count == 0 else "medium",
                "message": (
                    "Document-family depth coverage is low "
                    f"({depth_ready_count}/{expected_count} families meet minimum uploads)."
                ),
            }
        )
    if inventory_total_uploads > 0 and inventory_total_uploads < 3:
        warnings.append(
            {
                "code": "LOW_ABSOLUTE_UPLOAD_COUNT",
                "severity": "low",
                "message": "Only a few documents are uploaded; grounding quality may be unstable.",
            }
        )
    risk_level = _preflight_severity_max([str(row.get("severity") or "low") for row in warnings])
    grounding_policy = _build_preflight_grounding_policy(
        coverage_rate=coverage_rate,
        depth_coverage_rate=depth_coverage_rate,
        namespace_empty=namespace_empty,
        inventory_total_uploads=inventory_total_uploads,
        missing_doc_families=missing_doc_families,
        depth_gap_doc_families=depth_gap_doc_families,
        architect_claims=architect_claims,
    )
    grounding_risk_level = str(grounding_policy.get("risk_level") or "low")
    blocking = bool(grounding_policy.get("blocking"))
    return {
        "donor_id": donor_id,
        "tenant_id": resolved_tenant_id,
        "retrieval_namespace": namespace,
        "retrieval_namespace_normalized": namespace_normalized,
        "retrieval_query_terms": donor_query_preset_list(donor_id),
        "expected_doc_families": expected_doc_families,
        "present_doc_families": present_doc_families,
        "missing_doc_families": missing_doc_families,
        "doc_family_min_uploads": doc_family_min_uploads,
        "depth_ready_doc_families": depth_ready_doc_families,
        "depth_gap_doc_families": depth_gap_doc_families,
        "expected_count": expected_count,
        "loaded_count": loaded_count,
        "coverage_rate": coverage_rate,
        "depth_ready_count": depth_ready_count,
        "depth_gap_count": depth_gap_count,
        "depth_coverage_rate": depth_coverage_rate,
        "inventory_total_uploads": inventory_total_uploads,
        "inventory_family_count": int(inventory_payload.get("family_count") or 0),
        "namespace_empty": namespace_empty,
        "warning_count": len(warnings),
        "warning_level": risk_level,
        "risk_level": risk_level,
        "grounding_risk_level": grounding_risk_level,
        "architect_rag_enabled": bool(architect_rag_enabled),
        "grounding_policy": grounding_policy,
        "architect_claims": architect_claims,
        "go_ahead": risk_level != "high" and not blocking,
        "warnings": warnings,
    }
