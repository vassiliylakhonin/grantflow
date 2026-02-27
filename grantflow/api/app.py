from __future__ import annotations

import gzip
import io
import json
import tempfile
import uuid
import zipfile
from datetime import datetime, timezone
from typing import Any, Dict, Literal, Optional

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict

from grantflow.api.demo_ui import render_demo_ui_html
from grantflow.api.public_views import (
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
    public_job_review_workflow_payload,
    public_job_versions_payload,
    public_portfolio_metrics_csv_text,
    public_portfolio_metrics_payload,
    public_portfolio_quality_csv_text,
    public_portfolio_quality_payload,
)
from grantflow.api.schemas import (
    CriticFatalFlawPublicResponse,
    HITLPendingListPublicResponse,
    IngestInventoryPublicResponse,
    IngestRecentListPublicResponse,
    JobCitationsPublicResponse,
    JobCommentsPublicResponse,
    JobCriticPublicResponse,
    JobDiffPublicResponse,
    JobEventsPublicResponse,
    JobExportPayloadPublicResponse,
    JobMetricsPublicResponse,
    JobQualitySummaryPublicResponse,
    JobReviewWorkflowPublicResponse,
    JobStatusPublicResponse,
    JobVersionsPublicResponse,
    PortfolioMetricsPublicResponse,
    PortfolioQualityPublicResponse,
    ReviewCommentPublicResponse,
)
from grantflow.api.security import (
    api_key_configured,
    install_openapi_api_key_security,
    read_auth_required,
    require_api_key_if_configured,
)
from grantflow.api.webhooks import send_job_webhook_event
from grantflow.core.config import config
from grantflow.core.stores import create_ingest_audit_store_from_env, create_job_store_from_env
from grantflow.core.strategies.factory import DonorFactory
from grantflow.exporters.excel_builder import build_xlsx_from_logframe
from grantflow.exporters.word_builder import build_docx_from_toc
from grantflow.memory_bank.ingest import ingest_pdf_to_namespace
from grantflow.memory_bank.vector_store import vector_store
from grantflow.swarm.findings import finding_primary_id, normalize_findings
from grantflow.swarm.graph import grantflow_graph
from grantflow.swarm.hitl import HITLStatus, hitl_manager
from grantflow.swarm.retrieval_query import donor_query_preset_terms
from grantflow.swarm.state_contract import normalize_state_contract, state_donor_id

app = FastAPI(
    title="GrantFlow API",
    description="Enterprise-grade grant proposal automation",
    version="2.0.0",
)

JOB_STORE = create_job_store_from_env()
INGEST_AUDIT_STORE = create_ingest_audit_store_from_env()

HITLStartAt = Literal["start", "architect", "mel", "critic"]
TERMINAL_JOB_STATUSES = {"done", "error", "canceled"}
REVIEW_COMMENT_SECTIONS = {"toc", "logframe", "general"}
CRITIC_FINDING_STATUSES = {"open", "acknowledged", "resolved"}
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


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


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


def _list_ingest_events(*, donor_id: Optional[str] = None, limit: int = 50) -> list[Dict[str, Any]]:
    return INGEST_AUDIT_STORE.list_recent(donor_id=donor_id, limit=limit)


def _ingest_inventory(*, donor_id: Optional[str] = None) -> list[Dict[str, Any]]:
    inventory_fn = getattr(INGEST_AUDIT_STORE, "inventory", None)
    if callable(inventory_fn):
        rows = inventory_fn(donor_id=donor_id)
        return rows if isinstance(rows, list) else []
    # Fallback for older store implementations.
    rows = _list_ingest_events(donor_id=donor_id, limit=200)
    grouped: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        raw_metadata = row.get("metadata")
        metadata: Dict[str, Any] = raw_metadata if isinstance(raw_metadata, dict) else {}
        doc_family = str((metadata or {}).get("doc_family") or "").strip()
        donor = str(row.get("donor_id") or "").strip()
        if not doc_family:
            continue
        key = f"{donor.lower()}::{doc_family}"
        current = grouped.get(key)
        if current is None:
            grouped[key] = {
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
    rag_readiness = metadata.get("rag_readiness") if isinstance(metadata.get("rag_readiness"), dict) else {}
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
) -> Dict[str, Any]:
    namespace = str(getattr(strategy, "get_rag_collection", lambda: "")() or "").strip() or None
    inventory_rows = _ingest_inventory(donor_id=donor_id or None)
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
        "retrieval_namespace": namespace,
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
    llm_mode: bool = False
    hitl_enabled: bool = False
    strict_preflight: bool = False
    webhook_url: Optional[str] = None
    webhook_secret: Optional[str] = None
    client_metadata: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(extra="forbid")


