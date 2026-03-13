from __future__ import annotations

import gzip
import io
import json
import os
import uuid
import zipfile
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Literal, Optional

from fastapi import BackgroundTasks, FastAPI, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict

from grantflow.api.public_views import (
    REVIEW_WORKFLOW_OVERDUE_DEFAULT_HOURS,
    REVIEW_WORKFLOW_STATE_FILTER_VALUES,
    public_checkpoint_payload,
    public_ingest_inventory_csv_text,
    public_ingest_inventory_payload,
    public_ingest_recent_payload,
    public_job_citations_payload,
    public_job_comments_payload,
    public_job_critic_payload,
    public_job_diff_payload,
    public_job_events_payload,
    public_job_export_payload,
    public_job_metrics_payload,
    public_job_payload,
    public_job_quality_payload,
    public_job_review_workflow_csv_text,
    public_job_review_workflow_payload,
    public_job_review_workflow_sla_payload,
    public_job_versions_payload,
    public_portfolio_metrics_csv_text,
    public_portfolio_metrics_payload,
    public_portfolio_quality_csv_text,
    public_portfolio_quality_payload,
)
from grantflow.api.routers.health import configure_health_router, router as health_router
from grantflow.api.routers.ingest import configure_ingest_router, router as ingest_router
from grantflow.api.routers.status_read import configure_status_read_router, router as status_read_router
from grantflow.api.routers.review_workflow_read import (
    configure_review_workflow_read_router,
    router as review_workflow_read_router,
)
from grantflow.api.routers.comments_write import (
    configure_comments_write_router,
    router as comments_write_router,
)
from grantflow.api.routers.critic_write import (
    configure_critic_write_router,
    router as critic_write_router,
)
from grantflow.api.routers.portfolio_read import (
    configure_portfolio_read_router,
    router as portfolio_read_router,
)
from grantflow.api.routers.hitl import configure_hitl_router, router as hitl_router
from grantflow.api.routers.status_comments_read import (
    configure_status_comments_read_router,
    router as status_comments_read_router,
)
from grantflow.api.routers.system_misc import router as system_misc_router
from grantflow.api.schemas import (
    JobCitationsPublicResponse,
    JobCriticPublicResponse,
    JobDiffPublicResponse,
    JobEventsPublicResponse,
    JobExportPayloadPublicResponse,
    JobMetricsPublicResponse,
    JobQualitySummaryPublicResponse,
    JobReviewWorkflowSLARecomputePublicResponse,
    JobStatusPublicResponse,
    JobVersionsPublicResponse,
)
from grantflow.api.security import (
    api_key_configured,
    assert_production_auth_config,
    install_openapi_api_key_security,
    read_auth_required,
    require_api_key_if_configured,
)
from grantflow.api.webhooks import send_job_webhook_event
from grantflow.core.config import config
from grantflow.core.stores import create_ingest_audit_store_from_env, create_job_store_from_env
from grantflow.core.strategies.factory import DonorFactory
from grantflow.core.version import __version__
from grantflow.exporters.excel_builder import build_xlsx_from_logframe
from grantflow.exporters.word_builder import build_docx_from_toc
from grantflow.memory_bank.ingest import ingest_pdf_to_namespace
from grantflow.memory_bank.vector_store import vector_store
from grantflow.swarm.findings import bind_findings_to_latest_versions, finding_primary_id, normalize_findings
from grantflow.swarm.graph import grantflow_graph
from grantflow.swarm.hitl import HITLStatus, hitl_manager
from grantflow.swarm.retrieval_query import donor_query_preset_terms
from grantflow.swarm.citations import citation_traceability_status
from grantflow.swarm.state_contract import normalize_state_contract, state_donor_id

app = FastAPI(
    title="GrantFlow API",
    description="Enterprise-grade grant proposal automation",
    version=__version__,
)
assert_production_auth_config()

JOB_STORE = create_job_store_from_env()
INGEST_AUDIT_STORE = create_ingest_audit_store_from_env()

HITLStartAt = Literal["start", "architect", "mel", "critic"]
TERMINAL_JOB_STATUSES = {"done", "error", "canceled"}
REVIEW_COMMENT_SECTIONS = {"toc", "logframe", "general"}
CRITIC_FINDING_STATUSES = {"open", "acknowledged", "resolved"}
CRITIC_FINDING_SLA_HOURS = {"high": 24, "medium": 72, "low": 120}
REVIEW_COMMENT_DEFAULT_SLA_HOURS = 72
STATUS_WEBHOOK_EVENTS = {
    "running": "job.started",
    "pending_hitl": "job.pending_hitl",
    "done": "job.completed",
    "error": "job.failed",
    "canceled": "job.canceled",
}
RUNTIME_PIPELINE_STATE_KEYS = {
    "_start_at",
    "hitl_checkpoint_stage",
    "hitl_resume_from",
    "hitl_checkpoint_id",
}
GENERATE_PREFLIGHT_DEFAULT_DOC_FAMILIES: dict[str, list[str]] = {
    "usaid": ["donor_policy", "responsible_ai_guidance", "country_context"],
    "eu": ["donor_results_guidance", "digital_governance_guidance", "country_context"],
    "worldbank": ["donor_results_guidance", "project_reference_docs", "country_context"],
    "giz": ["donor_policy", "country_context", "implementation_reference"],
    "state_department": ["donor_policy", "country_context", "risk_context"],
    "us_state_department": ["donor_policy", "country_context", "risk_context"],
}
GROUNDING_POLICY_MODES = {"off", "warn", "strict"}
TENANT_HEADER = "x-tenant-id"


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_iso_utc(value: Any) -> Optional[datetime]:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _iso_plus_hours(base_ts: Optional[str], hours: int) -> str:
    base_dt = _parse_iso_utc(base_ts) or datetime.now(timezone.utc)
    return (base_dt + timedelta(hours=max(1, int(hours)))).isoformat()


def _finding_sla_hours(severity: Any, *, finding_sla_hours_override: Optional[Dict[str, int]] = None) -> int:
    token = str(severity or "").strip().lower()
    source = finding_sla_hours_override if isinstance(finding_sla_hours_override, dict) else CRITIC_FINDING_SLA_HOURS
    return int(source.get(token, source.get("medium", CRITIC_FINDING_SLA_HOURS["medium"])))


def _comment_sla_hours(
    *,
    linked_finding_severity: Optional[str] = None,
    finding_sla_hours_override: Optional[Dict[str, int]] = None,
    default_comment_sla_hours: Optional[int] = None,
) -> int:
    if linked_finding_severity:
        return _finding_sla_hours(linked_finding_severity, finding_sla_hours_override=finding_sla_hours_override)
    if isinstance(default_comment_sla_hours, int) and default_comment_sla_hours > 0:
        return int(default_comment_sla_hours)
    return int(REVIEW_COMMENT_DEFAULT_SLA_HOURS)


def _finding_actor_from_request(request: Request) -> str:
    for header in ("x-reviewer", "x-actor", "x-user", "x-user-id", "x-email"):
        value = str(request.headers.get(header) or "").strip()
        if value:
            return value[:120]
    return "api_user"


def _append_job_event_records(
    previous: Optional[Dict[str, Any]],
    next_payload: Dict[str, Any],
) -> Dict[str, Any]:
    events = []
    raw_previous_events = (previous or {}).get("job_events")
    if isinstance(raw_previous_events, list):
        events = [e for e in raw_previous_events if isinstance(e, dict)]

    # Preserve explicitly supplied events (used by manual event appends).
    if isinstance(next_payload.get("job_events"), list):
        events = [e for e in next_payload["job_events"] if isinstance(e, dict)]

    prev_status = (previous or {}).get("status")
    next_status = next_payload.get("status")
    if prev_status != next_status and next_status is not None:
        events = list(events)
        events.append(
            {
                "event_id": str(uuid.uuid4()),
                "ts": _utcnow_iso(),
                "type": "status_changed",
                "from_status": None if prev_status is None else str(prev_status),
                "to_status": str(next_status),
                "status": str(next_status),
            }
        )

    if events:
        next_payload["job_events"] = events[-200:]
    return next_payload


def _record_job_event(job_id: str, event_type: str, **fields: Any) -> None:
    job = JOB_STORE.get(job_id)
    if not job:
        return
    existing = job.get("job_events")
    events = [e for e in existing if isinstance(e, dict)] if isinstance(existing, list) else []
    event: Dict[str, Any] = {
        "event_id": str(uuid.uuid4()),
        "ts": _utcnow_iso(),
        "type": event_type,
        "status": str(job.get("status") or ""),
    }
    for key, value in fields.items():
        event[str(key)] = value
    events.append(event)
    JOB_STORE.update(job_id, job_events=events[-200:])


def _record_ingest_event(
    *,
    donor_id: str,
    namespace: str,
    filename: str,
    content_type: str,
    metadata: Optional[Dict[str, Any]] = None,
    result: Optional[Dict[str, Any]] = None,
) -> None:
    row: Dict[str, Any] = {
        "event_id": str(uuid.uuid4()),
        "ts": _utcnow_iso(),
        "donor_id": str(donor_id or ""),
        "namespace": str(namespace or ""),
        "filename": str(filename or ""),
        "content_type": str(content_type or ""),
        "metadata": dict(metadata or {}),
        "result": dict(result or {}),
    }
    INGEST_AUDIT_STORE.append(row)


def _tenant_authz_enabled() -> bool:
    return os.getenv("GRANTFLOW_TENANT_AUTHZ_ENABLED", "false").strip().lower() == "true"


def _allowed_tenant_tokens() -> set[str]:
    raw = os.getenv("GRANTFLOW_ALLOWED_TENANTS", os.getenv("AIDGRAPH_ALLOWED_TENANTS", ""))
    tokens = [part.strip() for part in str(raw or "").split(",") if part.strip()]
    return {vector_store.normalize_namespace(token) for token in tokens if token}


def _default_tenant_token() -> Optional[str]:
    token = str(os.getenv("GRANTFLOW_DEFAULT_TENANT", os.getenv("AIDGRAPH_DEFAULT_TENANT", "")) or "").strip()
    if not token:
        return None
    return vector_store.normalize_namespace(token)


def _normalize_tenant_candidate(value: Any) -> Optional[str]:
    token = str(value or "").strip()
    if not token:
        return None
    return vector_store.normalize_namespace(token)


def _resolve_tenant_id(
    request: Request,
    *,
    explicit_tenant: Optional[str] = None,
    client_metadata: Optional[Dict[str, Any]] = None,
    require_if_enabled: bool = True,
) -> Optional[str]:
    metadata = client_metadata if isinstance(client_metadata, dict) else {}
    candidate = (
        _normalize_tenant_candidate(explicit_tenant)
        or _normalize_tenant_candidate(request.headers.get(TENANT_HEADER))
        or _normalize_tenant_candidate(metadata.get("tenant_id"))
        or _normalize_tenant_candidate(metadata.get("tenant"))
        or _default_tenant_token()
    )
    allowed = _allowed_tenant_tokens()
    enforce = _tenant_authz_enabled()
    if require_if_enabled and enforce and not candidate:
        raise HTTPException(status_code=403, detail="tenant_id is required when tenant authz is enabled")
    if candidate and allowed and candidate not in allowed:
        raise HTTPException(status_code=403, detail="tenant_id is not allowed for this server")
    return candidate


def _tenant_rag_namespace(base_namespace: str, tenant_id: Optional[str]) -> str:
    base = str(base_namespace or "").strip() or "default"
    tenant = str(tenant_id or "").strip()
    if not tenant:
        return base
    return f"{tenant}/{base}"


def _list_ingest_events(
    *,
    donor_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
    limit: int = 50,
) -> list[Dict[str, Any]]:
    return INGEST_AUDIT_STORE.list_recent(donor_id=donor_id, tenant_id=tenant_id, limit=limit)


def _ingest_inventory(*, donor_id: Optional[str] = None, tenant_id: Optional[str] = None) -> list[Dict[str, Any]]:
    inventory_fn = getattr(INGEST_AUDIT_STORE, "inventory", None)
    if callable(inventory_fn):
        rows = inventory_fn(donor_id=donor_id, tenant_id=tenant_id)
        return rows if isinstance(rows, list) else []
    # Fallback for older store implementations.
    rows = _list_ingest_events(donor_id=donor_id, tenant_id=tenant_id, limit=200)
    grouped: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        raw_metadata = row.get("metadata")
        metadata: Dict[str, Any] = raw_metadata if isinstance(raw_metadata, dict) else {}
        doc_family = str((metadata or {}).get("doc_family") or "").strip()
        donor = str(row.get("donor_id") or "").strip()
        tenant = str((metadata or {}).get("tenant_id") or "").strip()
        if not doc_family:
            continue
        key = f"{tenant.lower()}::{donor.lower()}::{doc_family}"
        current = grouped.get(key)
        if current is None:
            grouped[key] = {
                "tenant_id": tenant or None,
                "donor_id": donor,
                "doc_family": doc_family,
                "count": 1,
                "latest_ts": row.get("ts"),
                "latest_filename": row.get("filename"),
                "latest_event_id": row.get("event_id"),
                "latest_source_type": metadata.get("source_type"),
            }
        else:
            current["count"] = int(current.get("count") or 0) + 1
    return list(grouped.values())


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


def _configured_mel_grounding_policy_mode() -> str:
    mel_mode = getattr(config.graph, "mel_grounding_policy_mode", None)
    if str(mel_mode or "").strip():
        return _normalize_grounding_policy_mode(mel_mode)
    return _configured_preflight_grounding_policy_mode()


def _mel_grounding_policy_thresholds() -> Dict[str, Any]:
    min_mel_citations_raw = getattr(config.graph, "mel_grounding_min_mel_citations", 2)
    min_claim_support_rate_raw = getattr(config.graph, "mel_grounding_min_claim_support_rate", 0.5)
    min_traceability_complete_rate_raw = getattr(config.graph, "mel_grounding_min_traceability_complete_rate", 0.5)
    max_traceability_gap_rate_raw = getattr(config.graph, "mel_grounding_max_traceability_gap_rate", 0.5)

    try:
        min_mel_citations = int(min_mel_citations_raw)
    except (TypeError, ValueError):
        min_mel_citations = 2
    try:
        min_claim_support_rate = float(min_claim_support_rate_raw)
    except (TypeError, ValueError):
        min_claim_support_rate = 0.5
    try:
        min_traceability_complete_rate = float(min_traceability_complete_rate_raw)
    except (TypeError, ValueError):
        min_traceability_complete_rate = 0.5
    try:
        max_traceability_gap_rate = float(max_traceability_gap_rate_raw)
    except (TypeError, ValueError):
        max_traceability_gap_rate = 0.5

    min_mel_citations = max(1, min(min_mel_citations, 1000))
    min_claim_support_rate = max(0.0, min(min_claim_support_rate, 1.0))
    min_traceability_complete_rate = max(0.0, min(min_traceability_complete_rate, 1.0))
    max_traceability_gap_rate = max(0.0, min(max_traceability_gap_rate, 1.0))
    return {
        "min_mel_citations": min_mel_citations,
        "min_claim_support_rate": round(min_claim_support_rate, 4),
        "min_traceability_complete_rate": round(min_traceability_complete_rate, 4),
        "max_traceability_gap_rate": round(max_traceability_gap_rate, 4),
    }


def _evaluate_mel_grounding_policy_from_state(state: Any) -> Dict[str, Any]:
    mode = _configured_mel_grounding_policy_mode()
    thresholds = _mel_grounding_policy_thresholds()
    min_mel_citations = int(thresholds["min_mel_citations"])
    min_claim_support_rate = float(thresholds["min_claim_support_rate"])
    min_traceability_complete_rate = float(thresholds["min_traceability_complete_rate"])
    max_traceability_gap_rate = float(thresholds["max_traceability_gap_rate"])

    state_dict = state if isinstance(state, dict) else {}
    raw_citations = state_dict.get("citations")
    citations = [c for c in raw_citations if isinstance(c, dict)] if isinstance(raw_citations, list) else []
    mel_citations = [c for c in citations if str(c.get("stage") or "") == "mel"]
    mel_traceability_statuses = [citation_traceability_status(c) for c in mel_citations]

    claim_support_types = {"rag_result", "rag_support", "rag_claim_support"}
    mel_claim_support_count = sum(1 for c in mel_citations if str(c.get("citation_type") or "") in claim_support_types)
    mel_fallback_count = sum(1 for c in mel_citations if str(c.get("citation_type") or "") == "fallback_namespace")
    mel_citation_count = len(mel_citations)
    mel_claim_support_rate = round(mel_claim_support_count / mel_citation_count, 4) if mel_citation_count else None
    mel_traceability_complete_count = sum(1 for status in mel_traceability_statuses if status == "complete")
    mel_traceability_partial_count = sum(1 for status in mel_traceability_statuses if status == "partial")
    mel_traceability_missing_count = sum(1 for status in mel_traceability_statuses if status == "missing")
    mel_traceability_gap_count = mel_traceability_partial_count + mel_traceability_missing_count
    mel_traceability_complete_rate = (
        round(mel_traceability_complete_count / mel_citation_count, 4) if mel_citation_count else None
    )
    mel_traceability_gap_rate = (
        round(mel_traceability_gap_count / mel_citation_count, 4) if mel_citation_count else None
    )

    reasons: list[str] = []
    risk_level = "low"
    if mel_citation_count == 0:
        reasons.append("no_mel_citations")
        risk_level = "high"
    elif mel_citation_count < min_mel_citations:
        reasons.append("mel_citations_below_min")
        risk_level = "medium"

    if mel_claim_support_rate is None:
        reasons.append("mel_claim_support_rate_unavailable")
        risk_level = "high"
    elif mel_claim_support_rate < min_claim_support_rate:
        reasons.append("mel_claim_support_rate_below_min")
        risk_level = "high"

    if mel_traceability_complete_rate is None:
        reasons.append("mel_traceability_rate_unavailable")
        risk_level = "high"
    elif mel_traceability_complete_rate < min_traceability_complete_rate:
        reasons.append("mel_traceability_complete_rate_below_min")
        risk_level = "high"

    if mel_traceability_gap_rate is None:
        reasons.append("mel_traceability_gap_rate_unavailable")
        risk_level = "high"
    elif mel_traceability_gap_rate > max_traceability_gap_rate:
        reasons.append("mel_traceability_gap_rate_above_max")
        risk_level = "high"

    if mode == "off":
        reasons = []
        risk_level = "low"
        passed = True
        blocking = False
        summary = "policy_off"
    else:
        passed = not reasons
        blocking = mode == "strict" and not passed
        summary = "mel_grounding_signals_ok" if passed else ",".join(reasons)

    return {
        "mode": mode,
        "thresholds": thresholds,
        "mel_citation_count": mel_citation_count,
        "mel_claim_support_citation_count": mel_claim_support_count,
        "mel_fallback_namespace_citation_count": mel_fallback_count,
        "mel_claim_support_rate": mel_claim_support_rate,
        "mel_traceability_complete_citation_count": mel_traceability_complete_count,
        "mel_traceability_partial_citation_count": mel_traceability_partial_count,
        "mel_traceability_missing_citation_count": mel_traceability_missing_count,
        "mel_traceability_gap_citation_count": mel_traceability_gap_count,
        "mel_traceability_complete_rate": mel_traceability_complete_rate,
        "mel_traceability_gap_rate": mel_traceability_gap_rate,
        "risk_level": risk_level,
        "passed": passed,
        "blocking": blocking,
        "go_ahead": not blocking,
        "summary": summary,
        "reasons": reasons,
    }


def _configured_export_grounding_policy_mode() -> str:
    export_mode = getattr(config.graph, "export_grounding_policy_mode", None)
    if str(export_mode or "").strip():
        return _normalize_grounding_policy_mode(export_mode)
    return _configured_preflight_grounding_policy_mode()


def _export_grounding_policy_thresholds() -> Dict[str, Any]:
    min_architect_citations_raw = getattr(config.graph, "export_grounding_min_architect_citations", 3)
    min_claim_support_rate_raw = getattr(config.graph, "export_grounding_min_claim_support_rate", 0.5)
    min_traceability_complete_rate_raw = getattr(
        config.graph,
        "export_grounding_min_traceability_complete_rate",
        0.5,
    )
    max_traceability_gap_rate_raw = getattr(config.graph, "export_grounding_max_traceability_gap_rate", 0.5)

    try:
        min_architect_citations = int(min_architect_citations_raw)
    except (TypeError, ValueError):
        min_architect_citations = 3
    try:
        min_claim_support_rate = float(min_claim_support_rate_raw)
    except (TypeError, ValueError):
        min_claim_support_rate = 0.5
    try:
        min_traceability_complete_rate = float(min_traceability_complete_rate_raw)
    except (TypeError, ValueError):
        min_traceability_complete_rate = 0.5
    try:
        max_traceability_gap_rate = float(max_traceability_gap_rate_raw)
    except (TypeError, ValueError):
        max_traceability_gap_rate = 0.5

    min_architect_citations = max(1, min(min_architect_citations, 1000))
    min_claim_support_rate = max(0.0, min(min_claim_support_rate, 1.0))
    min_traceability_complete_rate = max(0.0, min(min_traceability_complete_rate, 1.0))
    max_traceability_gap_rate = max(0.0, min(max_traceability_gap_rate, 1.0))

    return {
        "min_architect_citations": min_architect_citations,
        "min_claim_support_rate": round(min_claim_support_rate, 4),
        "min_traceability_complete_rate": round(min_traceability_complete_rate, 4),
        "max_traceability_gap_rate": round(max_traceability_gap_rate, 4),
    }