class GeneratePreflightRequest(BaseModel):
    donor_id: str
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
    changed = normalized != raw_flaws

    if not changed:
        return job

    next_notes = dict(critic_notes)
    next_notes["fatal_flaws"] = normalized
    next_state = dict(state)
    next_state["critic_notes"] = next_notes
    next_state["critic_fatal_flaws"] = normalized
    return _update_job(job_id, state=next_state)


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
        current["id"] = current_finding_id
        current["finding_id"] = current_finding_id
        current_status = str(current.get("status") or "open")
        if current_status != next_status:
            current["status"] = next_status
            current["updated_at"] = now
            current["updated_by"] = actor_value
            if next_status == "acknowledged":
                current["acknowledged_at"] = current.get("acknowledged_at") or now
                current["acknowledged_by"] = actor_value
                current.pop("resolved_at", None)
                current.pop("resolved_by", None)
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


def _append_review_comment(
    job_id: str,
    *,
    section: str,
    message: str,
    author: Optional[str] = None,
    version_id: Optional[str] = None,
    linked_finding_id: Optional[str] = None,
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

    next_comments: list[Dict[str, Any]] = []
    for item in comments:
        cid = str(item.get("comment_id") or "")
        if cid != comment_id:
            next_comments.append(item)
            continue

        current = dict(item)
        current_status = str(current.get("status") or "open")
        if current_status != next_status:
            current["status"] = next_status
            current["updated_ts"] = _utcnow_iso()
            if next_status == "resolved":
                current["resolved_at"] = current["updated_ts"]
            elif "resolved_at" in current:
                current.pop("resolved_at", None)
            changed = True
        updated_comment = current
        next_comments.append(current)

    if updated_comment is None:
        raise HTTPException(status_code=404, detail="Comment not found")

    if changed:
        _update_job(job_id, review_comments=next_comments[-500:])
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
    if _job_is_canceled(job_id):
        return
    for key in RUNTIME_PIPELINE_STATE_KEYS:
        state.pop(key, None)
    state["hitl_pending"] = True
    normalize_state_contract(state)
    donor_id = state_donor_id(state, default="unknown")
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
    diagnostics: dict[str, Any] = {
        "job_store": {"mode": job_store_mode},
        "hitl_store": {"mode": hitl_store_mode},
        "ingest_store": {"mode": ingest_store_mode},
        "auth": {
            "api_key_configured": bool(api_key_configured()),
            "read_auth_required": bool(read_auth_required()),
        },
        "vector_store": {
            "backend": vector_backend,
            "collection_prefix": getattr(vector_store, "prefix", "grantflow"),
        },
        "preflight_grounding_policy": {
            "mode": _configured_preflight_grounding_policy_mode(),
            "thresholds": preflight_grounding_thresholds,
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


@app.get("/health")
def health_check():
    return {"status": "healthy", "version": "2.0.0", "diagnostics": _health_diagnostics()}


@app.get("/ready")
def readiness_check():
    vector_ready = _vector_store_readiness()
    ready = bool(vector_ready.get("ready"))
    preflight_grounding_thresholds = _preflight_grounding_policy_thresholds()
    payload = {
        "status": "ready" if ready else "degraded",
        "checks": {
            "vector_store": vector_ready,
            "preflight_grounding_policy": {
                "mode": _configured_preflight_grounding_policy_mode(),
                "thresholds": preflight_grounding_thresholds,
            },
        },
    }
    if not ready:
        raise HTTPException(status_code=503, detail=payload)
    return payload


@app.get("/donors")
def list_donors():
    return {"donors": DonorFactory.list_supported()}


@app.get("/demo", response_class=HTMLResponse, include_in_schema=False)
def demo_console():
    return HTMLResponse(render_demo_ui_html())


@app.get(
    "/portfolio/metrics",
    response_model=PortfolioMetricsPublicResponse,
    response_model_exclude_none=True,
)
def get_portfolio_metrics(
    request: Request,
    donor_id: Optional[str] = None,
    status: Optional[str] = None,
    hitl_enabled: Optional[bool] = Query(default=None),
    warning_level: Optional[str] = None,
    grounding_risk_level: Optional[str] = None,
):
    require_api_key_if_configured(request, for_read=True)
    jobs = _list_jobs()
    return public_portfolio_metrics_payload(
        jobs,
        donor_id=(donor_id or None),
        status=(status or None),
        hitl_enabled=hitl_enabled,
        warning_level=(warning_level or None),
        grounding_risk_level=(grounding_risk_level or None),
    )


@app.get("/portfolio/metrics/export")
def export_portfolio_metrics(
    request: Request,
    donor_id: Optional[str] = None,
    status: Optional[str] = None,
    hitl_enabled: Optional[bool] = Query(default=None),
    warning_level: Optional[str] = None,
    grounding_risk_level: Optional[str] = None,
    format: Literal["csv", "json"] = Query(default="csv"),
    gzip_enabled: bool = Query(default=False, alias="gzip"),
):
    require_api_key_if_configured(request, for_read=True)
    jobs = _list_jobs()
    payload = public_portfolio_metrics_payload(
        jobs,
        donor_id=(donor_id or None),
        status=(status or None),
        hitl_enabled=hitl_enabled,
        warning_level=(warning_level or None),
        grounding_risk_level=(grounding_risk_level or None),
    )

    return _portfolio_export_response(
        payload=payload,
        filename_prefix="grantflow_portfolio_metrics",
        donor_id=donor_id,
        status=status,
        hitl_enabled=hitl_enabled,
        export_format=format,
        gzip_enabled=gzip_enabled,
        csv_renderer=public_portfolio_metrics_csv_text,
    )


@app.get(
    "/portfolio/quality",
    response_model=PortfolioQualityPublicResponse,
    response_model_exclude_none=True,
)
def get_portfolio_quality(
    request: Request,
    donor_id: Optional[str] = None,
    status: Optional[str] = None,
    hitl_enabled: Optional[bool] = Query(default=None),
    warning_level: Optional[str] = None,
    grounding_risk_level: Optional[str] = None,
    finding_status: Optional[str] = None,
    finding_severity: Optional[str] = None,
):
    require_api_key_if_configured(request, for_read=True)
    jobs = _list_jobs()
    return public_portfolio_quality_payload(
        jobs,
        donor_id=(donor_id or None),
        status=(status or None),
        hitl_enabled=hitl_enabled,
        warning_level=(warning_level or None),
        grounding_risk_level=(grounding_risk_level or None),
        finding_status=(finding_status or None),
        finding_severity=(finding_severity or None),
    )


@app.get("/portfolio/quality/export")
def export_portfolio_quality(
    request: Request,
    donor_id: Optional[str] = None,
    status: Optional[str] = None,
    hitl_enabled: Optional[bool] = Query(default=None),
    warning_level: Optional[str] = None,
    grounding_risk_level: Optional[str] = None,
    finding_status: Optional[str] = None,
    finding_severity: Optional[str] = None,
    format: Literal["csv", "json"] = Query(default="csv"),
    gzip_enabled: bool = Query(default=False, alias="gzip"),
):
    require_api_key_if_configured(request, for_read=True)
    jobs = _list_jobs()
    payload = public_portfolio_quality_payload(
        jobs,
        donor_id=(donor_id or None),
        status=(status or None),
        hitl_enabled=hitl_enabled,
        warning_level=(warning_level or None),
        grounding_risk_level=(grounding_risk_level or None),
        finding_status=(finding_status or None),
        finding_severity=(finding_severity or None),
    )

    return _portfolio_export_response(
        payload=payload,
        filename_prefix="grantflow_portfolio_quality",
        donor_id=donor_id,
        status=status,
        hitl_enabled=hitl_enabled,
        export_format=format,
        gzip_enabled=gzip_enabled,
        csv_renderer=public_portfolio_quality_csv_text,
    )


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
    client_metadata = req.client_metadata if isinstance(req.client_metadata, dict) else None
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
    client_metadata = req.client_metadata if isinstance(req.client_metadata, dict) else None
    preflight = _build_generate_preflight(
        donor_id=donor,
        strategy=strategy,
        client_metadata=client_metadata,
    )
    grounding_policy = preflight.get("grounding_policy") if isinstance(preflight.get("grounding_policy"), dict) else {}
    if bool(grounding_policy.get("blocking")):
        raise HTTPException(
            status_code=409,
            detail={
                "reason": "preflight_grounding_policy_block",
                "message": "Generation blocked by strict grounding policy before pipeline start.",
                "preflight": preflight,
            },
        )
    preflight_risk_high = str(preflight.get("risk_level") or "").lower() == "high"
    grounding_risk_high = str(preflight.get("grounding_risk_level") or "").lower() == "high"
    if req.strict_preflight and str(preflight.get("risk_level") or "").lower() == "high":
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
                "preflight": preflight,
            },
        )
    if req.strict_preflight and grounding_risk_high:
        raise HTTPException(
            status_code=409,
            detail={
                "reason": "preflight_high_risk_block",
                "message": "Generation blocked by strict_preflight because predicted grounding risk is high.",
                "strict_reasons": ["grounding_risk_high"],
                "preflight": preflight,
            },
        )
    job_id = str(uuid.uuid4())
    initial_state = {
        "donor_id": donor,
        "donor_strategy": strategy,
        "input_context": input_payload,
        "generate_preflight": preflight,
        "strict_preflight": req.strict_preflight,
        "llm_mode": req.llm_mode,
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
            "generate_preflight": preflight,
            "strict_preflight": req.strict_preflight,
        },
    )
    _record_job_event(
        job_id,
        "generate_preflight_evaluated",
        risk_level=str(preflight.get("risk_level") or "none"),
        grounding_risk_level=str(preflight.get("grounding_risk_level") or "none"),
        warning_count=int(preflight.get("warning_count") or 0),
        retrieval_namespace=preflight.get("retrieval_namespace"),
        namespace_empty=bool(preflight.get("namespace_empty")),
        grounding_policy_mode=str(grounding_policy.get("mode") or ""),
        grounding_policy_blocking=bool(grounding_policy.get("blocking")),
    )
    if req.hitl_enabled:
        background_tasks.add_task(_run_hitl_pipeline, job_id, initial_state, "start")
    else:
        background_tasks.add_task(_run_pipeline_to_completion, job_id, initial_state)
    return {"status": "accepted", "job_id": job_id, "preflight": preflight}


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