def _evaluate_export_grounding_policy(citations: list[dict[str, Any]]) -> Dict[str, Any]:
    mode = _configured_export_grounding_policy_mode()
    thresholds = _export_grounding_policy_thresholds()
    min_architect_citations = int(thresholds["min_architect_citations"])
    min_claim_support_rate = float(thresholds["min_claim_support_rate"])
    min_traceability_complete_rate = float(thresholds["min_traceability_complete_rate"])
    max_traceability_gap_rate = float(thresholds["max_traceability_gap_rate"])

    architect_citations = [c for c in citations if isinstance(c, dict) and str(c.get("stage") or "") == "architect"]
    architect_traceability_statuses = [citation_traceability_status(c) for c in architect_citations]
    architect_citation_count = len(architect_citations)
    architect_claim_support_count = sum(
        1 for c in architect_citations if str(c.get("citation_type") or "") == "rag_claim_support"
    )
    architect_fallback_count = sum(
        1 for c in architect_citations if str(c.get("citation_type") or "") == "fallback_namespace"
    )
    architect_claim_support_rate = (
        round(architect_claim_support_count / architect_citation_count, 4) if architect_citation_count else None
    )
    architect_traceability_complete_count = sum(1 for status in architect_traceability_statuses if status == "complete")
    architect_traceability_partial_count = sum(1 for status in architect_traceability_statuses if status == "partial")
    architect_traceability_missing_count = sum(1 for status in architect_traceability_statuses if status == "missing")
    architect_traceability_gap_count = architect_traceability_partial_count + architect_traceability_missing_count
    architect_traceability_complete_rate = (
        round(architect_traceability_complete_count / architect_citation_count, 4) if architect_citation_count else None
    )
    architect_traceability_gap_rate = (
        round(architect_traceability_gap_count / architect_citation_count, 4) if architect_citation_count else None
    )

    reasons: list[str] = []
    risk_level = "low"
    if architect_citation_count == 0:
        reasons.append("no_architect_citations")
        risk_level = "high"
    elif architect_citation_count < min_architect_citations:
        reasons.append("architect_citations_below_min")
        risk_level = "medium"

    if architect_claim_support_rate is None:
        reasons.append("claim_support_rate_unavailable")
        risk_level = "high"
    elif architect_claim_support_rate < min_claim_support_rate:
        reasons.append("claim_support_rate_below_min")
        risk_level = "high"

    if architect_traceability_complete_rate is None:
        reasons.append("traceability_rate_unavailable")
        risk_level = "high"
    elif architect_traceability_complete_rate < min_traceability_complete_rate:
        reasons.append("traceability_complete_rate_below_min")
        risk_level = "high"

    if architect_traceability_gap_rate is None:
        reasons.append("traceability_gap_rate_unavailable")
        risk_level = "high"
    elif architect_traceability_gap_rate > max_traceability_gap_rate:
        reasons.append("traceability_gap_rate_above_max")
        risk_level = "high"

    passed = not reasons
    blocking = mode == "strict" and not passed
    summary = "export_grounding_signals_ok" if passed else ",".join(reasons)
    return {
        "mode": mode,
        "thresholds": thresholds,
        "architect_citation_count": architect_citation_count,
        "architect_claim_support_citation_count": architect_claim_support_count,
        "architect_fallback_namespace_citation_count": architect_fallback_count,
        "architect_claim_support_rate": architect_claim_support_rate,
        "architect_traceability_complete_citation_count": architect_traceability_complete_count,
        "architect_traceability_partial_citation_count": architect_traceability_partial_count,
        "architect_traceability_missing_citation_count": architect_traceability_missing_count,
        "architect_traceability_gap_citation_count": architect_traceability_gap_count,
        "architect_traceability_complete_rate": architect_traceability_complete_rate,
        "architect_traceability_gap_rate": architect_traceability_gap_rate,
        "risk_level": risk_level,
        "passed": passed,
        "blocking": blocking,
        "go_ahead": not blocking,
        "summary": summary,
        "reasons": reasons,
    }


def _preflight_grounding_policy_thresholds() -> Dict[str, Any]:
    high_cov_raw = getattr(config.graph, "preflight_grounding_high_risk_coverage_threshold", 0.5)
    medium_cov_raw = getattr(config.graph, "preflight_grounding_medium_risk_coverage_threshold", 0.8)
    min_uploads_raw = getattr(config.graph, "preflight_grounding_min_uploads", 3)

    try:
        high_cov = float(high_cov_raw)
    except (TypeError, ValueError):
        high_cov = 0.5
    try:
        medium_cov = float(medium_cov_raw)
    except (TypeError, ValueError):
        medium_cov = 0.8
    try:
        min_uploads = int(min_uploads_raw)
    except (TypeError, ValueError):
        min_uploads = 3

    high_cov = max(0.0, min(high_cov, 1.0))
    medium_cov = max(0.0, min(medium_cov, 1.0))
    if medium_cov < high_cov:
        medium_cov = high_cov
    min_uploads = max(1, min_uploads)

    return {
        "high_risk_coverage_threshold": round(high_cov, 4),
        "medium_risk_coverage_threshold": round(medium_cov, 4),
        "min_uploads": min_uploads,
    }


def _build_preflight_grounding_policy(
    *,
    coverage_rate: Optional[float],
    namespace_empty: bool,
    inventory_total_uploads: int,
    missing_doc_families: list[str],
) -> Dict[str, Any]:
    mode = _configured_preflight_grounding_policy_mode()
    thresholds = _preflight_grounding_policy_thresholds()
    high_risk_coverage_threshold = float(thresholds["high_risk_coverage_threshold"])
    medium_risk_coverage_threshold = float(thresholds["medium_risk_coverage_threshold"])
    min_uploads = int(thresholds["min_uploads"])
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

    if inventory_total_uploads > 0 and inventory_total_uploads < min_uploads and risk_level == "low":
        reasons.append("few_uploaded_documents")
        risk_level = "medium"

    if missing_doc_families and risk_level == "low":
        reasons.append("recommended_doc_families_missing")
        risk_level = "medium"

    if not reasons:
        reasons.append("sufficient_readiness_signals")

    blocking = mode == "strict" and risk_level == "high"
    summary = (
        "namespace_empty_or_low_coverage"
        if risk_level == "high"
        else "partial_readiness_signals" if risk_level == "medium" else "readiness_signals_ok"
    )

    return {
        "mode": mode,
        "risk_level": risk_level,
        "reasons": reasons,
        "summary": summary,
        "blocking": blocking,
        "go_ahead": not blocking,
        "thresholds": thresholds,
    }


def _build_generate_preflight(
    *,
    donor_id: str,
    strategy: Any,
    client_metadata: Optional[Dict[str, Any]],
    tenant_id: Optional[str] = None,
) -> Dict[str, Any]:
    metadata = client_metadata if isinstance(client_metadata, dict) else {}
    resolved_tenant_id = _normalize_tenant_candidate(tenant_id) or _normalize_tenant_candidate(
        metadata.get("tenant_id") or metadata.get("tenant")
    )
    base_namespace = str(getattr(strategy, "get_rag_collection", lambda: "")() or "").strip() or None
    namespace = _tenant_rag_namespace(base_namespace or "", resolved_tenant_id) if base_namespace else None
    namespace_normalized = vector_store.normalize_namespace(namespace or "")
    inventory_rows = _ingest_inventory(donor_id=donor_id or None, tenant_id=resolved_tenant_id)
    inventory_payload = public_ingest_inventory_payload(inventory_rows, donor_id=donor_id or None)
    doc_family_counts_raw = inventory_payload.get("doc_family_counts")
    doc_family_counts = doc_family_counts_raw if isinstance(doc_family_counts_raw, dict) else {}
    inventory_total_uploads = int(inventory_payload.get("total_uploads") or 0)

    expected_doc_families = _preflight_expected_doc_families(donor_id=donor_id, client_metadata=client_metadata)
    present_doc_families = [doc for doc in expected_doc_families if int(doc_family_counts.get(doc) or 0) > 0]
    missing_doc_families = [doc for doc in expected_doc_families if int(doc_family_counts.get(doc) or 0) <= 0]
    expected_count = len(expected_doc_families)
    loaded_count = len(present_doc_families)
    coverage_rate = round(loaded_count / expected_count, 4) if expected_count else None

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
        namespace_empty=namespace_empty,
        inventory_total_uploads=inventory_total_uploads,
        missing_doc_families=missing_doc_families,
    )
    grounding_risk_level = str(grounding_policy.get("risk_level") or "low")
    blocking = bool(grounding_policy.get("blocking"))
    return {
        "donor_id": donor_id,
        "tenant_id": resolved_tenant_id,
        "retrieval_namespace": namespace,
        "retrieval_namespace_normalized": namespace_normalized,
        "retrieval_query_terms": donor_query_preset_terms(donor_id),
        "expected_doc_families": expected_doc_families,
        "present_doc_families": present_doc_families,
        "missing_doc_families": missing_doc_families,
        "expected_count": expected_count,
        "loaded_count": loaded_count,
        "coverage_rate": coverage_rate,
        "inventory_total_uploads": inventory_total_uploads,
        "inventory_family_count": int(inventory_payload.get("family_count") or 0),
        "namespace_empty": namespace_empty,
        "warning_count": len(warnings),
        "warning_level": risk_level,
        "risk_level": risk_level,
        "grounding_risk_level": grounding_risk_level,
        "grounding_policy": grounding_policy,
        "go_ahead": risk_level != "high" and not blocking,
        "warnings": warnings,
    }


def _set_job(job_id: str, payload: Dict[str, Any]) -> None:
    previous = JOB_STORE.get(job_id)
    next_payload = dict(payload)

    if previous and previous.get("status") == "canceled" and next_payload.get("status") != "canceled":
        return

    for key in ("webhook_url", "webhook_secret", "client_metadata", "generate_preflight", "strict_preflight"):
        if key not in next_payload and previous and key in previous:
            next_payload[key] = previous.get(key)

    next_payload = _append_job_event_records(previous, next_payload)
    JOB_STORE.set(job_id, next_payload)
    _dispatch_job_webhook_for_status_change(job_id, previous, next_payload)


def _update_job(job_id: str, **patch: Any) -> Dict[str, Any]:
    previous = JOB_STORE.get(job_id)
    if previous and previous.get("status") == "canceled" and patch.get("status") != "canceled":
        return previous
    next_patch = dict(patch)
    merged_preview = dict(previous or {})
    merged_preview.update(next_patch)
    merged_preview = _append_job_event_records(previous, merged_preview)
    if "job_events" in merged_preview:
        next_patch["job_events"] = merged_preview["job_events"]
    updated = JOB_STORE.update(job_id, **next_patch)
    _dispatch_job_webhook_for_status_change(job_id, previous, updated)
    return updated


def _get_job(job_id: str) -> Optional[Dict[str, Any]]:
    return JOB_STORE.get(job_id)


def _list_jobs() -> Dict[str, Dict[str, Any]]:
    list_fn = getattr(JOB_STORE, "list", None)
    if callable(list_fn):
        result = list_fn()
        if isinstance(result, dict):
            return result
    return {}


class GenerateRequest(BaseModel):
    donor_id: str
    input_context: Dict[str, Any]
    tenant_id: Optional[str] = None
    llm_mode: bool = False
    hitl_enabled: bool = False
    hitl_checkpoints: Optional[list[Literal["architect", "toc", "mel", "logframe"]]] = None
    strict_preflight: bool = False
    webhook_url: Optional[str] = None
    webhook_secret: Optional[str] = None
    client_metadata: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(extra="forbid")


class GeneratePreflightRequest(BaseModel):
    donor_id: str
    tenant_id: Optional[str] = None
    client_metadata: Optional[Dict[str, Any]] = None
    input_context: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(extra="forbid")


class HITLApprovalRequest(BaseModel):
    checkpoint_id: str
    approved: bool
    feedback: Optional[str] = None


class ExportRequest(BaseModel):
    payload: Optional[Dict[str, Any]] = None
    toc_draft: Optional[Dict[str, Any]] = None
    logframe_draft: Optional[Dict[str, Any]] = None
    donor_id: Optional[str] = None
    review_comments: Optional[list[Dict[str, Any]]] = None
    critic_findings: Optional[list[Dict[str, Any]]] = None
    format: str = "both"
    allow_unsafe_export: bool = False

    model_config = ConfigDict(extra="allow")


class JobCommentCreateRequest(BaseModel):
    section: str
    message: str
    author: Optional[str] = None
    version_id: Optional[str] = None
    linked_finding_id: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class CriticFindingsBulkStatusRequest(BaseModel):
    next_status: str
    apply_to_all: bool = False
    finding_status: Optional[str] = None
    severity: Optional[str] = None
    section: Optional[str] = None
    finding_ids: Optional[list[str]] = None

    model_config = ConfigDict(extra="forbid")


class ReviewWorkflowSLARecomputeRequest(BaseModel):
    finding_sla_hours: Optional[Dict[str, int]] = None
    default_comment_sla_hours: Optional[int] = None
    use_saved_profile: bool = False

    model_config = ConfigDict(extra="forbid")