@app.get("/status/{job_id}", response_model=JobStatusPublicResponse, response_model_exclude_none=True)
def get_status(job_id: str, request: Request):
    require_api_key_if_configured(request, for_read=True)
    job = _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return public_job_payload(job)


@app.get(
    "/status/{job_id}/citations",
    response_model=JobCitationsPublicResponse,
    response_model_exclude_none=True,
)
def get_status_citations(job_id: str, request: Request):
    require_api_key_if_configured(request, for_read=True)
    job = _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return public_job_citations_payload(job_id, job)


@app.get(
    "/status/{job_id}/export-payload",
    response_model=JobExportPayloadPublicResponse,
    response_model_exclude_none=True,
)
def get_status_export_payload(job_id: str, request: Request):
    require_api_key_if_configured(request, for_read=True)
    job = _normalize_critic_fatal_flaws_for_job(job_id) or _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    state = job.get("state")
    state_dict = state if isinstance(state, dict) else {}
    donor = str(
        state_dict.get("donor_id")
        or state_dict.get("donor")
        or ((job.get("client_metadata") or {}) if isinstance(job.get("client_metadata"), dict) else {}).get("donor_id")
        or ""
    ).strip()
    inventory_rows = _ingest_inventory(donor_id=donor or None)
    return public_job_export_payload(job_id, job, ingest_inventory_rows=inventory_rows)