def _resolve_export_inputs(
    req: ExportRequest,
) -> tuple[dict, dict, str, list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    payload = req.payload or {}
    payload_root = payload if isinstance(payload, dict) else {}
    state_payload = payload_root.get("state") if isinstance(payload_root.get("state"), dict) else payload_root
    payload = state_payload if isinstance(state_payload, dict) else {}

    donor_id = req.donor_id or payload.get("donor") or payload.get("donor_id") or "grantflow"
    toc = req.toc_draft or payload.get("toc_draft") or payload.get("toc") or {}
    logframe = req.logframe_draft or payload.get("logframe_draft") or payload.get("mel") or {}
    citations = payload.get("citations") or []
    critic_notes_raw = payload.get("critic_notes")
    critic_notes: dict[str, Any] = critic_notes_raw if isinstance(critic_notes_raw, dict) else {}
    critic_findings = (
        req.critic_findings or critic_notes.get("fatal_flaws") or payload_root.get("critic_findings") or []
    )
    review_comments = req.review_comments or payload_root.get("review_comments") or payload.get("review_comments") or []

    if not isinstance(toc, dict):
        toc = {}
    if not isinstance(logframe, dict):
        logframe = {}
    if not isinstance(citations, list):
        citations = []
    if not isinstance(critic_findings, list):
        critic_findings = []
    if not isinstance(review_comments, list):
        review_comments = []
    citations = [c for c in citations if isinstance(c, dict)]
    critic_findings = normalize_findings(critic_findings, default_source="rules")
    critic_findings = bind_findings_to_latest_versions(critic_findings, state=payload)
    review_comments = [c for c in review_comments if isinstance(c, dict)]
    return toc, logframe, str(donor_id), citations, critic_findings, review_comments


def _extract_export_grounding_gate(req: ExportRequest) -> Dict[str, Any]:
    payload = req.payload if isinstance(req.payload, dict) else {}
    if not payload:
        return {}

    state_payload = payload.get("state") if isinstance(payload.get("state"), dict) else payload
    if not isinstance(state_payload, dict):
        return {}
    gate = state_payload.get("grounding_gate")
    return gate if isinstance(gate, dict) else {}


def _record_hitl_feedback_in_state(state: dict, checkpoint: Dict[str, Any]) -> None:
    feedback = checkpoint.get("feedback")
    if not feedback:
        return
    history = list(state.get("hitl_feedback_history") or [])
    history.append(
        {
            "checkpoint_id": checkpoint.get("id"),
            "stage": checkpoint.get("stage"),
            "status": getattr(checkpoint.get("status"), "value", checkpoint.get("status")),
            "feedback": feedback,
        }
    )
    state["hitl_feedback_history"] = history
    state["hitl_feedback"] = feedback


def _state_grounding_gate(state: Any) -> Dict[str, Any]:
    if not isinstance(state, dict):
        return {}
    gate = state.get("grounding_gate")
    return gate if isinstance(gate, dict) else {}


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


def _mel_grounding_policy_block_reason(state: Any) -> Optional[str]:
    policy = _evaluate_mel_grounding_policy_from_state(state)
    state_dict = state if isinstance(state, dict) else {}
    state_dict["mel_grounding_policy"] = policy
    if not bool(policy.get("blocking")):
        return None
    summary = str(policy.get("summary") or "").strip() or "weak mel grounding signals"
    return f"MEL grounding policy (strict) blocked finalization: {summary}"


def _job_draft_version_exists_for_section(job: Dict[str, Any], *, section: str, version_id: str) -> bool:
    state = job.get("state")
    if not isinstance(state, dict):
        return False
    raw_versions = state.get("draft_versions")
    if not isinstance(raw_versions, list):
        return False
    for item in raw_versions:
        if not isinstance(item, dict):
            continue
        if str(item.get("version_id") or "") != version_id:
            continue
        if str(item.get("section") or "") != section:
            continue
        return True
    return False


def _normalize_finding_sla_profile(
    finding_sla_hours: Optional[Dict[str, Any]],
    *,
    default: Optional[Dict[str, int]] = None,
) -> Dict[str, int]:
    profile: Dict[str, int] = dict(default or CRITIC_FINDING_SLA_HOURS)
    if not isinstance(finding_sla_hours, dict):
        return profile
    for raw_key, raw_value in finding_sla_hours.items():
        key = str(raw_key or "").strip().lower()
        if key not in CRITIC_FINDING_SLA_HOURS:
            raise HTTPException(status_code=400, detail=f"Unsupported SLA severity key: {raw_key}")
        try:
            value = int(raw_value)
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail=f"Invalid SLA hours for {key}") from None
        if value <= 0 or value > 24 * 365:
            raise HTTPException(status_code=400, detail=f"SLA hours for {key} must be within 1..8760")
        profile[key] = value
    return profile


def _normalize_comment_sla_hours(default_comment_sla_hours: Optional[Any]) -> int:
    if default_comment_sla_hours is None:
        return int(REVIEW_COMMENT_DEFAULT_SLA_HOURS)
    try:
        value = int(default_comment_sla_hours)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid default_comment_sla_hours") from None
    if value <= 0 or value > 24 * 365:
        raise HTTPException(status_code=400, detail="default_comment_sla_hours must be within 1..8760")
    return value


def _resolve_sla_profile_for_recompute(
    *,
    job: Dict[str, Any],
    finding_sla_hours_override: Optional[Dict[str, Any]],
    default_comment_sla_hours: Optional[Any],
    use_saved_profile: bool,
) -> tuple[Dict[str, int], int]:
    base_finding = dict(CRITIC_FINDING_SLA_HOURS)
    base_comment = int(REVIEW_COMMENT_DEFAULT_SLA_HOURS)

    if use_saved_profile:
        client_metadata = job.get("client_metadata")
        metadata = client_metadata if isinstance(client_metadata, dict) else {}
        saved_profile = metadata.get("sla_profile")
        saved_dict = saved_profile if isinstance(saved_profile, dict) else {}
        saved_finding = saved_dict.get("finding_sla_hours")
        saved_comment = saved_dict.get("default_comment_sla_hours")
        base_finding = _normalize_finding_sla_profile(saved_finding, default=base_finding)
        base_comment = _normalize_comment_sla_hours(saved_comment)

    resolved_finding = _normalize_finding_sla_profile(finding_sla_hours_override, default=base_finding)
    if default_comment_sla_hours is None:
        resolved_comment = base_comment
    else:
        resolved_comment = _normalize_comment_sla_hours(default_comment_sla_hours)
    return resolved_finding, resolved_comment


def _review_workflow_sla_profile_payload(job_id: str, job: Dict[str, Any]) -> Dict[str, Any]:
    client_metadata = job.get("client_metadata")
    metadata = client_metadata if isinstance(client_metadata, dict) else {}
    saved_profile = metadata.get("sla_profile")
    saved_profile_dict = saved_profile if isinstance(saved_profile, dict) else {}
    has_saved_profile = bool(saved_profile_dict)

    finding_sla_hours_default = dict(CRITIC_FINDING_SLA_HOURS)
    comment_sla_default = int(REVIEW_COMMENT_DEFAULT_SLA_HOURS)
    source = "default"
    saved_profile_valid = True
    saved_profile_error: Optional[str] = None
    finding_sla_hours = finding_sla_hours_default
    default_comment_sla_hours = comment_sla_default

    if has_saved_profile:
        try:
            finding_sla_hours = _normalize_finding_sla_profile(
                saved_profile_dict.get("finding_sla_hours"),
                default=finding_sla_hours_default,
            )
            default_comment_sla_hours = _normalize_comment_sla_hours(
                saved_profile_dict.get("default_comment_sla_hours")
            )
            source = "saved"
        except HTTPException as exc:
            saved_profile_valid = False
            saved_profile_error = str(exc.detail)
            finding_sla_hours = finding_sla_hours_default
            default_comment_sla_hours = comment_sla_default
            source = "default"

    return {
        "job_id": str(job_id),
        "status": str(job.get("status") or ""),
        "source": source,
        "finding_sla_hours": finding_sla_hours,
        "default_comment_sla_hours": default_comment_sla_hours,
        "saved_profile_available": has_saved_profile,
        "saved_profile_valid": saved_profile_valid,
        "saved_profile_error": saved_profile_error,
        "saved_profile_updated_at": str(saved_profile_dict.get("updated_at") or "").strip() or None,
        "saved_profile_updated_by": str(saved_profile_dict.get("updated_by") or "").strip() or None,
    }


def _ensure_finding_due_at(
    item: Dict[str, Any],
    *,
    now_iso: str,
    reset: bool = False,
    finding_sla_hours_override: Optional[Dict[str, int]] = None,
) -> Dict[str, Any]:
    current = dict(item)
    status = str(current.get("status") or "open").strip().lower()
    if status == "resolved":
        return current
    if not reset and str(current.get("due_at") or "").strip():
        return current
    sla_hours = _finding_sla_hours(current.get("severity"), finding_sla_hours_override=finding_sla_hours_override)
    base_ts = None
    if status == "acknowledged":
        base_ts = str(current.get("acknowledged_at") or current.get("updated_at") or now_iso)
    else:
        base_ts = str(current.get("updated_at") or now_iso)
    current["due_at"] = _iso_plus_hours(base_ts, sla_hours)
    current["sla_hours"] = sla_hours
    return current


def _normalize_critic_fatal_flaws_for_job(job_id: str) -> Optional[Dict[str, Any]]:
    job = _get_job(job_id)
    if not job:
        return None
    state = job.get("state")
    if not isinstance(state, dict):
        return job
    critic_notes = state.get("critic_notes")
    if not isinstance(critic_notes, dict):
        return job
    raw_flaws = critic_notes.get("fatal_flaws")
    if not isinstance(raw_flaws, list):
        return job

    normalized = normalize_findings(raw_flaws, previous_items=raw_flaws, default_source="rules")
    normalized = bind_findings_to_latest_versions(normalized, state=state)
    now_iso = _utcnow_iso()
    normalized_with_due = [_ensure_finding_due_at(item, now_iso=now_iso) for item in normalized]
    changed = normalized_with_due != raw_flaws

    if not changed:
        return job

    next_notes = dict(critic_notes)
    next_notes["fatal_flaws"] = normalized_with_due
    next_state = dict(state)
    next_state["critic_notes"] = next_notes
    next_state["critic_fatal_flaws"] = normalized_with_due
    return _update_job(job_id, state=next_state)


def _normalize_review_comments_for_job(job_id: str) -> Optional[Dict[str, Any]]:
    job = _get_job(job_id)
    if not job:
        return None
    raw_comments = job.get("review_comments")
    if not isinstance(raw_comments, list):
        return job
    comments = [c for c in raw_comments if isinstance(c, dict)]
    now_iso = _utcnow_iso()
    normalized_comments = [_ensure_comment_due_at(comment, job=job, now_iso=now_iso) for comment in comments]
    if normalized_comments == comments:
        return job
    return _update_job(job_id, review_comments=normalized_comments[-500:])


def _recompute_review_workflow_sla(
    job_id: str,
    *,
    actor: Optional[str] = None,
    finding_sla_hours_override: Optional[Dict[str, Any]] = None,
    default_comment_sla_hours: Optional[Any] = None,
    use_saved_profile: bool = False,
) -> Dict[str, Any]:
    job = _normalize_critic_fatal_flaws_for_job(job_id) or _get_job(job_id)
    job = _normalize_review_comments_for_job(job_id) or job
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    now_iso = _utcnow_iso()
    actor_value = str(actor or "").strip() or "api_user"
    applied_finding_sla_hours, applied_default_comment_sla_hours = _resolve_sla_profile_for_recompute(
        job=job,
        finding_sla_hours_override=finding_sla_hours_override,
        default_comment_sla_hours=default_comment_sla_hours,
        use_saved_profile=bool(use_saved_profile),
    )

    state = job.get("state")
    state_dict = state if isinstance(state, dict) else {}
    critic_notes = state_dict.get("critic_notes")
    critic_notes_dict = critic_notes if isinstance(critic_notes, dict) else {}
    raw_flaws = critic_notes_dict.get("fatal_flaws")
    flaws = normalize_findings(raw_flaws if isinstance(raw_flaws, list) else [], default_source="rules")
    flaws = bind_findings_to_latest_versions(flaws, state=state)

    finding_checked_count = len(flaws)
    finding_updated_count = 0
    next_flaws: list[Dict[str, Any]] = []
    for item in flaws:
        current = dict(item)
        recomputed = _ensure_finding_due_at(
            current,
            now_iso=now_iso,
            reset=True,
            finding_sla_hours_override=applied_finding_sla_hours,
        )
        if recomputed != current:
            finding_updated_count += 1
        next_flaws.append(recomputed)

    next_state = state_dict
    state_changed = False
    if (
        isinstance(state, dict)
        and isinstance(critic_notes, dict)
        and (next_flaws != (raw_flaws if isinstance(raw_flaws, list) else []))
    ):
        next_notes = dict(critic_notes_dict)
        next_notes["fatal_flaws"] = next_flaws
        next_state = dict(state_dict)
        next_state["critic_notes"] = next_notes
        next_state["critic_fatal_flaws"] = next_flaws
        state_changed = True

    working_job = dict(job)
    if state_changed:
        working_job["state"] = next_state

    raw_comments = job.get("review_comments")
    comments = [c for c in raw_comments if isinstance(c, dict)] if isinstance(raw_comments, list) else []
    comment_checked_count = len(comments)
    comment_updated_count = 0
    next_comments: list[Dict[str, Any]] = []
    for comment in comments:
        current = dict(comment)
        recomputed = _ensure_comment_due_at(
            current,
            job=working_job,
            now_iso=now_iso,
            reset=True,
            finding_sla_hours_override=applied_finding_sla_hours,
            default_comment_sla_hours=applied_default_comment_sla_hours,
        )
        if recomputed != current:
            comment_updated_count += 1
        next_comments.append(recomputed)

    update_payload: Dict[str, Any] = {}
    if state_changed:
        update_payload["state"] = next_state
    if next_comments != comments:
        update_payload["review_comments"] = next_comments[-500:]

    client_metadata = job.get("client_metadata")
    metadata = dict(client_metadata) if isinstance(client_metadata, dict) else {}
    sla_profile = {
        "finding_sla_hours": dict(applied_finding_sla_hours),
        "default_comment_sla_hours": int(applied_default_comment_sla_hours),
        "updated_at": now_iso,
        "updated_by": actor_value,
    }
    if metadata.get("sla_profile") != sla_profile:
        metadata["sla_profile"] = sla_profile
        update_payload["client_metadata"] = metadata

    if update_payload:
        job = _update_job(job_id, **update_payload) or _get_job(job_id) or job

    total_updated_count = finding_updated_count + comment_updated_count
    _record_job_event(
        job_id,
        "review_workflow_sla_recomputed",
        actor=actor_value,
        finding_checked_count=finding_checked_count,
        comment_checked_count=comment_checked_count,
        finding_updated_count=finding_updated_count,
        comment_updated_count=comment_updated_count,
        total_updated_count=total_updated_count,
        use_saved_profile=bool(use_saved_profile),
        applied_finding_sla_hours=applied_finding_sla_hours,
        applied_default_comment_sla_hours=applied_default_comment_sla_hours,
    )

    return {
        "job_id": str(job_id),
        "status": str((job or {}).get("status") or ""),
        "actor": actor_value,
        "recomputed_at": now_iso,
        "use_saved_profile": bool(use_saved_profile),
        "applied_finding_sla_hours": applied_finding_sla_hours,
        "applied_default_comment_sla_hours": applied_default_comment_sla_hours,
        "finding_checked_count": finding_checked_count,
        "comment_checked_count": comment_checked_count,
        "finding_updated_count": finding_updated_count,
        "comment_updated_count": comment_updated_count,
        "total_updated_count": total_updated_count,
        "sla": public_job_review_workflow_sla_payload(
            job_id,
            job,
            overdue_after_hours=REVIEW_WORKFLOW_OVERDUE_DEFAULT_HOURS,
        ),
    }


def _find_critic_fatal_flaw(job: Dict[str, Any], finding_id: str) -> Optional[Dict[str, Any]]:
    state = job.get("state")
    if not isinstance(state, dict):
        return None
    critic_notes = state.get("critic_notes")
    if not isinstance(critic_notes, dict):
        return None
    raw_flaws = critic_notes.get("fatal_flaws")
    if not isinstance(raw_flaws, list):
        return None
    for item in raw_flaws:
        if not isinstance(item, dict):
            continue
        if finding_primary_id(item) == finding_id:
            return item
    return None


def _set_critic_fatal_flaw_status(
    job_id: str,
    *,
    finding_id: str,
    next_status: str,
    actor: Optional[str] = None,
) -> Dict[str, Any]:
    if next_status not in CRITIC_FINDING_STATUSES:
        raise HTTPException(status_code=400, detail="Unsupported critic finding status")

    job = _normalize_critic_fatal_flaws_for_job(job_id) or _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    state = job.get("state")
    if not isinstance(state, dict):
        raise HTTPException(status_code=404, detail="Critic findings not found")
    critic_notes = state.get("critic_notes")
    if not isinstance(critic_notes, dict):
        raise HTTPException(status_code=404, detail="Critic findings not found")

    raw_flaws = critic_notes.get("fatal_flaws")
    flaws = normalize_findings(raw_flaws if isinstance(raw_flaws, list) else [], default_source="rules")
    flaws = bind_findings_to_latest_versions(flaws, state=state)
    if not flaws:
        raise HTTPException(status_code=404, detail="Critic findings not found")

    changed = False
    updated_finding: Optional[Dict[str, Any]] = None
    next_flaws: list[Dict[str, Any]] = []
    now = _utcnow_iso()
    actor_value = str(actor or "").strip() or "api_user"
    for item in flaws:
        current = dict(item)
        current_finding_id = finding_primary_id(current)
        if current_finding_id != finding_id:
            next_flaws.append(current)
            continue
        current, finding_changed = _apply_critic_finding_status_transition(
            current,
            next_status=next_status,
            now=now,
            actor_value=actor_value,
        )
        if finding_changed:
            changed = True
        updated_finding = current
        next_flaws.append(current)

    if updated_finding is None:
        raise HTTPException(status_code=404, detail="Critic finding not found")

    if changed:
        next_notes = dict(critic_notes)
        next_notes["fatal_flaws"] = next_flaws
        next_state = dict(state)
        next_state["critic_notes"] = next_notes
        next_state["critic_fatal_flaws"] = next_flaws
        _update_job(job_id, state=next_state)
        _record_job_event(
            job_id,
            "critic_finding_status_changed",
            finding_id=str(updated_finding.get("id") or finding_id),
            status=next_status,
            section=updated_finding.get("section"),
            severity=updated_finding.get("severity"),
            actor=actor_value,
        )

    return updated_finding


def _apply_critic_finding_status_transition(
    item: Dict[str, Any],
    *,
    next_status: str,
    now: str,
    actor_value: str,
) -> tuple[Dict[str, Any], bool]:
    current = dict(item)
    current_finding_id = finding_primary_id(current)
    if current_finding_id:
        current["id"] = current_finding_id
        current["finding_id"] = current_finding_id
    current = _ensure_finding_due_at(current, now_iso=now)

    current_status = str(current.get("status") or "open")
    if current_status == next_status:
        return current, False

    current["status"] = next_status
    current["updated_at"] = now
    current["updated_by"] = actor_value
    if next_status == "acknowledged":
        current["acknowledged_at"] = current.get("acknowledged_at") or now
        current["acknowledged_by"] = actor_value
        current.pop("resolved_at", None)
        current.pop("resolved_by", None)
        current = _ensure_finding_due_at(current, now_iso=now)
    elif next_status == "resolved":
        current["resolved_at"] = now
        current["resolved_by"] = actor_value
        if not current.get("acknowledged_at"):
            current["acknowledged_at"] = now
        if not current.get("acknowledged_by"):
            current["acknowledged_by"] = actor_value
    elif next_status == "open":
        current.pop("acknowledged_at", None)
        current.pop("acknowledged_by", None)
        current.pop("resolved_at", None)
        current.pop("resolved_by", None)
        current = _ensure_finding_due_at(current, now_iso=now, reset=True)
    return current, True


def _set_critic_fatal_flaws_status_bulk(
    job_id: str,
    *,
    next_status: str,
    actor: Optional[str] = None,
    apply_to_all: bool = False,
    finding_status: Optional[str] = None,
    severity: Optional[str] = None,
    section: Optional[str] = None,
    finding_ids: Optional[list[str]] = None,
) -> Dict[str, Any]:
    if next_status not in CRITIC_FINDING_STATUSES:
        raise HTTPException(status_code=400, detail="Unsupported critic finding status")

    finding_status_filter = str(finding_status or "").strip().lower() or None
    if finding_status_filter and finding_status_filter not in CRITIC_FINDING_STATUSES:
        raise HTTPException(status_code=400, detail="Unsupported finding_status filter")
    severity_filter = str(severity or "").strip().lower() or None
    if severity_filter and severity_filter not in {"high", "medium", "low"}:
        raise HTTPException(status_code=400, detail="Unsupported severity filter")
    section_filter = str(section or "").strip().lower() or None
    if section_filter and section_filter not in {"toc", "logframe", "general"}:
        raise HTTPException(status_code=400, detail="Unsupported section filter")

    requested_finding_ids_raw = finding_ids if isinstance(finding_ids, list) else []
    requested_finding_ids: list[str] = []
    for item in requested_finding_ids_raw:
        token = str(item or "").strip()
        if not token:
            continue
        if token not in requested_finding_ids:
            requested_finding_ids.append(token)
    requested_finding_ids_set = set(requested_finding_ids)

    has_selector = bool(requested_finding_ids or finding_status_filter or severity_filter or section_filter)
    if not has_selector and not apply_to_all:
        raise HTTPException(status_code=400, detail="Provide at least one selector or set apply_to_all=true")

    job = _normalize_critic_fatal_flaws_for_job(job_id) or _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    state = job.get("state")
    if not isinstance(state, dict):
        raise HTTPException(status_code=404, detail="Critic findings not found")
    critic_notes = state.get("critic_notes")
    if not isinstance(critic_notes, dict):
        raise HTTPException(status_code=404, detail="Critic findings not found")

    raw_flaws = critic_notes.get("fatal_flaws")
    flaws = normalize_findings(raw_flaws if isinstance(raw_flaws, list) else [], default_source="rules")
    flaws = bind_findings_to_latest_versions(flaws, state=state)
    if not flaws:
        raise HTTPException(status_code=404, detail="Critic findings not found")

    available_ids = {finding_primary_id(item) for item in flaws if finding_primary_id(item)}
    not_found_finding_ids = [item for item in requested_finding_ids if item not in available_ids]

    now = _utcnow_iso()
    actor_value = str(actor or "").strip() or "api_user"
    batch_id = str(uuid.uuid4())

    changed = False
    changed_items: list[Dict[str, Any]] = []
    matched_items: list[Dict[str, Any]] = []
    next_flaws: list[Dict[str, Any]] = []

    for item in flaws:
        current = dict(item)
        current_finding_id = finding_primary_id(current)
        current_status = str(current.get("status") or "open").strip().lower()
        current_severity = str(current.get("severity") or "").strip().lower()
        current_section = str(current.get("section") or "").strip().lower()
        if current_finding_id:
            current["id"] = current_finding_id
            current["finding_id"] = current_finding_id

        match = bool(apply_to_all)
        if not apply_to_all:
            match = True
            if requested_finding_ids_set and current_finding_id not in requested_finding_ids_set:
                match = False
            if finding_status_filter and current_status != finding_status_filter:
                match = False
            if severity_filter and current_severity != severity_filter:
                match = False
            if section_filter and current_section != section_filter:
                match = False
        if not match:
            next_flaws.append(current)
            continue

        updated, finding_changed = _apply_critic_finding_status_transition(
            current,
            next_status=next_status,
            now=now,
            actor_value=actor_value,
        )
        matched_items.append(updated)
        next_flaws.append(updated)
        if finding_changed:
            changed = True
            changed_items.append(updated)

    if changed:
        next_notes = dict(critic_notes)
        next_notes["fatal_flaws"] = next_flaws
        next_state = dict(state)
        next_state["critic_notes"] = next_notes
        next_state["critic_fatal_flaws"] = next_flaws
        _update_job(job_id, state=next_state)
        for updated in changed_items:
            _record_job_event(
                job_id,
                "critic_finding_status_changed",
                finding_id=str(updated.get("id") or ""),
                status=next_status,
                section=updated.get("section"),
                severity=updated.get("severity"),
                actor=actor_value,
                batch_id=batch_id,
            )

    matched_count = len(matched_items)
    changed_count = len(changed_items)
    return {
        "job_id": str(job_id),
        "status": str((job or {}).get("status") or ""),
        "requested_status": next_status,
        "actor": actor_value,
        "matched_count": matched_count,
        "changed_count": changed_count,
        "unchanged_count": max(0, matched_count - changed_count),
        "not_found_finding_ids": not_found_finding_ids,
        "filters": {
            "apply_to_all": bool(apply_to_all),
            "finding_status": finding_status_filter,
            "severity": severity_filter,
            "section": section_filter,
            "finding_ids": requested_finding_ids or None,
        },
        "updated_findings": matched_items,
    }