@app.get(
    "/status/{job_id}/versions",
    response_model=JobVersionsPublicResponse,
    response_model_exclude_none=True,
)
def get_status_versions(job_id: str, request: Request, section: Optional[str] = None):
    require_api_key_if_configured(request, for_read=True)
    job = _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return public_job_versions_payload(job_id, job, section=section)


@app.get(
    "/status/{job_id}/diff",
    response_model=JobDiffPublicResponse,
    response_model_exclude_none=True,
)
def get_status_diff(
    job_id: str,
    request: Request,
    section: Optional[str] = None,
    from_version_id: Optional[str] = Query(default=None),
    to_version_id: Optional[str] = Query(default=None),
):
    require_api_key_if_configured(request, for_read=True)
    job = _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return public_job_diff_payload(
        job_id,
        job,
        section=section,
        from_version_id=from_version_id,
        to_version_id=to_version_id,
    )


@app.get(
    "/status/{job_id}/events",
    response_model=JobEventsPublicResponse,
    response_model_exclude_none=True,
)
def get_status_events(job_id: str, request: Request):
    require_api_key_if_configured(request, for_read=True)
    job = _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return public_job_events_payload(job_id, job)


@app.get(
    "/status/{job_id}/metrics",
    response_model=JobMetricsPublicResponse,
    response_model_exclude_none=True,
)
def get_status_metrics(job_id: str, request: Request):
    require_api_key_if_configured(request, for_read=True)
    job = _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return public_job_metrics_payload(job_id, job)