def _linked_finding_severity(job: Dict[str, Any], linked_finding_id: Optional[str]) -> Optional[str]:
    token = str(linked_finding_id or "").strip()
    if not token:
        return None
    finding = _find_critic_fatal_flaw(job, token)
    if not isinstance(finding, dict):
        return None
    severity = str(finding.get("severity") or "").strip().lower()
    return severity or None


def _ensure_comment_due_at(
    comment: Dict[str, Any],
    *,
    job: Dict[str, Any],
    now_iso: str,
    reset: bool = False,
    finding_sla_hours_override: Optional[Dict[str, int]] = None,
    default_comment_sla_hours: Optional[int] = None,
) -> Dict[str, Any]:
    current = dict(comment)
    status = str(current.get("status") or "open").strip().lower()
    if status == "resolved":
        return current
    if not reset and str(current.get("due_at") or "").strip():
        if not current.get("sla_hours"):
            inferred_sla = _comment_sla_hours(
                linked_finding_severity=_linked_finding_severity(
                    job, str(current.get("linked_finding_id") or "").strip()
                ),
                finding_sla_hours_override=finding_sla_hours_override,
                default_comment_sla_hours=default_comment_sla_hours,
            )
            current["sla_hours"] = inferred_sla
        return current
    linked_finding_id = str(current.get("linked_finding_id") or "").strip() or None
    severity = _linked_finding_severity(job, linked_finding_id)
    sla_hours = _comment_sla_hours(
        linked_finding_severity=severity,
        finding_sla_hours_override=finding_sla_hours_override,
        default_comment_sla_hours=default_comment_sla_hours,
    )
    base_ts = str(current.get("updated_ts") or current.get("ts") or now_iso)
    current["sla_hours"] = sla_hours
    current["due_at"] = _iso_plus_hours(base_ts, sla_hours)
    return current


def _append_review_comment(
    job_id: str,
    *,
    section: str,
    message: str,
    author: Optional[str] = None,
    version_id: Optional[str] = None,
    linked_finding_id: Optional[str] = None,
    linked_finding_severity: Optional[str] = None,
) -> Dict[str, Any]:
    job = _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    existing = job.get("review_comments")
    comments = [c for c in existing if isinstance(c, dict)] if isinstance(existing, list) else []
    comment: Dict[str, Any] = {
        "comment_id": str(uuid.uuid4()),
        "ts": _utcnow_iso(),
        "section": section,
        "status": "open",
        "message": message,
    }
    comment["sla_hours"] = _comment_sla_hours(linked_finding_severity=linked_finding_severity)
    comment["due_at"] = _iso_plus_hours(comment["ts"], int(comment["sla_hours"]))
    if author:
        comment["author"] = author
    if version_id:
        comment["version_id"] = version_id
    if linked_finding_id:
        comment["linked_finding_id"] = linked_finding_id
    comments.append(comment)
    _update_job(job_id, review_comments=comments[-500:])
    _record_job_event(
        job_id,
        "review_comment_added",
        comment_id=comment["comment_id"],
        section=section,
        version_id=version_id,
        author=author,
        linked_finding_id=linked_finding_id,
    )
    return comment


def _set_review_comment_status(
    job_id: str,
    *,
    comment_id: str,
    next_status: str,
) -> Dict[str, Any]:
    job = _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    existing = job.get("review_comments")
    comments = [c for c in existing if isinstance(c, dict)] if isinstance(existing, list) else []
    updated_comment: Optional[Dict[str, Any]] = None
    changed = False
    status_transitioned = False
    now_iso = _utcnow_iso()

    next_comments: list[Dict[str, Any]] = []
    for item in comments:
        cid = str(item.get("comment_id") or "")
        if cid != comment_id:
            next_comments.append(item)
            continue

        current = dict(item)
        current_status = str(current.get("status") or "open")
        current_with_due = _ensure_comment_due_at(current, job=job, now_iso=now_iso)
        if current_with_due != current:
            changed = True
        current = current_with_due
        if current_status != next_status:
            current["status"] = next_status
            current["updated_ts"] = now_iso
            if next_status == "resolved":
                current["resolved_at"] = current["updated_ts"]
            elif "resolved_at" in current:
                current.pop("resolved_at", None)
            if next_status == "open":
                current = _ensure_comment_due_at(current, job=job, now_iso=now_iso, reset=True)
            changed = True
            status_transitioned = True
        updated_comment = current
        next_comments.append(current)

    if updated_comment is None:
        raise HTTPException(status_code=404, detail="Comment not found")

    if changed:
        _update_job(job_id, review_comments=next_comments[-500:])
    if status_transitioned:
        _record_job_event(
            job_id,
            "review_comment_status_changed",
            comment_id=comment_id,
            status=next_status,
            section=updated_comment.get("section"),
        )
    return updated_comment


def _job_is_canceled(job_id: str) -> bool:
    job = _get_job(job_id)
    return bool(job and job.get("status") == "canceled")


def _dispatch_job_webhook_for_status_change(
    job_id: str,
    previous: Optional[Dict[str, Any]],
    current: Optional[Dict[str, Any]],
) -> None:
    if not current:
        return

    previous_status = (previous or {}).get("status")
    current_status = current.get("status")
    if previous_status == current_status:
        return

    event_name = STATUS_WEBHOOK_EVENTS.get(str(current_status))
    if not event_name:
        return

    webhook_url = str(current.get("webhook_url") or (previous or {}).get("webhook_url") or "").strip()
    if not webhook_url:
        return

    webhook_secret = current.get("webhook_secret") or (previous or {}).get("webhook_secret")
    public_payload = public_job_payload(current)
    try:
        send_job_webhook_event(
            url=webhook_url,
            secret=str(webhook_secret) if webhook_secret else None,
            event=event_name,
            job_id=job_id,
            job=public_payload,
        )
    except Exception:
        # Webhook delivery failures are non-fatal for the job lifecycle.
        pass


install_openapi_api_key_security(app)


def _pause_for_hitl(job_id: str, state: dict, stage: Literal["toc", "logframe"], resume_from: HITLStartAt) -> None:
    existing_checkpoint_id = str(state.get("hitl_checkpoint_id") or "").strip() or None
    if _job_is_canceled(job_id):
        if existing_checkpoint_id:
            hitl_manager.cancel(existing_checkpoint_id, "Canceled before HITL checkpoint was published")
        return
    for key in RUNTIME_PIPELINE_STATE_KEYS:
        state.pop(key, None)
    state["hitl_pending"] = True
    normalize_state_contract(state)
    donor_id = state_donor_id(state, default="unknown")
    checkpoint_id = existing_checkpoint_id
    if checkpoint_id:
        checkpoint = hitl_manager.get_checkpoint(checkpoint_id)
        if not checkpoint:
            checkpoint_id = None
    if not checkpoint_id:
        checkpoint_id = hitl_manager.create_checkpoint(stage, state, donor_id)
    if _job_is_canceled(job_id):
        hitl_manager.cancel(checkpoint_id, "Canceled before HITL checkpoint was published")
        return
    _set_job(
        job_id,
        {
            "status": "pending_hitl",
            "state": state,
            "checkpoint_id": checkpoint_id,
            "checkpoint_stage": stage,
            "resume_from": resume_from,
            "hitl_enabled": True,
        },
    )


def _run_pipeline_to_completion(job_id: str, initial_state: dict) -> None:
    try:
        if _job_is_canceled(job_id):
            return
        normalize_state_contract(initial_state)
        initial_state["hitl_enabled"] = False
        initial_state["_start_at"] = "start"
        _set_job(job_id, {"status": "running", "state": initial_state, "hitl_enabled": False})
        if _job_is_canceled(job_id):
            return
        final_state = grantflow_graph.invoke(initial_state)
        for key in RUNTIME_PIPELINE_STATE_KEYS:
            final_state.pop(key, None)
        final_state["hitl_pending"] = False
        normalize_state_contract(final_state)
        if _job_is_canceled(job_id):
            return
        grounding_block_reason = _grounding_gate_block_reason(final_state)
        if grounding_block_reason:
            _set_job(
                job_id,
                {
                    "status": "error",
                    "error": grounding_block_reason,
                    "state": final_state,
                    "hitl_enabled": False,
                },
            )
            return
        mel_grounding_block_reason = _mel_grounding_policy_block_reason(final_state)
        if mel_grounding_block_reason:
            _set_job(
                job_id,
                {
                    "status": "error",
                    "error": mel_grounding_block_reason,
                    "state": final_state,
                    "hitl_enabled": False,
                },
            )
            return
        _set_job(job_id, {"status": "done", "state": final_state, "hitl_enabled": False})
    except Exception as exc:
        _set_job(job_id, {"status": "error", "error": str(exc), "hitl_enabled": False})


def _run_hitl_pipeline(job_id: str, state: dict, start_at: HITLStartAt) -> None:
    try:
        if _job_is_canceled(job_id):
            return
        normalize_state_contract(state)
        state["hitl_enabled"] = True
        state["_start_at"] = start_at
        _set_job(
            job_id,
            {
                "status": "running",
                "state": state,
                "hitl_enabled": True,
                "resume_from": start_at,
            },
        )
        if _job_is_canceled(job_id):
            return
        final_state = grantflow_graph.invoke(state)
        if _job_is_canceled(job_id):
            return
        checkpoint_stage = str(final_state.get("hitl_checkpoint_stage") or "").strip().lower()
        checkpoint_resume = str(final_state.get("hitl_resume_from") or "").strip().lower()
        if bool(final_state.get("hitl_pending")) and checkpoint_stage in {"toc", "logframe"}:
            stage_literal: Literal["toc", "logframe"] = "toc" if checkpoint_stage == "toc" else "logframe"
            resume_literal: HITLStartAt
            if checkpoint_resume == "start":
                resume_literal = "start"
            elif checkpoint_resume == "architect":
                resume_literal = "architect"
            elif checkpoint_resume == "mel":
                resume_literal = "mel"
            elif checkpoint_resume == "critic":
                resume_literal = "critic"
            else:
                resume_literal = "mel" if stage_literal == "toc" else "critic"
            _pause_for_hitl(job_id, final_state, stage=stage_literal, resume_from=resume_literal)
            return
        for key in RUNTIME_PIPELINE_STATE_KEYS:
            final_state.pop(key, None)
        final_state["hitl_pending"] = False
        grounding_block_reason = _grounding_gate_block_reason(final_state)
        if grounding_block_reason:
            _set_job(
                job_id,
                {
                    "status": "error",
                    "error": grounding_block_reason,
                    "state": final_state,
                    "hitl_enabled": True,
                },
            )
            return
        mel_grounding_block_reason = _mel_grounding_policy_block_reason(final_state)
        if mel_grounding_block_reason:
            _set_job(
                job_id,
                {
                    "status": "error",
                    "error": mel_grounding_block_reason,
                    "state": final_state,
                    "hitl_enabled": True,
                },
            )
            return
        _set_job(job_id, {"status": "done", "state": final_state, "hitl_enabled": True})
        return
    except Exception as exc:
        _set_job(job_id, {"status": "error", "error": str(exc), "hitl_enabled": True, "state": state})