@app.get(
    "/status/{job_id}/quality",
    response_model=JobQualitySummaryPublicResponse,
    response_model_exclude_none=True,
)
def get_status_quality(job_id: str, request: Request):
    require_api_key_if_configured(request, for_read=True)
    job = _normalize_critic_fatal_flaws_for_job(job_id) or _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    state = job.get("state")
    state_dict = state if isinstance(state, dict) else {}
    donor = str(
        state_dict.get("donor_id")
        or state_dict.get("donor")
        or ((job.get("client_metadata") or {}) if isinstance(job.get("client_metadata"), dict) else {}).get("donor_id")
        or ""
    ).strip()
    inventory_rows = _ingest_inventory(donor_id=donor or None)
    return public_job_quality_payload(job_id, job, ingest_inventory_rows=inventory_rows)


@app.get(
    "/status/{job_id}/critic",
    response_model=JobCriticPublicResponse,
    response_model_exclude_none=True,
)
def get_status_critic(job_id: str, request: Request):
    require_api_key_if_configured(request, for_read=True)
    job = _normalize_critic_fatal_flaws_for_job(job_id) or _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return public_job_critic_payload(job_id, job)


@app.post(
    "/status/{job_id}/critic/findings/{finding_id}/ack",
    response_model=CriticFatalFlawPublicResponse,
    response_model_exclude_none=True,
)
def acknowledge_status_critic_finding(job_id: str, finding_id: str, request: Request):
    require_api_key_if_configured(request)
    return _set_critic_fatal_flaw_status(
        job_id,
        finding_id=finding_id,
        next_status="acknowledged",
        actor=_finding_actor_from_request(request),
    )


@app.post(
    "/status/{job_id}/critic/findings/{finding_id}/open",
    response_model=CriticFatalFlawPublicResponse,
    response_model_exclude_none=True,
)
def reopen_status_critic_finding(job_id: str, finding_id: str, request: Request):
    require_api_key_if_configured(request)
    return _set_critic_fatal_flaw_status(
        job_id,
        finding_id=finding_id,
        next_status="open",
        actor=_finding_actor_from_request(request),
    )


@app.post(
    "/status/{job_id}/critic/findings/{finding_id}/resolve",
    response_model=CriticFatalFlawPublicResponse,
    response_model_exclude_none=True,
)
def resolve_status_critic_finding(job_id: str, finding_id: str, request: Request):
    require_api_key_if_configured(request)
    return _set_critic_fatal_flaw_status(
        job_id,
        finding_id=finding_id,
        next_status="resolved",
        actor=_finding_actor_from_request(request),
    )