def _resume_target_from_checkpoint(checkpoint: Dict[str, Any], default_resume_from: str | None) -> HITLStartAt:
    stage = checkpoint.get("stage")
    status = checkpoint.get("status")

    if status == HITLStatus.APPROVED:
        if stage == "toc":
            return "mel"
        if stage == "logframe":
            return "critic"

    if status == HITLStatus.REJECTED:
        if stage == "toc":
            return "architect"
        if stage == "logframe":
            return "mel"

    if default_resume_from in {"start", "architect", "mel", "critic"}:
        return default_resume_from  # type: ignore[return-value]

    raise ValueError("Checkpoint is not ready for resume")


def _health_diagnostics() -> dict[str, Any]:
    job_store_mode = "sqlite" if getattr(JOB_STORE, "db_path", None) else "inmem"
    hitl_store_mode = "sqlite" if bool(getattr(hitl_manager, "_use_sqlite", False)) else "inmem"
    ingest_store_mode = "sqlite" if getattr(INGEST_AUDIT_STORE, "db_path", None) else "inmem"
    sqlite_path = getattr(JOB_STORE, "db_path", None) or (
        getattr(hitl_manager, "_sqlite_path", None) if hitl_store_mode == "sqlite" else None
    )
    if not sqlite_path and ingest_store_mode == "sqlite":
        sqlite_path = getattr(INGEST_AUDIT_STORE, "db_path", None)

    vector_backend = "chroma" if getattr(vector_store, "client", None) is not None else "memory"
    preflight_grounding_thresholds = _preflight_grounding_policy_thresholds()
    mel_grounding_thresholds = _mel_grounding_policy_thresholds()
    export_grounding_thresholds = _export_grounding_policy_thresholds()
    diagnostics: dict[str, Any] = {
        "job_store": {"mode": job_store_mode},
        "hitl_store": {"mode": hitl_store_mode},
        "ingest_store": {"mode": ingest_store_mode},
        "auth": {
            "api_key_configured": bool(api_key_configured()),
            "read_auth_required": bool(read_auth_required()),
            "tenant_authz_enabled": _tenant_authz_enabled(),
            "allowed_tenant_count": len(_allowed_tenant_tokens()),
        },
        "vector_store": {
            "backend": vector_backend,
            "collection_prefix": getattr(vector_store, "prefix", "grantflow"),
        },
        "preflight_grounding_policy": {
            "mode": _configured_preflight_grounding_policy_mode(),
            "thresholds": preflight_grounding_thresholds,
        },
        "mel_grounding_policy": {
            "mode": _configured_mel_grounding_policy_mode(),
            "thresholds": mel_grounding_thresholds,
        },
        "export_grounding_policy": {
            "mode": _configured_export_grounding_policy_mode(),
            "thresholds": export_grounding_thresholds,
        },
    }
    if sqlite_path and (job_store_mode == "sqlite" or hitl_store_mode == "sqlite" or ingest_store_mode == "sqlite"):
        diagnostics["sqlite"] = {"path": str(sqlite_path)}
    client_init_error = getattr(vector_store, "_client_init_error", None)
    if client_init_error:
        diagnostics["vector_store"]["client_init_error"] = str(client_init_error)
    return diagnostics