@app.get(
    "/status/{job_id}/comments",
    response_model=JobCommentsPublicResponse,
    response_model_exclude_none=True,
)
def get_status_comments(
    job_id: str,
    request: Request,
    section: Optional[str] = None,
    comment_status: Optional[str] = Query(default=None, alias="status"),
    version_id: Optional[str] = None,
):
    require_api_key_if_configured(request, for_read=True)
    job = _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return public_job_comments_payload(
        job_id,
        job,
        section=section,
        comment_status=comment_status,
        version_id=version_id,
    )


@app.get(
    "/status/{job_id}/review/workflow",
    response_model=JobReviewWorkflowPublicResponse,
    response_model_exclude_none=True,
)
def get_status_review_workflow(job_id: str, request: Request):
    require_api_key_if_configured(request, for_read=True)
    job = _normalize_critic_fatal_flaws_for_job(job_id) or _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return public_job_review_workflow_payload(job_id, job)


@app.post(
    "/status/{job_id}/comments",
    response_model=ReviewCommentPublicResponse,
    response_model_exclude_none=True,
)
def add_status_comment(job_id: str, req: JobCommentCreateRequest, request: Request):
    require_api_key_if_configured(request)
    job = _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    section = (req.section or "").strip().lower()
    if section not in REVIEW_COMMENT_SECTIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported section: {section or req.section}")

    message = (req.message or "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="Missing comment message")
    if len(message) > 4000:
        raise HTTPException(status_code=400, detail="Comment message is too long")

    author = (req.author or "").strip() or None
    version_id = (req.version_id or "").strip() or None
    linked_finding_id = (req.linked_finding_id or "").strip() or None
    if version_id and not _job_draft_version_exists_for_section(job, section=section, version_id=version_id):
        raise HTTPException(status_code=400, detail="Unknown version_id for requested section")
    if linked_finding_id:
        normalized_job = _normalize_critic_fatal_flaws_for_job(job_id) or _get_job(job_id)
        if not normalized_job:
            raise HTTPException(status_code=404, detail="Job not found")
        finding = _find_critic_fatal_flaw(normalized_job, linked_finding_id)
        if not finding:
            raise HTTPException(status_code=400, detail="Unknown linked_finding_id")
        linked_finding_id = finding_primary_id(finding) or linked_finding_id
        finding_section = str(finding.get("section") or "")
        if section != "general" and finding_section and section != finding_section:
            raise HTTPException(status_code=400, detail="linked_finding_id section does not match comment section")

    return _append_review_comment(
        job_id,
        section=section,
        message=message,
        author=author,
        version_id=version_id,
        linked_finding_id=linked_finding_id,
    )


@app.post(
    "/status/{job_id}/comments/{comment_id}/resolve",
    response_model=ReviewCommentPublicResponse,
    response_model_exclude_none=True,
)
def resolve_status_comment(job_id: str, comment_id: str, request: Request):
    require_api_key_if_configured(request)
    return _set_review_comment_status(job_id, comment_id=comment_id, next_status="resolved")


@app.post(
    "/status/{job_id}/comments/{comment_id}/reopen",
    response_model=ReviewCommentPublicResponse,
    response_model_exclude_none=True,
)
def reopen_status_comment(job_id: str, comment_id: str, request: Request):
    require_api_key_if_configured(request)
    return _set_review_comment_status(job_id, comment_id=comment_id, next_status="open")


@app.post("/hitl/approve")
def approve_checkpoint(req: HITLApprovalRequest, request: Request):
    require_api_key_if_configured(request)
    checkpoint = hitl_manager.get_checkpoint(req.checkpoint_id)
    if not checkpoint:
        raise HTTPException(status_code=404, detail="Checkpoint not found")

    if req.approved:
        hitl_manager.approve(req.checkpoint_id, req.feedback)
        return {"status": "approved", "checkpoint_id": req.checkpoint_id}

    hitl_manager.reject(req.checkpoint_id, req.feedback or "Rejected")
    return {"status": "rejected", "checkpoint_id": req.checkpoint_id}


@app.get("/hitl/pending", response_model=HITLPendingListPublicResponse, response_model_exclude_none=True)
def list_pending_hitl(request: Request, donor_id: Optional[str] = None):
    require_api_key_if_configured(request, for_read=True)
    pending = hitl_manager.list_pending(donor_id)
    return {
        "pending_count": len(pending),
        "checkpoints": [public_checkpoint_payload(cp) for cp in pending],
    }


@app.get("/ingest/recent", response_model=IngestRecentListPublicResponse, response_model_exclude_none=True)
def list_recent_ingests(
    request: Request,
    donor_id: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
):
    require_api_key_if_configured(request, for_read=True)
    rows = _list_ingest_events(donor_id=donor_id, limit=limit)
    return public_ingest_recent_payload(rows, donor_id=(donor_id or None))


@app.get("/ingest/inventory", response_model=IngestInventoryPublicResponse, response_model_exclude_none=True)
def get_ingest_inventory(
    request: Request,
    donor_id: Optional[str] = Query(default=None),
):
    require_api_key_if_configured(request, for_read=True)
    rows = _ingest_inventory(donor_id=donor_id)
    return public_ingest_inventory_payload(rows, donor_id=(donor_id or None))


@app.get("/ingest/inventory/export")
def export_ingest_inventory(
    request: Request,
    donor_id: Optional[str] = None,
    format: Literal["csv", "json"] = Query(default="csv"),
    gzip_enabled: bool = Query(default=False, alias="gzip"),
):
    require_api_key_if_configured(request, for_read=True)
    rows = _ingest_inventory(donor_id=donor_id)
    payload = public_ingest_inventory_payload(rows, donor_id=(donor_id or None))
    return _portfolio_export_response(
        payload=payload,
        filename_prefix="grantflow_ingest_inventory",
        donor_id=donor_id,
        status=None,
        hitl_enabled=None,
        export_format=format,
        gzip_enabled=gzip_enabled,
        csv_renderer=public_ingest_inventory_csv_text,
    )


@app.post("/ingest")
async def ingest_pdf(
    request: Request,
    donor_id: str = Form(...),
    file: UploadFile = File(...),
    metadata_json: Optional[str] = Form(None),
):
    require_api_key_if_configured(request)

    donor = (donor_id or "").strip()
    if not donor:
        raise HTTPException(status_code=400, detail="Missing donor_id")

    try:
        strategy = DonorFactory.get_strategy(donor)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    filename = (file.filename or "").strip()
    if not filename:
        raise HTTPException(status_code=400, detail="Missing uploaded file name")
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF uploads are supported")

    content_type = (file.content_type or "").lower().strip()
    allowed_content_types = {"", "application/pdf", "application/x-pdf", "application/octet-stream"}
    if content_type not in allowed_content_types:
        raise HTTPException(status_code=400, detail=f"Unsupported content type: {content_type}")

    metadata: Optional[Dict[str, Any]] = None
    if metadata_json:
        try:
            parsed = json.loads(metadata_json)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail=f"Invalid metadata_json: {exc.msg}") from exc
        if not isinstance(parsed, dict):
            raise HTTPException(status_code=400, detail="metadata_json must decode to an object")
        metadata = parsed

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    namespace = strategy.get_rag_collection()
    upload_metadata: Dict[str, Any] = {
        "uploaded_filename": filename,
        "uploaded_content_type": content_type or "application/pdf",
        "donor_id": donor,
    }
    if metadata:
        upload_metadata.update(metadata)

    tmp_path: Optional[str] = None
    try:
        with tempfile.NamedTemporaryFile(prefix="grantflow_ingest_", suffix=".pdf", delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        result = ingest_pdf_to_namespace(tmp_path, namespace=namespace, metadata=upload_metadata)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Ingest failed: {exc}") from exc
    finally:
        if tmp_path:
            try:
                import os

                os.unlink(tmp_path)
            except FileNotFoundError:
                pass

    result_payload = result if isinstance(result, dict) else {"raw_result": str(result)}
    _record_ingest_event(
        donor_id=donor,
        namespace=namespace,
        filename=filename,
        content_type=content_type or "application/pdf",
        metadata=upload_metadata,
        result=result_payload,
    )

    return {
        "status": "ingested",
        "donor_id": donor,
        "namespace": namespace,
        "filename": filename,
        "result": result_payload,
    }


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