def _portfolio_export_response(
    *,
    payload: Dict[str, Any],
    filename_prefix: str,
    donor_id: Optional[str],
    status: Optional[str],
    hitl_enabled: Optional[bool],
    export_format: Literal["csv", "json"],
    gzip_enabled: bool,
    csv_renderer,
) -> StreamingResponse:
    filename_parts = [filename_prefix]
    if donor_id:
        filename_parts.append(donor_id)
    if status:
        filename_parts.append(status)
    if hitl_enabled is not None:
        filename_parts.append(f"hitl_{str(hitl_enabled).lower()}")

    if export_format == "csv":
        body_text = csv_renderer(payload)
        media_type = "text/csv; charset=utf-8"
        extension = "csv"
    elif export_format == "json":
        body_text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
        media_type = "application/json"
        extension = "json"
    else:
        raise HTTPException(status_code=400, detail="Unsupported export format")

    body_bytes = body_text.encode("utf-8")
    if gzip_enabled:
        body_bytes = gzip.compress(body_bytes)
        extension = f"{extension}.gz"
        media_type = "application/gzip"

    filename = "_".join(filename_parts) + f".{extension}"
    return StreamingResponse(
        io.BytesIO(body_bytes),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _vector_store_readiness() -> dict[str, Any]:
    client = getattr(vector_store, "client", None)
    backend = "chroma" if client is not None else "memory"

    if backend == "memory":
        return {"ready": True, "backend": "memory", "reason": "in-memory fallback backend active"}

    try:
        heartbeat = getattr(client, "heartbeat", None)
        if callable(heartbeat):
            hb_value = heartbeat()
            return {"ready": True, "backend": "chroma", "heartbeat": str(hb_value)}

        # Fallback to a lightweight no-op-ish capability check if heartbeat() is unavailable.
        list_collections = getattr(client, "list_collections", None)
        if callable(list_collections):
            list_collections()
        return {"ready": True, "backend": "chroma"}
    except Exception as exc:
        return {"ready": False, "backend": "chroma", "error": str(exc)}


configure_health_router(
    health_diagnostics_fn=_health_diagnostics,
    vector_store_readiness_fn=_vector_store_readiness,
    preflight_mode_fn=_configured_preflight_grounding_policy_mode,
    preflight_thresholds_fn=_preflight_grounding_policy_thresholds,
    mel_mode_fn=_configured_mel_grounding_policy_mode,
    mel_thresholds_fn=_mel_grounding_policy_thresholds,
    export_mode_fn=_configured_export_grounding_policy_mode,
    export_thresholds_fn=_export_grounding_policy_thresholds,
    version_value=__version__,
)
app.include_router(health_router)
app.include_router(system_misc_router)


configure_portfolio_read_router(
    require_api_key_if_configured=require_api_key_if_configured,
    list_jobs=_list_jobs,
    public_portfolio_metrics_payload=public_portfolio_metrics_payload,
    public_portfolio_quality_payload=public_portfolio_quality_payload,
    portfolio_export_response=_portfolio_export_response,
    public_portfolio_metrics_csv_text=public_portfolio_metrics_csv_text,
    public_portfolio_quality_csv_text=public_portfolio_quality_csv_text,
)
app.include_router(portfolio_read_router)

@app.post("/generate/preflight")
def generate_preflight(req: GeneratePreflightRequest, request: Request):
    require_api_key_if_configured(request)
    donor = req.donor_id.strip()
    if not donor:
        raise HTTPException(status_code=400, detail="Missing donor_id")
    try:
        strategy = DonorFactory.get_strategy(donor)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    metadata = dict(req.client_metadata) if isinstance(req.client_metadata, dict) else {}
    tenant_id = _resolve_tenant_id(
        request,
        explicit_tenant=req.tenant_id,
        client_metadata=metadata,
        require_if_enabled=True,
    )
    if tenant_id:
        metadata["tenant_id"] = tenant_id
    client_metadata = metadata or None
    return _build_generate_preflight(
        donor_id=donor,
        strategy=strategy,
        client_metadata=client_metadata,
    )


@app.post("/generate")
async def generate(req: GenerateRequest, background_tasks: BackgroundTasks, request: Request):
    require_api_key_if_configured(request)
    donor = req.donor_id.strip()
    if not donor:
        raise HTTPException(status_code=400, detail="Missing donor_id")

    webhook_url = (req.webhook_url or "").strip() or None
    webhook_secret = (req.webhook_secret or "").strip() or None
    if webhook_secret and not webhook_url:
        raise HTTPException(status_code=400, detail="webhook_secret requires webhook_url")
    if webhook_url and not (webhook_url.startswith("http://") or webhook_url.startswith("https://")):
        raise HTTPException(status_code=400, detail="webhook_url must start with http:// or https://")

    try:
        strategy = DonorFactory.get_strategy(donor)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    input_payload = req.input_context or {}
    metadata = dict(req.client_metadata) if isinstance(req.client_metadata, dict) else {}
    tenant_id = _resolve_tenant_id(
        request,
        explicit_tenant=req.tenant_id,
        client_metadata=metadata,
        require_if_enabled=True,
    )
    if tenant_id:
        metadata["tenant_id"] = tenant_id
    client_metadata = metadata or None
    preflight = _build_generate_preflight(
        donor_id=donor,
        strategy=strategy,
        client_metadata=client_metadata,
    )
    preflight_payload: Dict[str, Any] = preflight if isinstance(preflight, dict) else {}
    raw_grounding_policy = preflight_payload.get("grounding_policy")
    grounding_policy: Dict[str, Any] = raw_grounding_policy if isinstance(raw_grounding_policy, dict) else {}
    if bool(grounding_policy.get("blocking")):
        raise HTTPException(
            status_code=409,
            detail={
                "reason": "preflight_grounding_policy_block",
                "message": "Generation blocked by strict grounding policy before pipeline start.",
                "preflight": preflight_payload,
            },
        )
    preflight_risk_high = str(preflight_payload.get("risk_level") or "").lower() == "high"
    grounding_risk_high = str(preflight_payload.get("grounding_risk_level") or "").lower() == "high"
    if req.strict_preflight and str(preflight_payload.get("risk_level") or "").lower() == "high":
        strict_reasons = []
        if preflight_risk_high:
            strict_reasons.append("readiness_risk_high")
        if grounding_risk_high:
            strict_reasons.append("grounding_risk_high")
        raise HTTPException(
            status_code=409,
            detail={
                "reason": "preflight_high_risk_block",
                "message": "Generation blocked by strict_preflight because donor readiness risk is high.",
                "strict_reasons": strict_reasons,
                "preflight": preflight_payload,
            },
        )
    if req.strict_preflight and grounding_risk_high:
        raise HTTPException(
            status_code=409,
            detail={
                "reason": "preflight_high_risk_block",
                "message": "Generation blocked by strict_preflight because predicted grounding risk is high.",
                "strict_reasons": ["grounding_risk_high"],
                "preflight": preflight_payload,
            },
        )
    job_id = str(uuid.uuid4())
    initial_state = {
        "donor_id": donor,
        "tenant_id": tenant_id,
        "rag_namespace": preflight_payload.get("retrieval_namespace"),
        "donor_strategy": strategy,
        "input_context": input_payload,
        "generate_preflight": preflight,
        "strict_preflight": req.strict_preflight,
        "llm_mode": req.llm_mode,
        "hitl_checkpoints": list(req.hitl_checkpoints or []),
        "iteration_count": 0,
        "max_iterations": config.graph.max_iterations,
        "critic_score": 0.0,
        "needs_revision": False,
        "critic_notes": {},
        "critic_feedback_history": [],
        "hitl_pending": False,
        "errors": [],
    }
    normalize_state_contract(initial_state)

    _set_job(
        job_id,
        {
            "status": "accepted",
            "state": initial_state,
            "hitl_enabled": req.hitl_enabled,
            "webhook_url": webhook_url,
            "webhook_secret": webhook_secret,
            "client_metadata": client_metadata,
            "generate_preflight": preflight_payload,
            "strict_preflight": req.strict_preflight,
        },
    )
    _record_job_event(
        job_id,
        "generate_preflight_evaluated",
        tenant_id=preflight_payload.get("tenant_id"),
        risk_level=str(preflight_payload.get("risk_level") or "none"),
        grounding_risk_level=str(preflight_payload.get("grounding_risk_level") or "none"),
        warning_count=int(preflight_payload.get("warning_count") or 0),
        retrieval_namespace=preflight_payload.get("retrieval_namespace"),
        namespace_empty=bool(preflight_payload.get("namespace_empty")),
        grounding_policy_mode=str(grounding_policy.get("mode") or ""),
        grounding_policy_blocking=bool(grounding_policy.get("blocking")),
    )
    if req.hitl_enabled:
        background_tasks.add_task(_run_hitl_pipeline, job_id, initial_state, "start")
    else:
        background_tasks.add_task(_run_pipeline_to_completion, job_id, initial_state)
    return {"status": "accepted", "job_id": job_id, "preflight": preflight_payload}


@app.post("/cancel/{job_id}")
def cancel_job(job_id: str, request: Request):
    require_api_key_if_configured(request)
    job = _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    status = str(job.get("status") or "")
    if status == "canceled":
        return {"status": "canceled", "job_id": job_id, "already_canceled": True}
    if status in {"done", "error"}:
        raise HTTPException(status_code=409, detail=f"Job is already terminal: {status}")

    checkpoint_id = job.get("checkpoint_id")
    if checkpoint_id:
        checkpoint = hitl_manager.get_checkpoint(str(checkpoint_id))
        if checkpoint and checkpoint.get("status") == HITLStatus.PENDING:
            hitl_manager.cancel(str(checkpoint_id), "Canceled by user")

    _update_job(
        job_id,
        status="canceled",
        cancellation_reason="Canceled by user",
        canceled=True,
    )
    _record_job_event(job_id, "job_canceled", previous_status=status, reason="Canceled by user")
    return {"status": "canceled", "job_id": job_id, "previous_status": status}


@app.post("/resume/{job_id}")
async def resume_job(job_id: str, background_tasks: BackgroundTasks, request: Request):
    require_api_key_if_configured(request)
    job = _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.get("status") != "pending_hitl":
        raise HTTPException(status_code=409, detail="Job is not waiting for HITL review")

    checkpoint_id = job.get("checkpoint_id")
    if not checkpoint_id:
        raise HTTPException(status_code=409, detail="Checkpoint missing for pending HITL job")

    checkpoint = hitl_manager.get_checkpoint(checkpoint_id)
    if not checkpoint:
        raise HTTPException(status_code=404, detail="Checkpoint not found")
    if checkpoint.get("status") == HITLStatus.PENDING:
        raise HTTPException(status_code=409, detail="Checkpoint is still pending approval")

    state = job.get("state")
    if not isinstance(state, dict):
        raise HTTPException(status_code=409, detail="Job state is missing or invalid")

    _record_hitl_feedback_in_state(state, checkpoint)

    try:
        start_at = _resume_target_from_checkpoint(checkpoint, job.get("resume_from"))
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    _update_job(
        job_id,
        status="accepted",
        state=state,
        resume_from=start_at,
        checkpoint_status=getattr(checkpoint.get("status"), "value", checkpoint.get("status")),
    )
    _record_job_event(
        job_id,
        "resume_requested",
        checkpoint_id=str(checkpoint_id),
        checkpoint_status=getattr(checkpoint.get("status"), "value", checkpoint.get("status")),
        resuming_from=start_at,
    )
    background_tasks.add_task(_run_hitl_pipeline, job_id, state, start_at)
    return {
        "status": "accepted",
        "job_id": job_id,
        "resuming_from": start_at,
        "checkpoint_id": checkpoint_id,
        "checkpoint_status": getattr(checkpoint.get("status"), "value", checkpoint.get("status")),
    }


configure_status_read_router(
    require_api_key_if_configured=require_api_key_if_configured,
    get_job=_get_job,
    normalize_critic_fatal_flaws_for_job=_normalize_critic_fatal_flaws_for_job,
    ingest_inventory=_ingest_inventory,
    public_job_payload=public_job_payload,
    public_job_citations_payload=public_job_citations_payload,
    public_job_export_payload=public_job_export_payload,
    public_job_versions_payload=public_job_versions_payload,
    public_job_diff_payload=public_job_diff_payload,
    public_job_events_payload=public_job_events_payload,
    public_job_metrics_payload=public_job_metrics_payload,
    public_job_quality_payload=public_job_quality_payload,
    public_job_critic_payload=public_job_critic_payload,
)
app.include_router(status_read_router)

configure_review_workflow_read_router(
    require_api_key_if_configured=require_api_key_if_configured,
    normalize_critic_fatal_flaws_for_job=_normalize_critic_fatal_flaws_for_job,
    get_job=_get_job,
    normalize_review_comments_for_job=_normalize_review_comments_for_job,
    public_job_review_workflow_payload=public_job_review_workflow_payload,
    public_job_review_workflow_sla_payload=public_job_review_workflow_sla_payload,
    review_workflow_sla_profile_payload=_review_workflow_sla_profile_payload,
    portfolio_export_response=_portfolio_export_response,
    public_job_review_workflow_csv_text=public_job_review_workflow_csv_text,
    review_workflow_overdue_default_hours=REVIEW_WORKFLOW_OVERDUE_DEFAULT_HOURS,
    review_workflow_state_filter_values=REVIEW_WORKFLOW_STATE_FILTER_VALUES,
)
app.include_router(review_workflow_read_router)

configure_critic_write_router(
    require_api_key_if_configured=require_api_key_if_configured,
    set_critic_fatal_flaw_status=_set_critic_fatal_flaw_status,
    set_critic_fatal_flaws_status_bulk=_set_critic_fatal_flaws_status_bulk,
    finding_actor_from_request=_finding_actor_from_request,
)
app.include_router(critic_write_router)

configure_status_comments_read_router(
    require_api_key_if_configured=require_api_key_if_configured,
    normalize_critic_fatal_flaws_for_job=_normalize_critic_fatal_flaws_for_job,
    get_job=_get_job,
    normalize_review_comments_for_job=_normalize_review_comments_for_job,
    public_job_comments_payload=public_job_comments_payload,
)
app.include_router(status_comments_read_router)

configure_hitl_router(
    require_api_key_if_configured=require_api_key_if_configured,
    hitl_manager=hitl_manager,
    hitl_status_pending=HITLStatus.PENDING,
    public_checkpoint_payload=public_checkpoint_payload,
)
app.include_router(hitl_router)

@app.post(
    "/status/{job_id}/review/workflow/sla/recompute",
    response_model=JobReviewWorkflowSLARecomputePublicResponse,
    response_model_exclude_none=True,
)
def recompute_status_review_workflow_sla(
    job_id: str,
    request: Request,
    req: Optional[ReviewWorkflowSLARecomputeRequest] = None,
):
    require_api_key_if_configured(request)
    payload = req or ReviewWorkflowSLARecomputeRequest()
    return _recompute_review_workflow_sla(
        job_id,
        actor=_finding_actor_from_request(request),
        finding_sla_hours_override=payload.finding_sla_hours,
        default_comment_sla_hours=payload.default_comment_sla_hours,
        use_saved_profile=bool(payload.use_saved_profile),
    )


configure_comments_write_router(
    require_api_key_if_configured=require_api_key_if_configured,
    get_job=_get_job,
    job_draft_version_exists_for_section=_job_draft_version_exists_for_section,
    normalize_critic_fatal_flaws_for_job=_normalize_critic_fatal_flaws_for_job,
    find_critic_fatal_flaw=_find_critic_fatal_flaw,
    finding_primary_id=finding_primary_id,
    append_review_comment=_append_review_comment,
    set_review_comment_status=_set_review_comment_status,
    review_comment_sections=REVIEW_COMMENT_SECTIONS,
)
app.include_router(comments_write_router)

configure_ingest_router(
    require_api_key_if_configured=require_api_key_if_configured,
    resolve_tenant_id=_resolve_tenant_id,
    list_ingest_events=_list_ingest_events,
    ingest_inventory_fn=_ingest_inventory,
    portfolio_export_response=_portfolio_export_response,
    public_ingest_recent_payload=public_ingest_recent_payload,
    public_ingest_inventory_payload=public_ingest_inventory_payload,
    public_ingest_inventory_csv_text=public_ingest_inventory_csv_text,
    donor_get_strategy=DonorFactory.get_strategy,
    tenant_rag_namespace=_tenant_rag_namespace,
    vector_store_normalize_namespace=vector_store.normalize_namespace,
    ingest_pdf_to_namespace_fn=ingest_pdf_to_namespace,
    record_ingest_event=_record_ingest_event,
)
app.include_router(ingest_router)


@app.post("/export")
def export_artifacts(req: ExportRequest, request: Request):
    require_api_key_if_configured(request)
    grounding_gate = _extract_export_grounding_gate(req)
    if (
        not req.allow_unsafe_export
        and bool(grounding_gate.get("blocking"))
        and str(grounding_gate.get("mode") or "").lower() == "strict"
    ):
        raise HTTPException(
            status_code=409,
            detail={
                "reason": "grounding_gate_strict_block",
                "message": "Export blocked by strict grounding gate. Set allow_unsafe_export=true to override.",
                "grounding_gate": grounding_gate,
            },
        )
    toc_draft, logframe_draft, donor_id, citations, critic_findings, review_comments = _resolve_export_inputs(req)
    export_grounding_policy = _evaluate_export_grounding_policy(citations)
    if not req.allow_unsafe_export and bool(export_grounding_policy.get("blocking")):
        raise HTTPException(
            status_code=409,
            detail={
                "reason": "export_grounding_policy_block",
                "message": (
                    "Export blocked by strict export grounding policy "
                    "(architect claim support below configured threshold). "
                    "Set allow_unsafe_export=true to override."
                ),
                "export_grounding_policy": export_grounding_policy,
            },
        )
    fmt = (req.format or "").lower()

    try:
        docx_bytes: Optional[bytes] = None
        xlsx_bytes: Optional[bytes] = None

        if fmt in {"docx", "both"}:
            docx_bytes = build_docx_from_toc(
                toc_draft,
                donor_id,
                citations=citations,
                critic_findings=critic_findings,
                review_comments=review_comments,
            )

        if fmt in {"xlsx", "both"}:
            xlsx_bytes = build_xlsx_from_logframe(
                logframe_draft,
                donor_id,
                toc_draft=toc_draft,
                citations=citations,
                critic_findings=critic_findings,
                review_comments=review_comments,
            )

        if fmt == "docx" and docx_bytes is not None:
            return StreamingResponse(
                io.BytesIO(docx_bytes),
                media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                headers={"Content-Disposition": "attachment; filename=proposal.docx"},
            )

        if fmt == "xlsx" and xlsx_bytes is not None:
            return StreamingResponse(
                io.BytesIO(xlsx_bytes),
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": "attachment; filename=mel.xlsx"},
            )

        if fmt == "both" and docx_bytes is not None and xlsx_bytes is not None:
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.writestr("proposal.docx", docx_bytes)
                archive.writestr("mel.xlsx", xlsx_bytes)
            buf.seek(0)
            return StreamingResponse(
                buf,
                media_type="application/zip",
                headers={"Content-Disposition": "attachment; filename=grantflow_export.zip"},
            )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    raise HTTPException(status_code=400, detail="Unsupported format")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=config.api_host, port=config.api_port, reload=config.debug)
