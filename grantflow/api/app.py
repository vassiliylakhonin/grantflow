from __future__ import annotations

import gzip
import io
import json
import os
import re
import tempfile
import threading
import uuid
import zipfile
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Any, AsyncIterator, Callable, Dict, Literal, Optional

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict

from grantflow.api.demo_ui import render_demo_ui_html
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
    public_job_grounding_gate_payload,
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
from grantflow.api.schemas import (
    CriticFindingsBulkStatusPublicResponse,
    CriticFindingsListPublicResponse,
    CriticFatalFlawPublicResponse,
    CriticFatalFlawStatusUpdatePublicResponse,
    GeneratePreflightPublicResponse,
    HITLPendingListPublicResponse,
    IngestInventoryPublicResponse,
    IngestRecentListPublicResponse,
    JobCitationsPublicResponse,
    JobCommentsPublicResponse,
    JobCriticPublicResponse,
    JobDiffPublicResponse,
    JobEventsPublicResponse,
    JobExportPayloadPublicResponse,
    JobGroundingGatePublicResponse,
    JobHITLHistoryPublicResponse,
    JobMetricsPublicResponse,
    JobQualitySummaryPublicResponse,
    JobReviewWorkflowPublicResponse,
    JobReviewWorkflowSLAProfilePublicResponse,
    JobReviewWorkflowSLARecomputePublicResponse,
    JobReviewWorkflowSLAPublicResponse,
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
from grantflow.core.job_runner import InMemoryJobRunner
from grantflow.core.stores import create_ingest_audit_store_from_env, create_job_store_from_env
from grantflow.core.strategies.factory import DonorFactory
from grantflow.core.version import __version__
from grantflow.exporters.donor_contracts import evaluate_export_contract_gate, normalize_export_contract_policy_mode
from grantflow.exporters.excel_builder import build_xlsx_from_logframe
from grantflow.exporters.word_builder import build_docx_from_toc
from grantflow.memory_bank.ingest import ingest_pdf_to_namespace
from grantflow.memory_bank.vector_store import vector_store
from grantflow.swarm.findings import (
    canonicalize_findings,
    finding_primary_id,
    state_critic_findings,
    write_state_critic_findings,
)
from grantflow.swarm.graph import grantflow_graph
from grantflow.swarm.hitl import HITLStatus, hitl_manager
from grantflow.swarm.nodes.architect_generation import generate_toc_under_contract
from grantflow.swarm.nodes.architect_retrieval import retrieve_architect_evidence
from grantflow.swarm.retrieval_query import donor_query_preset_list
from grantflow.swarm.citations import (
    citation_traceability_status,
    is_non_retrieval_citation_type,
    is_retrieval_grounded_citation_type,
)
from grantflow.swarm.state_contract import (
    build_graph_state,
    normalize_rag_namespace,
    normalize_state_contract,
    normalized_state_copy,
    state_donor_id,
)

JOB_STORE = create_job_store_from_env()
INGEST_AUDIT_STORE = create_ingest_audit_store_from_env()
JOB_RUNNER = InMemoryJobRunner(
    worker_count=int(getattr(config.job_runner, "worker_count", 2) or 2),
    queue_maxsize=int(getattr(config.job_runner, "queue_maxsize", 200) or 200),
)

HITLStartAt = Literal["start", "architect", "mel", "critic"]
TERMINAL_JOB_STATUSES = {"done", "error", "canceled"}
REVIEW_COMMENT_SECTIONS = {"toc", "logframe", "general"}
CRITIC_FINDING_STATUSES = {"open", "acknowledged", "resolved"}
CRITIC_FINDING_SLA_HOURS = {"high": 24, "medium": 72, "low": 120}
REVIEW_COMMENT_DEFAULT_SLA_HOURS = 72
REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{1,120}$")
MAX_IDEMPOTENCY_RECORDS = 300
MAX_GLOBAL_IDEMPOTENCY_RECORDS = 1000
JOB_RUNNER_MODES = {"background_tasks", "inmemory_queue"}
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
PREFLIGHT_CRITICAL_DOC_FAMILY_MIN_UPLOADS: dict[str, int] = {
    "donor_policy": 2,
    "compliance_requirements": 2,
    "eligibility_rules": 2,
}
GROUNDING_POLICY_MODES = {"off", "warn", "strict"}
TENANT_HEADER = "x-tenant-id"
HITL_HISTORY_EVENT_TYPES = {
    "status_changed",
    "resume_requested",
    "hitl_checkpoint_published",
    "hitl_checkpoint_decision",
    "hitl_checkpoint_canceled",
}
GLOBAL_IDEMPOTENCY_RECORDS: Dict[str, Dict[str, Any]] = {}
GLOBAL_IDEMPOTENCY_LOCK = threading.Lock()


def _job_runner_mode() -> str:
    raw_mode = str(getattr(config.job_runner, "mode", "background_tasks") or "background_tasks").strip().lower()
    if raw_mode not in JOB_RUNNER_MODES:
        return "background_tasks"
    return raw_mode


def _uses_inmemory_queue_runner() -> bool:
    return _job_runner_mode() == "inmemory_queue"


def _job_store_mode() -> str:
    return "sqlite" if getattr(JOB_STORE, "db_path", None) else "inmem"


def _hitl_store_mode() -> str:
    return "sqlite" if bool(getattr(hitl_manager, "_use_sqlite", False)) else "inmem"


def _ingest_store_mode() -> str:
    return "sqlite" if getattr(INGEST_AUDIT_STORE, "db_path", None) else "inmem"


def _validate_store_backend_alignment() -> None:
    job_store_mode = _job_store_mode()
    hitl_store_mode = _hitl_store_mode()
    if job_store_mode == hitl_store_mode:
        return
    raise RuntimeError(
        "Store backend mismatch: "
        f"JOB_STORE={job_store_mode} while HITL_STORE={hitl_store_mode}. "
        "Use matching backends for GRANTFLOW_JOB_STORE and GRANTFLOW_HITL_STORE."
    )


@asynccontextmanager
async def _app_lifespan(_: FastAPI) -> AsyncIterator[None]:
    _validate_store_backend_alignment()
    if _uses_inmemory_queue_runner():
        JOB_RUNNER.start()
    try:
        yield
    finally:
        if _uses_inmemory_queue_runner():
            JOB_RUNNER.stop()


app = FastAPI(
    title="GrantFlow API",
    description="Enterprise-grade grant proposal automation",
    version=__version__,
    lifespan=_app_lifespan,
)


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _dispatch_pipeline_task(background_tasks: BackgroundTasks, fn: Callable[..., None], *args: Any) -> str:
    if _uses_inmemory_queue_runner():
        accepted = JOB_RUNNER.submit(fn, *args)
        if not accepted:
            raise HTTPException(status_code=503, detail="Job queue is full. Retry shortly.")
        return "inmemory_queue"
    background_tasks.add_task(fn, *args)
    return "background_tasks"


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


def _normalize_request_id(value: Any) -> Optional[str]:
    token = str(value or "").strip()
    if not token:
        return None
    if not REQUEST_ID_RE.fullmatch(token):
        raise HTTPException(
            status_code=400,
            detail="Invalid request_id (allowed: letters, numbers, ., _, :, -, length 1..120)",
        )
    return token


def _resolve_request_id(request: Request, explicit_request_id: Optional[str] = None) -> Optional[str]:
    return _normalize_request_id(explicit_request_id) or _normalize_request_id(request.headers.get("x-request-id"))


def _idempotency_fingerprint(payload: Dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _idempotency_record_key(scope: str, request_id: str) -> str:
    return f"{scope}:{request_id}"


def _idempotency_records(job: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    raw = job.get("idempotency_records")
    if not isinstance(raw, dict):
        return {}
    out: Dict[str, Dict[str, Any]] = {}
    for key, value in raw.items():
        if not isinstance(key, str) or not isinstance(value, dict):
            continue
        out[key] = dict(value)
    return out


def _idempotency_replay_response(
    job: Dict[str, Any],
    *,
    scope: str,
    request_id: Optional[str],
    fingerprint: str,
) -> Optional[Dict[str, Any]]:
    token = _normalize_request_id(request_id)
    if not token:
        return None
    key = _idempotency_record_key(scope, token)
    record = _idempotency_records(job).get(key)
    if not isinstance(record, dict):
        return None
    record_fingerprint = str(record.get("fingerprint") or "")
    if record_fingerprint and record_fingerprint != fingerprint:
        raise HTTPException(
            status_code=409,
            detail={
                "reason": "request_id_reused_with_different_payload",
                "message": "request_id is already used for a different action payload.",
                "request_id": token,
                "scope": scope,
            },
        )
    response_payload = record.get("response")
    if isinstance(response_payload, dict):
        replay = dict(response_payload)
    else:
        replay = {}
    replay["request_id"] = token
    replay["idempotent_replay"] = True
    replay["persisted"] = bool(record.get("persisted", True))
    return replay


def _store_idempotency_response(
    job_id: str,
    *,
    scope: str,
    request_id: Optional[str],
    fingerprint: str,
    response: Dict[str, Any],
    persisted: bool,
) -> None:
    token = _normalize_request_id(request_id)
    if not token:
        return
    job = _get_job(job_id)
    if not job:
        return
    records = _idempotency_records(job)
    key = _idempotency_record_key(scope, token)
    stored_response = dict(response)
    stored_response.pop("idempotent_replay", None)
    stored_response["request_id"] = token
    records[key] = {
        "scope": scope,
        "request_id": token,
        "fingerprint": fingerprint,
        "persisted": bool(persisted),
        "ts": _utcnow_iso(),
        "response": stored_response,
    }
    while len(records) > MAX_IDEMPOTENCY_RECORDS:
        oldest_key = next(iter(records))
        records.pop(oldest_key, None)
    _update_job(job_id, idempotency_records=records)


def _global_idempotency_record_key(scope: str, request_id: str) -> str:
    return f"{scope}:{request_id}"


def _global_idempotency_replay_response(
    *,
    scope: str,
    request_id: Optional[str],
    fingerprint: str,
) -> Optional[Dict[str, Any]]:
    token = _normalize_request_id(request_id)
    if not token:
        return None
    key = _global_idempotency_record_key(scope, token)
    with GLOBAL_IDEMPOTENCY_LOCK:
        record = dict(GLOBAL_IDEMPOTENCY_RECORDS.get(key) or {})
    if not record:
        return None
    record_fingerprint = str(record.get("fingerprint") or "")
    if record_fingerprint and record_fingerprint != fingerprint:
        raise HTTPException(
            status_code=409,
            detail={
                "reason": "request_id_reused_with_different_payload",
                "message": "request_id is already used for a different action payload.",
                "request_id": token,
                "scope": scope,
            },
        )
    response_payload = record.get("response")
    if isinstance(response_payload, dict):
        replay = dict(response_payload)
    else:
        replay = {}
    replay["request_id"] = token
    replay["idempotent_replay"] = True
    replay["persisted"] = bool(record.get("persisted", True))
    return replay


def _store_global_idempotency_response(
    *,
    scope: str,
    request_id: Optional[str],
    fingerprint: str,
    response: Dict[str, Any],
    persisted: bool,
) -> None:
    token = _normalize_request_id(request_id)
    if not token:
        return
    key = _global_idempotency_record_key(scope, token)
    stored_response = dict(response)
    stored_response.pop("idempotent_replay", None)
    stored_response["request_id"] = token
    with GLOBAL_IDEMPOTENCY_LOCK:
        GLOBAL_IDEMPOTENCY_RECORDS[key] = {
            "scope": scope,
            "request_id": token,
            "fingerprint": fingerprint,
            "persisted": bool(persisted),
            "ts": _utcnow_iso(),
            "response": stored_response,
        }
        while len(GLOBAL_IDEMPOTENCY_RECORDS) > MAX_GLOBAL_IDEMPOTENCY_RECORDS:
            oldest_key = next(iter(GLOBAL_IDEMPOTENCY_RECORDS))
            GLOBAL_IDEMPOTENCY_RECORDS.pop(oldest_key, None)


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
    request_id = _normalize_request_id(fields.get("request_id"))
    if request_id:
        for row in reversed(events):
            if not isinstance(row, dict):
                continue
            if str(row.get("type") or "") != event_type:
                continue
            if str(row.get("request_id") or "") != request_id:
                continue
            return
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
    base = normalize_rag_namespace(base_namespace) or "default"
    tenant = normalize_rag_namespace(tenant_id)
    if not tenant:
        return base
    return normalize_rag_namespace(f"{tenant}/{base}") or f"{tenant}/{base}"


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


def _configured_export_require_grounded_gate_pass() -> bool:
    return bool(getattr(config.graph, "export_require_grounded_gate_pass", False))


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


def _configured_export_contract_policy_mode() -> str:
    contract_mode = getattr(config.graph, "export_contract_policy_mode", None)
    if str(contract_mode or "").strip():
        return normalize_export_contract_policy_mode(contract_mode)
    return _configured_export_grounding_policy_mode()


def _evaluate_export_contract_gate(
    *,
    donor_id: str,
    toc_draft: dict[str, Any],
    workbook_sheetnames: Optional[list[str]] = None,
) -> Dict[str, Any]:
    return evaluate_export_contract_gate(
        donor_id=donor_id,
        toc_payload=toc_draft,
        policy_mode=_configured_export_contract_policy_mode(),
        workbook_sheetnames=workbook_sheetnames,
    )


def _attach_export_contract_gate(state: Any) -> Dict[str, Any]:
    state_dict: dict[str, Any] = state if isinstance(state, dict) else {}
    donor_id = state_donor_id(state_dict, default="grantflow")
    raw_toc = state_dict.get("toc_draft")
    toc_draft = raw_toc if isinstance(raw_toc, dict) else {}
    if not toc_draft:
        raw_toc_fallback = state_dict.get("toc")
        if isinstance(raw_toc_fallback, dict):
            toc_draft = raw_toc_fallback
    gate = _evaluate_export_contract_gate(donor_id=donor_id, toc_draft=toc_draft)
    state_dict["export_contract_gate"] = gate
    return gate


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
        if isinstance(c, dict)
        and str(c.get("used_for") or "") == "toc_claim"
        and str(c.get("statement_path") or "").strip()
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
    traceability_partial_count = sum(
        1 for c in architect_claim_citations if citation_traceability_status(c) == "partial"
    )
    traceability_missing_count = sum(
        1 for c in architect_claim_citations if citation_traceability_status(c) == "missing"
    )
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
        key_claim_coverage_ratio = (
            round(float(key_claim_coverage_ratio), 4) if key_claim_coverage_ratio is not None else None
        )
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
        "retrieval_hits_count": (
            int(retrieval_summary.get("hits_count") or 0) if isinstance(retrieval_summary, dict) else 0
        ),
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


def _set_job(job_id: str, payload: Dict[str, Any]) -> None:
    previous = JOB_STORE.get(job_id)
    next_payload = dict(payload)

    if previous and previous.get("status") == "canceled" and next_payload.get("status") != "canceled":
        return

    for key in (
        "webhook_url",
        "webhook_secret",
        "client_metadata",
        "generate_preflight",
        "strict_preflight",
        "idempotency_records",
    ):
        if key not in next_payload and previous and key in previous:
            next_payload[key] = previous.get(key)

    next_payload = _append_job_event_records(previous, next_payload)
    JOB_STORE.set(job_id, next_payload)
    _dispatch_job_webhook_for_status_change(job_id, previous, next_payload)


def _update_job(job_id: str, **patch: Any) -> Dict[str, Any]:
    previous = JOB_STORE.get(job_id)
    if previous and previous.get("status") == "canceled" and "status" in patch and patch.get("status") != "canceled":
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


def _find_job_by_checkpoint_id(checkpoint_id: str) -> tuple[Optional[str], Optional[Dict[str, Any]]]:
    token = str(checkpoint_id or "").strip()
    if not token:
        return None, None
    for job_id, job in _list_jobs().items():
        if not isinstance(job, dict):
            continue
        if str(job.get("checkpoint_id") or "").strip() == token:
            return str(job_id), job
    return None, None


def _is_hitl_history_event(event: Dict[str, Any]) -> bool:
    event_type = str(event.get("type") or "").strip()
    if event_type not in HITL_HISTORY_EVENT_TYPES:
        return False
    if event_type != "status_changed":
        return True
    from_status = str(event.get("from_status") or "").strip().lower()
    to_status = str(event.get("to_status") or "").strip().lower()
    return from_status == "pending_hitl" or to_status == "pending_hitl"


def _hitl_history_payload(
    job_id: str,
    job: Dict[str, Any],
    *,
    event_type: Optional[str] = None,
    checkpoint_id: Optional[str] = None,
) -> Dict[str, Any]:
    event_type_filter = str(event_type or "").strip() or None
    if event_type_filter and event_type_filter not in HITL_HISTORY_EVENT_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported event_type filter")
    checkpoint_filter = str(checkpoint_id or "").strip() or None
    raw_events_value = job.get("job_events")
    raw_events: list[Any] = raw_events_value if isinstance(raw_events_value, list) else []
    events: list[Dict[str, Any]] = []
    for row in raw_events:
        if not isinstance(row, dict) or not _is_hitl_history_event(row):
            continue
        row_type = str(row.get("type") or "").strip()
        row_checkpoint_id = str(row.get("checkpoint_id") or "").strip() or None
        if event_type_filter and row_type != event_type_filter:
            continue
        if checkpoint_filter and row_checkpoint_id != checkpoint_filter:
            continue
        status = str(row.get("status") or "").strip()
        from_status = str(row.get("from_status") or "").strip()
        to_status = str(row.get("to_status") or "").strip()
        event: Dict[str, Any] = {
            "event_id": row.get("event_id"),
            "ts": row.get("ts"),
            "type": row_type,
            "from_status": from_status or None,
            "to_status": to_status or None,
            "status": status or None,
            "checkpoint_id": row_checkpoint_id,
            "checkpoint_stage": str(row.get("checkpoint_stage") or row.get("stage") or "").strip() or None,
            "checkpoint_status": str(row.get("checkpoint_status") or "").strip() or None,
            "resuming_from": str(row.get("resuming_from") or "").strip() or None,
            "approved": row.get("approved") if isinstance(row.get("approved"), bool) else None,
            "feedback": str(row.get("feedback") or "").strip() or None,
            "actor": str(row.get("actor") or "").strip() or None,
            "request_id": str(row.get("request_id") or "").strip() or None,
            "reason": str(row.get("reason") or "").strip() or None,
            "backend": str(row.get("backend") or "").strip() or None,
        }
        events.append(event)
    events.sort(key=lambda item: str(item.get("ts") or ""), reverse=True)
    event_type_counts: Dict[str, int] = {}
    for row in events:
        row_type = str(row.get("type") or "").strip()
        if row_type:
            event_type_counts[row_type] = int(event_type_counts.get(row_type, 0)) + 1
    return {
        "job_id": str(job_id),
        "status": str(job.get("status") or ""),
        "filters": {"event_type": event_type_filter, "checkpoint_id": checkpoint_filter},
        "event_count": len(events),
        "event_type_counts": event_type_counts,
        "events": events,
    }


def _tenant_from_namespace(namespace: Any) -> Optional[str]:
    raw = str(namespace or "").strip()
    if "/" not in raw:
        return None
    prefix = raw.split("/", 1)[0]
    return _normalize_tenant_candidate(prefix)


def _job_tenant_id(job: Dict[str, Any]) -> Optional[str]:
    if not isinstance(job, dict):
        return None
    metadata_raw = job.get("client_metadata")
    state_raw = job.get("state")
    preflight_raw = job.get("generate_preflight")
    metadata: Dict[str, Any] = metadata_raw if isinstance(metadata_raw, dict) else {}
    state: Dict[str, Any] = state_raw if isinstance(state_raw, dict) else {}
    preflight: Dict[str, Any] = preflight_raw if isinstance(preflight_raw, dict) else {}
    candidates = [
        metadata.get("tenant_id"),
        metadata.get("tenant"),
        state.get("tenant_id"),
        preflight.get("tenant_id"),
        state.get("rag_namespace"),
        state.get("retrieval_namespace"),
        preflight.get("retrieval_namespace"),
    ]
    for candidate in candidates:
        normalized = _normalize_tenant_candidate(candidate)
        if normalized:
            if isinstance(candidate, str) and "/" in candidate:
                from_namespace = _tenant_from_namespace(candidate)
                if from_namespace:
                    return from_namespace
            return normalized
    return None


def _job_state_dict(job: Dict[str, Any]) -> Dict[str, Any]:
    state = job.get("state") if isinstance(job.get("state"), dict) else {}
    return dict(normalized_state_copy(state))


def _job_donor_id(job: Dict[str, Any], *, default: str = "") -> str:
    state_dict = _job_state_dict(job)
    donor_id = state_donor_id(state_dict, default="")
    if donor_id:
        return donor_id
    metadata_raw = job.get("client_metadata")
    metadata: Dict[str, Any] = metadata_raw if isinstance(metadata_raw, dict) else {}
    token = str(metadata.get("donor_id") or metadata.get("donor") or "").strip().lower()
    return token or default


def _checkpoint_tenant_id(checkpoint: Dict[str, Any]) -> Optional[str]:
    if not isinstance(checkpoint, dict):
        return None
    snapshot_raw = checkpoint.get("state_snapshot")
    snapshot: Dict[str, Any] = snapshot_raw if isinstance(snapshot_raw, dict) else {}
    candidates = [
        checkpoint.get("tenant_id"),
        snapshot.get("tenant_id"),
        snapshot.get("rag_namespace"),
        snapshot.get("retrieval_namespace"),
    ]
    for candidate in candidates:
        normalized = _normalize_tenant_candidate(candidate)
        if normalized:
            if isinstance(candidate, str) and "/" in candidate:
                from_namespace = _tenant_from_namespace(candidate)
                if from_namespace:
                    return from_namespace
            return normalized
    return None


def _ensure_job_tenant_read_access(request: Request, job: Dict[str, Any]) -> Optional[str]:
    if not _tenant_authz_enabled():
        return None
    request_tenant = _resolve_tenant_id(request, require_if_enabled=True)
    job_tenant = _job_tenant_id(job)
    if not request_tenant or not job_tenant:
        raise HTTPException(status_code=403, detail="Tenant access denied for requested job")
    if request_tenant != job_tenant:
        raise HTTPException(status_code=403, detail="Tenant access denied for requested job")
    return request_tenant


def _ensure_job_tenant_write_access(request: Request, job: Dict[str, Any]) -> Optional[str]:
    return _ensure_job_tenant_read_access(request, job)


def _ensure_checkpoint_tenant_write_access(request: Request, checkpoint: Dict[str, Any]) -> Optional[str]:
    if not _tenant_authz_enabled():
        return None
    request_tenant = _resolve_tenant_id(request, require_if_enabled=True)
    checkpoint_tenant = _checkpoint_tenant_id(checkpoint)
    if not request_tenant or not checkpoint_tenant:
        raise HTTPException(status_code=403, detail="Tenant access denied for requested checkpoint")
    if request_tenant != checkpoint_tenant:
        raise HTTPException(status_code=403, detail="Tenant access denied for requested checkpoint")
    return request_tenant


def _filter_jobs_by_tenant(jobs: Dict[str, Dict[str, Any]], tenant_id: Optional[str]) -> Dict[str, Dict[str, Any]]:
    token = _normalize_tenant_candidate(tenant_id)
    if not token:
        return jobs
    filtered: Dict[str, Dict[str, Any]] = {}
    for job_id, job in jobs.items():
        if _job_tenant_id(job) == token:
            filtered[job_id] = job
    return filtered


class GenerateRequest(BaseModel):
    donor_id: str
    input_context: Dict[str, Any]
    tenant_id: Optional[str] = None
    request_id: Optional[str] = None
    llm_mode: bool = False
    architect_rag_enabled: bool = True
    require_grounded_generation: bool = False
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
    architect_rag_enabled: bool = True
    client_metadata: Optional[Dict[str, Any]] = None
    input_context: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(extra="forbid")


class IngestReadinessRequest(BaseModel):
    donor_id: str
    tenant_id: Optional[str] = None
    architect_rag_enabled: bool = True
    expected_doc_families: Optional[list[str]] = None
    client_metadata: Optional[Dict[str, Any]] = None
    input_context: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(extra="forbid")


class HITLApprovalRequest(BaseModel):
    checkpoint_id: str
    approved: bool
    feedback: Optional[str] = None
    request_id: Optional[str] = None


class ExportRequest(BaseModel):
    payload: Optional[Dict[str, Any]] = None
    toc_draft: Optional[Dict[str, Any]] = None
    logframe_draft: Optional[Dict[str, Any]] = None
    donor_id: Optional[str] = None
    review_comments: Optional[list[Dict[str, Any]]] = None
    critic_findings: Optional[list[Dict[str, Any]]] = None
    format: str = "both"
    allow_unsafe_export: bool = False
    production_export: bool = False

    model_config = ConfigDict(extra="allow")


class JobCommentCreateRequest(BaseModel):
    section: str
    message: str
    author: Optional[str] = None
    version_id: Optional[str] = None
    linked_finding_id: Optional[str] = None
    request_id: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class CriticFindingsBulkStatusRequest(BaseModel):
    next_status: str
    apply_to_all: bool = False
    dry_run: bool = False
    request_id: Optional[str] = None
    if_match_status: Optional[str] = None
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

    payload_state = dict(normalized_state_copy(payload))
    req_donor = str(req.donor_id or "").strip().lower()
    donor_id = req_donor or state_donor_id(payload_state, default="grantflow")
    toc = req.toc_draft or payload.get("toc_draft") or payload.get("toc") or {}
    logframe = req.logframe_draft or payload.get("logframe_draft") or payload.get("mel") or {}
    citations = payload.get("citations") or []
    state_critic_findings_payload = state_critic_findings(payload_state, default_source="rules")
    critic_findings = req.critic_findings or state_critic_findings_payload or payload_root.get("critic_findings") or []
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
    critic_findings = canonicalize_findings(critic_findings, state=payload_state, default_source="rules")
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


def _extract_export_runtime_grounded_quality_gate(req: ExportRequest) -> Dict[str, Any]:
    payload = req.payload if isinstance(req.payload, dict) else {}
    if not payload:
        return {}
    payload_root = payload if isinstance(payload, dict) else {}
    state_payload = payload_root.get("state") if isinstance(payload_root.get("state"), dict) else payload_root
    if not isinstance(state_payload, dict):
        return {}

    runtime_gate = state_payload.get("grounded_quality_gate")
    if isinstance(runtime_gate, dict):
        return runtime_gate

    public_runtime_gate = state_payload.get("grounded_gate")
    if isinstance(public_runtime_gate, dict):
        return public_runtime_gate

    root_runtime_gate = payload_root.get("grounded_quality_gate")
    if isinstance(root_runtime_gate, dict):
        return root_runtime_gate

    root_public_runtime_gate = payload_root.get("grounded_gate")
    if isinstance(root_public_runtime_gate, dict):
        return root_public_runtime_gate
    return {}


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
    raw_flaws = state_critic_findings(state, default_source="rules")
    if not raw_flaws:
        return job

    now_iso = _utcnow_iso()
    normalized_with_due = [_ensure_finding_due_at(item, now_iso=now_iso) for item in raw_flaws]
    existing_notes_raw = state.get("critic_notes")
    existing_notes: Dict[str, Any] = existing_notes_raw if isinstance(existing_notes_raw, dict) else {}
    existing_notes_flaws = (
        existing_notes.get("fatal_flaws") if isinstance(existing_notes.get("fatal_flaws"), list) else []
    )
    existing_state_flaws = state.get("critic_fatal_flaws") if isinstance(state.get("critic_fatal_flaws"), list) else []
    changed = normalized_with_due != existing_notes_flaws or normalized_with_due != existing_state_flaws

    if not changed:
        return job

    next_state = dict(state)
    write_state_critic_findings(
        next_state, normalized_with_due, previous_items=normalized_with_due, default_source="rules"
    )
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
    flaws = state_critic_findings(state_dict, default_source="rules")

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
    existing_notes_raw = state_dict.get("critic_notes")
    existing_notes: Dict[str, Any] = existing_notes_raw if isinstance(existing_notes_raw, dict) else {}
    existing_notes_flaws = (
        existing_notes.get("fatal_flaws") if isinstance(existing_notes.get("fatal_flaws"), list) else []
    )
    existing_state_flaws = (
        state_dict.get("critic_fatal_flaws") if isinstance(state_dict.get("critic_fatal_flaws"), list) else []
    )
    if isinstance(state, dict) and (next_flaws != existing_notes_flaws or next_flaws != existing_state_flaws):
        next_state = dict(state_dict)
        write_state_critic_findings(next_state, next_flaws, previous_items=next_flaws, default_source="rules")
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
    flaws = state_critic_findings(state, default_source="rules")
    for item in flaws:
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
    dry_run: bool = False,
    if_match_status: Optional[str] = None,
    request_id: Optional[str] = None,
) -> Dict[str, Any]:
    if next_status not in CRITIC_FINDING_STATUSES:
        raise HTTPException(status_code=400, detail="Unsupported critic finding status")
    expected_status = str(if_match_status or "").strip().lower() or None
    if expected_status and expected_status not in CRITIC_FINDING_STATUSES:
        raise HTTPException(status_code=400, detail="Unsupported if_match_status")
    request_id_token = _normalize_request_id(request_id)

    job = _normalize_critic_fatal_flaws_for_job(job_id) or _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    idempotency_fingerprint = _idempotency_fingerprint(
        {
            "op": "critic_finding_status",
            "job_id": str(job_id),
            "finding_id": str(finding_id),
            "next_status": str(next_status),
            "dry_run": bool(dry_run),
            "if_match_status": expected_status,
        }
    )
    replay = _idempotency_replay_response(
        job,
        scope="critic_finding_status",
        request_id=request_id_token,
        fingerprint=idempotency_fingerprint,
    )
    if replay is not None:
        return replay
    state = job.get("state")
    if not isinstance(state, dict):
        raise HTTPException(status_code=404, detail="Critic findings not found")
    critic_notes = state.get("critic_notes")
    if not isinstance(critic_notes, dict):
        raise HTTPException(status_code=404, detail="Critic findings not found")

    flaws = state_critic_findings(state, default_source="rules")
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
        current_status = str(current.get("status") or "open").strip().lower() or "open"
        if expected_status and current_status != expected_status:
            raise HTTPException(
                status_code=409,
                detail={
                    "reason": "finding_status_conflict",
                    "message": "Finding status changed since last read; refresh and retry.",
                    "finding_id": current_finding_id,
                    "if_match_status": expected_status,
                    "current_status": current_status,
                },
            )
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

    if changed and not dry_run:
        next_state = dict(state)
        write_state_critic_findings(next_state, next_flaws, previous_items=next_flaws, default_source="rules")
        _update_job(job_id, state=next_state)
        _record_job_event(
            job_id,
            "critic_finding_status_changed",
            finding_id=str(updated_finding.get("id") or finding_id),
            status=next_status,
            section=updated_finding.get("section"),
            severity=updated_finding.get("severity"),
            actor=actor_value,
            request_id=request_id_token,
        )

    response = dict(updated_finding)
    response["dry_run"] = bool(dry_run)
    response["persisted"] = not bool(dry_run)
    response["changed"] = bool(changed)
    if expected_status:
        response["if_match_status"] = expected_status
    if request_id_token:
        response["request_id"] = request_id_token
    _store_idempotency_response(
        job_id,
        scope="critic_finding_status",
        request_id=request_id_token,
        fingerprint=idempotency_fingerprint,
        response=response,
        persisted=not bool(dry_run),
    )
    return response


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
    dry_run: bool = False,
    request_id: Optional[str] = None,
    if_match_status: Optional[str] = None,
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
    expected_status = str(if_match_status or "").strip().lower() or None
    if expected_status and expected_status not in CRITIC_FINDING_STATUSES:
        raise HTTPException(status_code=400, detail="Unsupported if_match_status")
    if expected_status and finding_status_filter and expected_status != finding_status_filter:
        raise HTTPException(
            status_code=400, detail="if_match_status must match finding_status filter when both provided"
        )
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
    request_id_token = _normalize_request_id(request_id)

    job = _normalize_critic_fatal_flaws_for_job(job_id) or _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    idempotency_fingerprint = _idempotency_fingerprint(
        {
            "op": "critic_findings_bulk_status",
            "job_id": str(job_id),
            "next_status": str(next_status),
            "dry_run": bool(dry_run),
            "request_selectors": {
                "apply_to_all": bool(apply_to_all),
                "if_match_status": expected_status,
                "finding_status": finding_status_filter,
                "severity": severity_filter,
                "section": section_filter,
                "finding_ids": requested_finding_ids,
            },
        }
    )
    replay = _idempotency_replay_response(
        job,
        scope="critic_findings_bulk_status",
        request_id=request_id_token,
        fingerprint=idempotency_fingerprint,
    )
    if replay is not None:
        return replay
    state = job.get("state")
    if not isinstance(state, dict):
        raise HTTPException(status_code=404, detail="Critic findings not found")
    critic_notes = state.get("critic_notes")
    if not isinstance(critic_notes, dict):
        raise HTTPException(status_code=404, detail="Critic findings not found")

    flaws = state_critic_findings(state, default_source="rules")
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
    conflict_items: list[Dict[str, Any]] = []
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
        if expected_status and current_status != expected_status:
            conflict_items.append(
                {
                    "finding_id": current_finding_id,
                    "current_status": current_status,
                    "expected_status": expected_status,
                }
            )
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

    if conflict_items:
        raise HTTPException(
            status_code=409,
            detail={
                "reason": "finding_status_conflict",
                "message": "One or more findings changed status since last read; refresh and retry.",
                "if_match_status": expected_status,
                "conflict_count": len(conflict_items),
                "conflicts": conflict_items,
            },
        )

    if changed and not dry_run:
        next_state = dict(state)
        write_state_critic_findings(next_state, next_flaws, previous_items=next_flaws, default_source="rules")
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
                request_id=request_id_token,
            )

    matched_count = len(matched_items)
    changed_count = len(changed_items)
    response = {
        "job_id": str(job_id),
        "status": str((job or {}).get("status") or ""),
        "requested_status": next_status,
        "actor": actor_value,
        "dry_run": bool(dry_run),
        "persisted": not bool(dry_run),
        "matched_count": matched_count,
        "changed_count": changed_count,
        "unchanged_count": max(0, matched_count - changed_count),
        "not_found_finding_ids": not_found_finding_ids,
        "filters": {
            "apply_to_all": bool(apply_to_all),
            "if_match_status": expected_status,
            "finding_status": finding_status_filter,
            "severity": severity_filter,
            "section": section_filter,
            "finding_ids": requested_finding_ids or None,
        },
        "updated_findings": matched_items,
    }
    if request_id_token:
        response["request_id"] = request_id_token
    _store_idempotency_response(
        job_id,
        scope="critic_findings_bulk_status",
        request_id=request_id_token,
        fingerprint=idempotency_fingerprint,
        response=response,
        persisted=not bool(dry_run),
    )
    return response


def _validated_filter_token(
    value: Optional[str],
    *,
    allowed: set[str],
    detail: str,
) -> Optional[str]:
    token = str(value or "").strip().lower()
    if not token:
        return None
    if token not in allowed:
        raise HTTPException(status_code=400, detail=detail)
    return token


def _critic_findings_list_payload(
    job_id: str,
    job: Dict[str, Any],
    *,
    finding_status: Optional[str] = None,
    severity: Optional[str] = None,
    section: Optional[str] = None,
    version_id: Optional[str] = None,
    workflow_state: Optional[str] = None,
    include_resolved: bool = True,
    overdue_after_hours: int = REVIEW_WORKFLOW_OVERDUE_DEFAULT_HOURS,
) -> Dict[str, Any]:
    workflow_payload = public_job_review_workflow_payload(
        job_id,
        job,
        workflow_state=workflow_state,
        overdue_after_hours=overdue_after_hours,
    )
    findings_raw = workflow_payload.get("findings")
    findings = [dict(item) for item in findings_raw if isinstance(item, dict)] if isinstance(findings_raw, list) else []

    filtered: list[Dict[str, Any]] = []
    for row in findings:
        row_status = str(row.get("status") or "open").strip().lower()
        row_severity = str(row.get("severity") or "").strip().lower()
        row_section = str(row.get("section") or "").strip().lower()
        row_version_id = str(row.get("version_id") or "").strip() or None
        row_workflow_state = str(row.get("workflow_state") or "").strip().lower()

        if not include_resolved and row_status == "resolved":
            continue
        if finding_status is not None and row_status != finding_status:
            continue
        if severity is not None and row_severity != severity:
            continue
        if section is not None and row_section != section:
            continue
        if version_id is not None and row_version_id != version_id:
            continue
        if workflow_state is not None and row_workflow_state != workflow_state:
            continue
        filtered.append(row)

    finding_status_counts = {"open": 0, "acknowledged": 0, "resolved": 0}
    finding_severity_counts = {"high": 0, "medium": 0, "low": 0}
    pending_finding_count = 0
    overdue_finding_count = 0
    for row in filtered:
        row_status = str(row.get("status") or "open").strip().lower()
        row_severity = str(row.get("severity") or "").strip().lower()
        row_workflow_state = str(row.get("workflow_state") or "").strip().lower()
        if row_status in finding_status_counts:
            finding_status_counts[row_status] += 1
        if row_severity in finding_severity_counts:
            finding_severity_counts[row_severity] += 1
        if row_workflow_state == "pending":
            pending_finding_count += 1
        elif row_workflow_state == "overdue":
            overdue_finding_count += 1

    return {
        "job_id": str(job_id),
        "status": str(job.get("status") or ""),
        "filters": {
            "status": finding_status,
            "severity": severity,
            "section": section,
            "version_id": version_id,
            "workflow_state": workflow_state,
            "include_resolved": bool(include_resolved),
            "overdue_after_hours": int(overdue_after_hours),
        },
        "summary": {
            "finding_count": len(filtered),
            "open_finding_count": int(finding_status_counts.get("open", 0)),
            "acknowledged_finding_count": int(finding_status_counts.get("acknowledged", 0)),
            "resolved_finding_count": int(finding_status_counts.get("resolved", 0)),
            "pending_finding_count": pending_finding_count,
            "overdue_finding_count": overdue_finding_count,
            "finding_status_counts": finding_status_counts,
            "finding_severity_counts": finding_severity_counts,
        },
        "findings": filtered,
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
    request_id: Optional[str] = None,
) -> Dict[str, Any]:
    job = _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    request_id_token = _normalize_request_id(request_id)
    idempotency_fingerprint = _idempotency_fingerprint(
        {
            "op": "review_comment_add",
            "job_id": str(job_id),
            "section": section,
            "message": message,
            "author": author,
            "version_id": version_id,
            "linked_finding_id": linked_finding_id,
        }
    )
    replay = _idempotency_replay_response(
        job,
        scope="review_comment_add",
        request_id=request_id_token,
        fingerprint=idempotency_fingerprint,
    )
    if replay is not None:
        return replay

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
    if request_id_token:
        comment["request_id"] = request_id_token
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
        request_id=request_id_token,
    )
    _store_idempotency_response(
        job_id,
        scope="review_comment_add",
        request_id=request_id_token,
        fingerprint=idempotency_fingerprint,
        response=comment,
        persisted=True,
    )
    return comment


def _set_review_comment_status(
    job_id: str,
    *,
    comment_id: str,
    next_status: str,
    actor: Optional[str] = None,
    request_id: Optional[str] = None,
) -> Dict[str, Any]:
    job = _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    request_id_token = _normalize_request_id(request_id)
    idempotency_fingerprint = _idempotency_fingerprint(
        {
            "op": "review_comment_status",
            "job_id": str(job_id),
            "comment_id": str(comment_id),
            "next_status": str(next_status),
        }
    )
    replay = _idempotency_replay_response(
        job,
        scope="review_comment_status",
        request_id=request_id_token,
        fingerprint=idempotency_fingerprint,
    )
    if replay is not None:
        return replay

    existing = job.get("review_comments")
    comments = [c for c in existing if isinstance(c, dict)] if isinstance(existing, list) else []
    updated_comment: Optional[Dict[str, Any]] = None
    changed = False
    status_transitioned = False
    now_iso = _utcnow_iso()
    actor_value = str(actor or "").strip() or "api_user"

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
            current["updated_by"] = actor_value
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
            actor=actor_value,
            request_id=request_id_token,
        )
    response = dict(updated_comment)
    if request_id_token:
        response["request_id"] = request_id_token
    response["persisted"] = True
    response["changed"] = bool(status_transitioned)
    _store_idempotency_response(
        job_id,
        scope="review_comment_status",
        request_id=request_id_token,
        fingerprint=idempotency_fingerprint,
        response=response,
        persisted=True,
    )
    return response


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
    _clear_hitl_runtime_state(state, clear_pending=False)
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
    _record_job_event(
        job_id,
        "hitl_checkpoint_published",
        checkpoint_id=checkpoint_id,
        checkpoint_stage=stage,
        resume_from=resume_from,
    )


def _run_pipeline_to_completion(job_id: str, initial_state: dict) -> None:
    try:
        if _job_is_canceled(job_id):
            return
        normalize_state_contract(initial_state)
        _clear_hitl_runtime_state(initial_state, clear_pending=True)
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
        _attach_export_contract_gate(final_state)
        runtime_grounded_gate = _evaluate_runtime_grounded_quality_gate_from_state(final_state)
        final_state["grounded_quality_gate"] = runtime_grounded_gate
        if _job_is_canceled(job_id):
            return
        runtime_grounded_block_reason = _runtime_grounded_quality_gate_block_reason(final_state)
        if runtime_grounded_block_reason:
            _append_runtime_grounded_quality_gate_finding(final_state, runtime_grounded_gate)
            _record_job_event(
                job_id,
                "runtime_grounded_quality_gate_blocked",
                mode=str(runtime_grounded_gate.get("mode") or "strict"),
                summary=str(runtime_grounded_gate.get("summary") or ""),
                reasons=list(runtime_grounded_gate.get("reasons") or []),
            )
            _set_job(
                job_id,
                {
                    "status": "error",
                    "error": runtime_grounded_block_reason,
                    "state": final_state,
                    "hitl_enabled": False,
                },
            )
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
        _clear_hitl_runtime_state(state, clear_pending=True)
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
        if bool(final_state.get("hitl_pending")):
            _set_job(
                job_id,
                {
                    "status": "error",
                    "error": "HITL pending state returned without a valid checkpoint stage",
                    "state": final_state,
                    "hitl_enabled": True,
                },
            )
            return
        for key in RUNTIME_PIPELINE_STATE_KEYS:
            final_state.pop(key, None)
        final_state["hitl_pending"] = False
        _attach_export_contract_gate(final_state)
        runtime_grounded_gate = _evaluate_runtime_grounded_quality_gate_from_state(final_state)
        final_state["grounded_quality_gate"] = runtime_grounded_gate
        runtime_grounded_block_reason = _runtime_grounded_quality_gate_block_reason(final_state)
        if runtime_grounded_block_reason:
            _append_runtime_grounded_quality_gate_finding(final_state, runtime_grounded_gate)
            _record_job_event(
                job_id,
                "runtime_grounded_quality_gate_blocked",
                mode=str(runtime_grounded_gate.get("mode") or "strict"),
                summary=str(runtime_grounded_gate.get("summary") or ""),
                reasons=list(runtime_grounded_gate.get("reasons") or []),
            )
            _set_job(
                job_id,
                {
                    "status": "error",
                    "error": runtime_grounded_block_reason,
                    "state": final_state,
                    "hitl_enabled": True,
                },
            )
            return
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


def _clear_hitl_runtime_state(state: dict, *, clear_pending: bool) -> None:
    for key in RUNTIME_PIPELINE_STATE_KEYS:
        state.pop(key, None)
    if clear_pending:
        state["hitl_pending"] = False


def _health_diagnostics() -> dict[str, Any]:
    job_store_mode = _job_store_mode()
    hitl_store_mode = _hitl_store_mode()
    ingest_store_mode = _ingest_store_mode()
    sqlite_path = getattr(JOB_STORE, "db_path", None) or (
        getattr(hitl_manager, "_sqlite_path", None) if hitl_store_mode == "sqlite" else None
    )
    if not sqlite_path and ingest_store_mode == "sqlite":
        sqlite_path = getattr(INGEST_AUDIT_STORE, "db_path", None)

    vector_backend = "chroma" if getattr(vector_store, "client", None) is not None else "memory"
    preflight_grounding_thresholds = _preflight_grounding_policy_thresholds()
    runtime_grounded_quality_gate_thresholds = _runtime_grounded_quality_gate_thresholds()
    mel_grounding_thresholds = _mel_grounding_policy_thresholds()
    export_grounding_thresholds = _export_grounding_policy_thresholds()
    diagnostics: dict[str, Any] = {
        "job_store": {"mode": job_store_mode},
        "hitl_store": {"mode": hitl_store_mode},
        "ingest_store": {"mode": ingest_store_mode},
        "job_runner": {
            "mode": _job_runner_mode(),
            "queue_enabled": _uses_inmemory_queue_runner(),
            "queue": JOB_RUNNER.diagnostics(),
        },
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
        "runtime_grounded_quality_gate": {
            "mode": _configured_runtime_grounded_quality_gate_mode(),
            "thresholds": runtime_grounded_quality_gate_thresholds,
        },
        "mel_grounding_policy": {
            "mode": _configured_mel_grounding_policy_mode(),
            "thresholds": mel_grounding_thresholds,
        },
        "export_grounding_policy": {
            "mode": _configured_export_grounding_policy_mode(),
            "thresholds": export_grounding_thresholds,
        },
        "export_contract_policy": {
            "mode": _configured_export_contract_policy_mode(),
        },
        "export_runtime_grounded_gate_policy": {
            "require_pass": _configured_export_require_grounded_gate_pass(),
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
    return {"status": "healthy", "version": __version__, "diagnostics": _health_diagnostics()}


@app.get("/ready")
def readiness_check():
    vector_ready = _vector_store_readiness()
    job_runner_mode = _job_runner_mode()
    job_runner_diag = JOB_RUNNER.diagnostics()
    job_runner_ready = True
    if _uses_inmemory_queue_runner():
        job_runner_ready = bool(job_runner_diag.get("running"))
    ready = bool(vector_ready.get("ready")) and job_runner_ready
    preflight_grounding_thresholds = _preflight_grounding_policy_thresholds()
    runtime_grounded_quality_gate_thresholds = _runtime_grounded_quality_gate_thresholds()
    mel_grounding_thresholds = _mel_grounding_policy_thresholds()
    export_grounding_thresholds = _export_grounding_policy_thresholds()
    payload = {
        "status": "ready" if ready else "degraded",
        "checks": {
            "vector_store": vector_ready,
            "job_runner": {
                "mode": job_runner_mode,
                "ready": job_runner_ready,
                "queue": job_runner_diag,
            },
            "preflight_grounding_policy": {
                "mode": _configured_preflight_grounding_policy_mode(),
                "thresholds": preflight_grounding_thresholds,
            },
            "runtime_grounded_quality_gate": {
                "mode": _configured_runtime_grounded_quality_gate_mode(),
                "thresholds": runtime_grounded_quality_gate_thresholds,
            },
            "mel_grounding_policy": {
                "mode": _configured_mel_grounding_policy_mode(),
                "thresholds": mel_grounding_thresholds,
            },
            "export_grounding_policy": {
                "mode": _configured_export_grounding_policy_mode(),
                "thresholds": export_grounding_thresholds,
            },
            "export_contract_policy": {
                "mode": _configured_export_contract_policy_mode(),
            },
            "export_runtime_grounded_gate_policy": {
                "require_pass": _configured_export_require_grounded_gate_pass(),
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
    tenant_id: Optional[str] = Query(default=None),
    status: Optional[str] = None,
    hitl_enabled: Optional[bool] = Query(default=None),
    warning_level: Optional[str] = None,
    grounding_risk_level: Optional[str] = None,
    toc_text_risk_level: Optional[str] = None,
):
    require_api_key_if_configured(request, for_read=True)
    resolved_tenant_id = _resolve_tenant_id(request, explicit_tenant=tenant_id, require_if_enabled=True)
    jobs = _filter_jobs_by_tenant(_list_jobs(), resolved_tenant_id)
    return public_portfolio_metrics_payload(
        jobs,
        donor_id=(donor_id or None),
        status=(status or None),
        hitl_enabled=hitl_enabled,
        warning_level=(warning_level or None),
        grounding_risk_level=(grounding_risk_level or None),
        toc_text_risk_level=(toc_text_risk_level or None),
    )


@app.get("/portfolio/metrics/export")
def export_portfolio_metrics(
    request: Request,
    donor_id: Optional[str] = None,
    tenant_id: Optional[str] = Query(default=None),
    status: Optional[str] = None,
    hitl_enabled: Optional[bool] = Query(default=None),
    warning_level: Optional[str] = None,
    grounding_risk_level: Optional[str] = None,
    toc_text_risk_level: Optional[str] = None,
    format: Literal["csv", "json"] = Query(default="csv"),
    gzip_enabled: bool = Query(default=False, alias="gzip"),
):
    require_api_key_if_configured(request, for_read=True)
    resolved_tenant_id = _resolve_tenant_id(request, explicit_tenant=tenant_id, require_if_enabled=True)
    jobs = _filter_jobs_by_tenant(_list_jobs(), resolved_tenant_id)
    payload = public_portfolio_metrics_payload(
        jobs,
        donor_id=(donor_id or None),
        status=(status or None),
        hitl_enabled=hitl_enabled,
        warning_level=(warning_level or None),
        grounding_risk_level=(grounding_risk_level or None),
        toc_text_risk_level=(toc_text_risk_level or None),
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
    tenant_id: Optional[str] = Query(default=None),
    status: Optional[str] = None,
    hitl_enabled: Optional[bool] = Query(default=None),
    warning_level: Optional[str] = None,
    grounding_risk_level: Optional[str] = None,
    finding_status: Optional[str] = None,
    finding_severity: Optional[str] = None,
    toc_text_risk_level: Optional[str] = None,
):
    require_api_key_if_configured(request, for_read=True)
    resolved_tenant_id = _resolve_tenant_id(request, explicit_tenant=tenant_id, require_if_enabled=True)
    jobs = _filter_jobs_by_tenant(_list_jobs(), resolved_tenant_id)
    return public_portfolio_quality_payload(
        jobs,
        donor_id=(donor_id or None),
        status=(status or None),
        hitl_enabled=hitl_enabled,
        warning_level=(warning_level or None),
        grounding_risk_level=(grounding_risk_level or None),
        finding_status=(finding_status or None),
        finding_severity=(finding_severity or None),
        toc_text_risk_level=(toc_text_risk_level or None),
    )


@app.get("/portfolio/quality/export")
def export_portfolio_quality(
    request: Request,
    donor_id: Optional[str] = None,
    tenant_id: Optional[str] = Query(default=None),
    status: Optional[str] = None,
    hitl_enabled: Optional[bool] = Query(default=None),
    warning_level: Optional[str] = None,
    grounding_risk_level: Optional[str] = None,
    finding_status: Optional[str] = None,
    finding_severity: Optional[str] = None,
    toc_text_risk_level: Optional[str] = None,
    format: Literal["csv", "json"] = Query(default="csv"),
    gzip_enabled: bool = Query(default=False, alias="gzip"),
):
    require_api_key_if_configured(request, for_read=True)
    resolved_tenant_id = _resolve_tenant_id(request, explicit_tenant=tenant_id, require_if_enabled=True)
    jobs = _filter_jobs_by_tenant(_list_jobs(), resolved_tenant_id)
    payload = public_portfolio_quality_payload(
        jobs,
        donor_id=(donor_id or None),
        status=(status or None),
        hitl_enabled=hitl_enabled,
        warning_level=(warning_level or None),
        grounding_risk_level=(grounding_risk_level or None),
        finding_status=(finding_status or None),
        finding_severity=(finding_severity or None),
        toc_text_risk_level=(toc_text_risk_level or None),
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


@app.post(
    "/generate/preflight",
    response_model=GeneratePreflightPublicResponse,
    response_model_exclude_none=True,
)
def generate_preflight(req: GeneratePreflightRequest, request: Request):
    require_api_key_if_configured(request)
    donor, strategy, client_metadata = _resolve_preflight_request_context(
        request=request,
        donor_id=req.donor_id,
        tenant_id=req.tenant_id,
        client_metadata=req.client_metadata,
        input_context=req.input_context,
    )
    return _build_generate_preflight(
        donor_id=donor,
        strategy=strategy,
        client_metadata=client_metadata,
        architect_rag_enabled=bool(req.architect_rag_enabled),
    )


def _resolve_preflight_request_context(
    *,
    request: Request,
    donor_id: str,
    tenant_id: Optional[str] = None,
    client_metadata: Optional[Dict[str, Any]] = None,
    input_context: Optional[Dict[str, Any]] = None,
    expected_doc_families: Optional[list[str]] = None,
) -> tuple[str, Any, Optional[Dict[str, Any]]]:
    donor = str(donor_id or "").strip()
    if not donor:
        raise HTTPException(status_code=400, detail="Missing donor_id")

    try:
        strategy = DonorFactory.get_strategy(donor)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    metadata = dict(client_metadata) if isinstance(client_metadata, dict) else {}
    resolved_tenant_id = _resolve_tenant_id(
        request,
        explicit_tenant=tenant_id,
        client_metadata=metadata,
        require_if_enabled=True,
    )
    if resolved_tenant_id:
        metadata["tenant_id"] = resolved_tenant_id

    if isinstance(input_context, dict) and input_context:
        metadata["_preflight_input_context"] = dict(input_context)

    if isinstance(expected_doc_families, list):
        expected = _dedupe_doc_families(expected_doc_families)
        if expected:
            rag_readiness_raw = metadata.get("rag_readiness")
            rag_readiness: Dict[str, Any] = dict(rag_readiness_raw) if isinstance(rag_readiness_raw, dict) else {}
            rag_readiness["expected_doc_families"] = expected
            if not str(rag_readiness.get("donor_id") or "").strip():
                rag_readiness["donor_id"] = donor
            metadata["rag_readiness"] = rag_readiness

    return donor, strategy, (metadata or None)


@app.post(
    "/ingest/readiness",
    response_model=GeneratePreflightPublicResponse,
    response_model_exclude_none=True,
)
def ingest_readiness(req: IngestReadinessRequest, request: Request):
    require_api_key_if_configured(request, for_read=True)
    donor, strategy, client_metadata = _resolve_preflight_request_context(
        request=request,
        donor_id=req.donor_id,
        tenant_id=req.tenant_id,
        client_metadata=req.client_metadata,
        input_context=req.input_context,
        expected_doc_families=req.expected_doc_families,
    )
    return _build_generate_preflight(
        donor_id=donor,
        strategy=strategy,
        client_metadata=client_metadata,
        architect_rag_enabled=bool(req.architect_rag_enabled),
    )


@app.post("/generate")
async def generate(
    req: GenerateRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    request_id: Optional[str] = Query(default=None),
):
    require_api_key_if_configured(request)
    request_id_token = _resolve_request_id(request, request_id if request_id is not None else req.request_id)
    donor = req.donor_id.strip()
    if not donor:
        raise HTTPException(status_code=400, detail="Missing donor_id")

    webhook_url = (req.webhook_url or "").strip() or None
    webhook_secret = (req.webhook_secret or "").strip() or None
    if webhook_secret and not webhook_url:
        raise HTTPException(status_code=400, detail="webhook_secret requires webhook_url")
    if webhook_url and not (webhook_url.startswith("http://") or webhook_url.startswith("https://")):
        raise HTTPException(status_code=400, detail="webhook_url must start with http:// or https://")

    generate_fingerprint = _idempotency_fingerprint(
        {
            "op": "generate",
            "donor_id": donor,
            "input_context": req.input_context or {},
            "tenant_id": req.tenant_id,
            "llm_mode": bool(req.llm_mode),
            "architect_rag_enabled": bool(req.architect_rag_enabled),
            "require_grounded_generation": bool(req.require_grounded_generation),
            "hitl_enabled": bool(req.hitl_enabled),
            "hitl_checkpoints": list(req.hitl_checkpoints or []),
            "strict_preflight": bool(req.strict_preflight),
            "webhook_url": webhook_url,
            "webhook_secret": webhook_secret,
            "client_metadata": req.client_metadata or {},
        }
    )
    replay = _global_idempotency_replay_response(
        scope="generate",
        request_id=request_id_token,
        fingerprint=generate_fingerprint,
    )
    if replay is not None:
        return replay

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
    preflight_client_metadata = dict(client_metadata) if isinstance(client_metadata, dict) else {}
    if isinstance(input_payload, dict) and input_payload:
        preflight_client_metadata["_preflight_input_context"] = dict(input_payload)
    preflight = _build_generate_preflight(
        donor_id=donor,
        strategy=strategy,
        client_metadata=preflight_client_metadata or None,
        architect_rag_enabled=bool(req.architect_rag_enabled),
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
    if req.llm_mode and req.require_grounded_generation and grounding_risk_high:
        raise HTTPException(
            status_code=409,
            detail={
                "reason": "llm_grounded_generation_block",
                "message": (
                    "Generation blocked because require_grounded_generation=true "
                    "and predicted grounding risk is high."
                ),
                "strict_reasons": ["grounding_risk_high"],
                "preflight": preflight_payload,
            },
        )
    job_id = str(uuid.uuid4())
    initial_state = build_graph_state(
        donor_id=donor,
        input_context=input_payload,
        donor_strategy=strategy,
        tenant_id=tenant_id,
        rag_namespace=str(preflight_payload.get("retrieval_namespace") or ""),
        llm_mode=bool(req.llm_mode),
        hitl_checkpoints=list(req.hitl_checkpoints or []),
        max_iterations=int(config.graph.max_iterations),
        generate_preflight=preflight_payload,
        strict_preflight=bool(req.strict_preflight),
        extras={
            "require_grounded_generation": bool(req.require_grounded_generation),
            "architect_rag_enabled": bool(req.architect_rag_enabled),
        },
    )

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
            "require_grounded_generation": req.require_grounded_generation,
        },
    )
    _record_job_event(
        job_id,
        "generate_preflight_evaluated",
        request_id=request_id_token,
        tenant_id=preflight_payload.get("tenant_id"),
        risk_level=str(preflight_payload.get("risk_level") or "none"),
        grounding_risk_level=str(preflight_payload.get("grounding_risk_level") or "none"),
        warning_count=int(preflight_payload.get("warning_count") or 0),
        retrieval_namespace=preflight_payload.get("retrieval_namespace"),
        namespace_empty=bool(preflight_payload.get("namespace_empty")),
        llm_mode=bool(req.llm_mode),
        require_grounded_generation=bool(req.require_grounded_generation),
        grounding_policy_mode=str(grounding_policy.get("mode") or ""),
        grounding_policy_blocking=bool(grounding_policy.get("blocking")),
        architect_rag_enabled=bool(req.architect_rag_enabled),
    )
    try:
        queue_backend = "background_tasks"
        if req.hitl_enabled:
            queue_backend = _dispatch_pipeline_task(
                background_tasks, _run_hitl_pipeline, job_id, initial_state, "start"
            )
        else:
            queue_backend = _dispatch_pipeline_task(
                background_tasks, _run_pipeline_to_completion, job_id, initial_state
            )
    except HTTPException as exc:
        _set_job(
            job_id,
            {
                "status": "error",
                "error": str(exc.detail),
                "state": initial_state,
                "hitl_enabled": req.hitl_enabled,
            },
        )
        _record_job_event(
            job_id,
            "job_dispatch_failed",
            backend=_job_runner_mode(),
            hitl_enabled=bool(req.hitl_enabled),
            reason=str(exc.detail),
            request_id=request_id_token,
        )
        raise
    _record_job_event(
        job_id,
        "job_dispatch_queued",
        backend=queue_backend,
        hitl_enabled=bool(req.hitl_enabled),
        request_id=request_id_token,
    )
    response = {"status": "accepted", "job_id": job_id, "preflight": preflight_payload}
    if request_id_token:
        response["request_id"] = request_id_token
    _store_global_idempotency_response(
        scope="generate",
        request_id=request_id_token,
        fingerprint=generate_fingerprint,
        response=response,
        persisted=True,
    )
    return response


@app.post("/cancel/{job_id}")
def cancel_job(job_id: str, request: Request, request_id: Optional[str] = Query(default=None)):
    require_api_key_if_configured(request)
    job = _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    _ensure_job_tenant_write_access(request, job)
    request_id_token = _resolve_request_id(request, request_id)
    idempotency_fingerprint = _idempotency_fingerprint({"op": "cancel_job", "job_id": str(job_id)})
    replay = _idempotency_replay_response(
        job,
        scope="cancel_job",
        request_id=request_id_token,
        fingerprint=idempotency_fingerprint,
    )
    if replay is not None:
        return replay

    status = str(job.get("status") or "")
    if status == "canceled":
        response = {"status": "canceled", "job_id": job_id, "already_canceled": True}
        if request_id_token:
            response["request_id"] = request_id_token
        _store_idempotency_response(
            job_id,
            scope="cancel_job",
            request_id=request_id_token,
            fingerprint=idempotency_fingerprint,
            response=response,
            persisted=True,
        )
        return response
    if status in {"done", "error"}:
        raise HTTPException(status_code=409, detail=f"Job is already terminal: {status}")

    checkpoint_id = job.get("checkpoint_id")
    checkpoint_canceled = False
    if checkpoint_id:
        checkpoint = hitl_manager.get_checkpoint(str(checkpoint_id))
        if checkpoint and checkpoint.get("status") == HITLStatus.PENDING:
            checkpoint_canceled = bool(hitl_manager.cancel(str(checkpoint_id), "Canceled by user"))
    if checkpoint_id and checkpoint_canceled:
        _record_job_event(
            job_id,
            "hitl_checkpoint_canceled",
            checkpoint_id=str(checkpoint_id),
            reason="Canceled by user",
            request_id=request_id_token,
        )

    _update_job(
        job_id,
        status="canceled",
        cancellation_reason="Canceled by user",
        canceled=True,
    )
    _record_job_event(
        job_id, "job_canceled", previous_status=status, reason="Canceled by user", request_id=request_id_token
    )
    response = {"status": "canceled", "job_id": job_id, "previous_status": status}
    if request_id_token:
        response["request_id"] = request_id_token
    _store_idempotency_response(
        job_id,
        scope="cancel_job",
        request_id=request_id_token,
        fingerprint=idempotency_fingerprint,
        response=response,
        persisted=True,
    )
    return response


@app.post("/resume/{job_id}")
async def resume_job(
    job_id: str,
    background_tasks: BackgroundTasks,
    request: Request,
    request_id: Optional[str] = Query(default=None),
):
    require_api_key_if_configured(request)
    job = _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    _ensure_job_tenant_write_access(request, job)
    request_id_token = _resolve_request_id(request, request_id)
    idempotency_fingerprint = _idempotency_fingerprint({"op": "resume_job", "job_id": str(job_id)})
    replay = _idempotency_replay_response(
        job,
        scope="resume_job",
        request_id=request_id_token,
        fingerprint=idempotency_fingerprint,
    )
    if replay is not None:
        return replay
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

    _clear_hitl_runtime_state(state, clear_pending=True)
    normalize_state_contract(state)

    _update_job(
        job_id,
        status="accepted",
        state=state,
        resume_from=start_at,
        checkpoint_id=None,
        checkpoint_stage=None,
        checkpoint_status=getattr(checkpoint.get("status"), "value", checkpoint.get("status")),
    )
    _record_job_event(
        job_id,
        "resume_requested",
        checkpoint_id=str(checkpoint_id),
        checkpoint_status=getattr(checkpoint.get("status"), "value", checkpoint.get("status")),
        resuming_from=start_at,
        request_id=request_id_token,
    )
    try:
        queue_backend = _dispatch_pipeline_task(background_tasks, _run_hitl_pipeline, job_id, state, start_at)
    except HTTPException as exc:
        _update_job(
            job_id,
            status="pending_hitl",
            state=state,
            resume_from=job.get("resume_from"),
            checkpoint_id=checkpoint_id,
            checkpoint_stage=checkpoint.get("stage"),
            checkpoint_status=getattr(checkpoint.get("status"), "value", checkpoint.get("status")),
        )
        _record_job_event(
            job_id,
            "resume_dispatch_failed",
            backend=_job_runner_mode(),
            checkpoint_id=str(checkpoint_id),
            resuming_from=start_at,
            reason=str(exc.detail),
            request_id=request_id_token,
        )
        raise
    _record_job_event(
        job_id,
        "resume_dispatch_queued",
        backend=queue_backend,
        resuming_from=start_at,
        request_id=request_id_token,
    )
    response = {
        "status": "accepted",
        "job_id": job_id,
        "resuming_from": start_at,
        "checkpoint_id": checkpoint_id,
        "checkpoint_status": getattr(checkpoint.get("status"), "value", checkpoint.get("status")),
    }
    if request_id_token:
        response["request_id"] = request_id_token
    _store_idempotency_response(
        job_id,
        scope="resume_job",
        request_id=request_id_token,
        fingerprint=idempotency_fingerprint,
        response=response,
        persisted=True,
    )
    return response


@app.get("/status/{job_id}", response_model=JobStatusPublicResponse, response_model_exclude_none=True)
def get_status(job_id: str, request: Request):
    require_api_key_if_configured(request, for_read=True)
    job = _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    _ensure_job_tenant_read_access(request, job)
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
    _ensure_job_tenant_read_access(request, job)
    return public_job_citations_payload(job_id, job)


@app.get(
    "/status/{job_id}/export-payload",
    response_model=JobExportPayloadPublicResponse,
    response_model_exclude_none=True,
)
def get_status_export_payload(job_id: str, request: Request):
    require_api_key_if_configured(request, for_read=True)
    job = _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    _ensure_job_tenant_read_access(request, job)
    job = _normalize_critic_fatal_flaws_for_job(job_id) or job
    job_tenant_id = _job_tenant_id(job)
    donor = _job_donor_id(job)
    inventory_rows = _ingest_inventory(donor_id=donor or None, tenant_id=job_tenant_id)
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
    _ensure_job_tenant_read_access(request, job)
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
    _ensure_job_tenant_read_access(request, job)
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
    _ensure_job_tenant_read_access(request, job)
    return public_job_events_payload(job_id, job)


@app.get(
    "/status/{job_id}/hitl/history",
    response_model=JobHITLHistoryPublicResponse,
    response_model_exclude_none=True,
)
def get_status_hitl_history(
    job_id: str,
    request: Request,
    event_type: Optional[str] = Query(default=None),
    checkpoint_id: Optional[str] = Query(default=None),
):
    require_api_key_if_configured(request, for_read=True)
    job = _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    _ensure_job_tenant_read_access(request, job)
    return _hitl_history_payload(
        job_id,
        job,
        event_type=(event_type or None),
        checkpoint_id=(checkpoint_id or None),
    )


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
    _ensure_job_tenant_read_access(request, job)
    return public_job_metrics_payload(job_id, job)


@app.get(
    "/status/{job_id}/quality",
    response_model=JobQualitySummaryPublicResponse,
    response_model_exclude_none=True,
)
def get_status_quality(job_id: str, request: Request):
    require_api_key_if_configured(request, for_read=True)
    job = _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    _ensure_job_tenant_read_access(request, job)
    job = _normalize_critic_fatal_flaws_for_job(job_id) or job
    job_tenant_id = _job_tenant_id(job)
    donor = _job_donor_id(job)
    inventory_rows = _ingest_inventory(donor_id=donor or None, tenant_id=job_tenant_id)
    return public_job_quality_payload(job_id, job, ingest_inventory_rows=inventory_rows)


@app.get(
    "/status/{job_id}/grounding-gate",
    response_model=JobGroundingGatePublicResponse,
    response_model_exclude_none=True,
)
def get_status_grounding_gate(job_id: str, request: Request):
    require_api_key_if_configured(request, for_read=True)
    job = _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    _ensure_job_tenant_read_access(request, job)
    return public_job_grounding_gate_payload(job_id, job)


@app.get(
    "/status/{job_id}/critic",
    response_model=JobCriticPublicResponse,
    response_model_exclude_none=True,
)
def get_status_critic(job_id: str, request: Request):
    require_api_key_if_configured(request, for_read=True)
    job = _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    _ensure_job_tenant_read_access(request, job)
    job = _normalize_critic_fatal_flaws_for_job(job_id) or job
    return public_job_critic_payload(job_id, job)


@app.get(
    "/status/{job_id}/critic/findings",
    response_model=CriticFindingsListPublicResponse,
    response_model_exclude_none=True,
)
def get_status_critic_findings(
    job_id: str,
    request: Request,
    status: Optional[str] = Query(default=None),
    severity: Optional[str] = Query(default=None),
    section: Optional[str] = Query(default=None),
    version_id: Optional[str] = Query(default=None),
    workflow_state: Optional[str] = Query(default=None),
    include_resolved: bool = True,
    overdue_after_hours: int = REVIEW_WORKFLOW_OVERDUE_DEFAULT_HOURS,
):
    require_api_key_if_configured(request, for_read=True)
    job = _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    _ensure_job_tenant_read_access(request, job)
    job = _normalize_critic_fatal_flaws_for_job(job_id) or job

    finding_status = _validated_filter_token(
        status,
        allowed=CRITIC_FINDING_STATUSES,
        detail="Unsupported finding status filter",
    )
    finding_severity = _validated_filter_token(
        severity,
        allowed={"high", "medium", "low"},
        detail="Unsupported finding severity filter",
    )
    finding_section = _validated_filter_token(
        section,
        allowed={"toc", "logframe", "general"},
        detail="Unsupported finding section filter",
    )
    finding_workflow_state = _validated_filter_token(
        workflow_state,
        allowed=set(REVIEW_WORKFLOW_STATE_FILTER_VALUES) | {"resolved"},
        detail="Unsupported workflow_state filter",
    )
    if overdue_after_hours <= 0:
        raise HTTPException(status_code=400, detail="overdue_after_hours must be > 0")

    return _critic_findings_list_payload(
        job_id,
        job,
        finding_status=finding_status,
        severity=finding_severity,
        section=finding_section,
        version_id=(str(version_id or "").strip() or None),
        workflow_state=finding_workflow_state,
        include_resolved=bool(include_resolved),
        overdue_after_hours=int(overdue_after_hours),
    )


@app.get(
    "/status/{job_id}/critic/findings/{finding_id}",
    response_model=CriticFatalFlawPublicResponse,
    response_model_exclude_none=True,
)
def get_status_critic_finding(
    job_id: str,
    finding_id: str,
    request: Request,
    overdue_after_hours: int = REVIEW_WORKFLOW_OVERDUE_DEFAULT_HOURS,
):
    require_api_key_if_configured(request, for_read=True)
    job = _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    _ensure_job_tenant_read_access(request, job)
    job = _normalize_critic_fatal_flaws_for_job(job_id) or job

    if overdue_after_hours <= 0:
        raise HTTPException(status_code=400, detail="overdue_after_hours must be > 0")

    payload = _critic_findings_list_payload(
        job_id,
        job,
        overdue_after_hours=int(overdue_after_hours),
    )
    findings = payload.get("findings")
    for item in findings if isinstance(findings, list) else []:
        if not isinstance(item, dict):
            continue
        if finding_primary_id(item) == finding_id:
            return item
    raise HTTPException(status_code=404, detail="Critic finding not found")


@app.post(
    "/status/{job_id}/critic/findings/{finding_id}/ack",
    response_model=CriticFatalFlawStatusUpdatePublicResponse,
    response_model_exclude_none=True,
)
def acknowledge_status_critic_finding(
    job_id: str,
    finding_id: str,
    request: Request,
    dry_run: bool = False,
    if_match_status: Optional[str] = Query(default=None),
    request_id: Optional[str] = Query(default=None),
):
    require_api_key_if_configured(request)
    job = _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    _ensure_job_tenant_write_access(request, job)
    return _set_critic_fatal_flaw_status(
        job_id,
        finding_id=finding_id,
        next_status="acknowledged",
        actor=_finding_actor_from_request(request),
        dry_run=bool(dry_run),
        if_match_status=(if_match_status or None),
        request_id=_resolve_request_id(request, request_id),
    )


@app.post(
    "/status/{job_id}/critic/findings/{finding_id}/open",
    response_model=CriticFatalFlawStatusUpdatePublicResponse,
    response_model_exclude_none=True,
)
def reopen_status_critic_finding(
    job_id: str,
    finding_id: str,
    request: Request,
    dry_run: bool = False,
    if_match_status: Optional[str] = Query(default=None),
    request_id: Optional[str] = Query(default=None),
):
    require_api_key_if_configured(request)
    job = _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    _ensure_job_tenant_write_access(request, job)
    return _set_critic_fatal_flaw_status(
        job_id,
        finding_id=finding_id,
        next_status="open",
        actor=_finding_actor_from_request(request),
        dry_run=bool(dry_run),
        if_match_status=(if_match_status or None),
        request_id=_resolve_request_id(request, request_id),
    )


@app.post(
    "/status/{job_id}/critic/findings/{finding_id}/resolve",
    response_model=CriticFatalFlawStatusUpdatePublicResponse,
    response_model_exclude_none=True,
)
def resolve_status_critic_finding(
    job_id: str,
    finding_id: str,
    request: Request,
    dry_run: bool = False,
    if_match_status: Optional[str] = Query(default=None),
    request_id: Optional[str] = Query(default=None),
):
    require_api_key_if_configured(request)
    job = _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    _ensure_job_tenant_write_access(request, job)
    return _set_critic_fatal_flaw_status(
        job_id,
        finding_id=finding_id,
        next_status="resolved",
        actor=_finding_actor_from_request(request),
        dry_run=bool(dry_run),
        if_match_status=(if_match_status or None),
        request_id=_resolve_request_id(request, request_id),
    )


@app.post(
    "/status/{job_id}/critic/findings/bulk-status",
    response_model=CriticFindingsBulkStatusPublicResponse,
    response_model_exclude_none=True,
)
def bulk_status_critic_findings(job_id: str, req: CriticFindingsBulkStatusRequest, request: Request):
    require_api_key_if_configured(request)
    job = _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    _ensure_job_tenant_write_access(request, job)
    next_status = str(req.next_status or "").strip().lower()
    return _set_critic_fatal_flaws_status_bulk(
        job_id,
        next_status=next_status,
        actor=_finding_actor_from_request(request),
        dry_run=bool(req.dry_run),
        request_id=_resolve_request_id(request, req.request_id),
        if_match_status=(req.if_match_status or None),
        apply_to_all=bool(req.apply_to_all),
        finding_status=(req.finding_status or None),
        severity=(req.severity or None),
        section=(req.section or None),
        finding_ids=req.finding_ids,
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
    _ensure_job_tenant_read_access(request, job)
    job = _normalize_critic_fatal_flaws_for_job(job_id) or job
    job = _normalize_review_comments_for_job(job_id) or job
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
def get_status_review_workflow(
    job_id: str,
    request: Request,
    event_type: Optional[str] = None,
    finding_id: Optional[str] = None,
    finding_code: Optional[str] = Query(default=None, alias="finding_code"),
    finding_section: Optional[str] = Query(default=None, alias="finding_section"),
    comment_status: Optional[str] = Query(default=None, alias="comment_status"),
    workflow_state: Optional[str] = Query(default=None, alias="workflow_state"),
    overdue_after_hours: int = Query(
        default=REVIEW_WORKFLOW_OVERDUE_DEFAULT_HOURS,
        ge=1,
        le=24 * 30,
        alias="overdue_after_hours",
    ),
):
    require_api_key_if_configured(request, for_read=True)
    workflow_state_filter = str(workflow_state or "").strip().lower() or None
    if workflow_state_filter and workflow_state_filter not in REVIEW_WORKFLOW_STATE_FILTER_VALUES:
        raise HTTPException(status_code=400, detail="Unsupported workflow_state filter")
    finding_section_filter = _validated_filter_token(
        finding_section,
        allowed={"toc", "logframe", "general"},
        detail="Unsupported finding_section filter",
    )
    job = _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    _ensure_job_tenant_read_access(request, job)
    job = _normalize_critic_fatal_flaws_for_job(job_id) or job
    job = _normalize_review_comments_for_job(job_id) or job
    return public_job_review_workflow_payload(
        job_id,
        job,
        event_type=(event_type or None),
        finding_id=(finding_id or None),
        finding_code=(str(finding_code or "").strip() or None),
        finding_section=finding_section_filter,
        comment_status=(comment_status or None),
        workflow_state=workflow_state_filter,
        overdue_after_hours=overdue_after_hours,
    )


@app.get(
    "/status/{job_id}/review/workflow/sla",
    response_model=JobReviewWorkflowSLAPublicResponse,
    response_model_exclude_none=True,
)
def get_status_review_workflow_sla(
    job_id: str,
    request: Request,
    overdue_after_hours: int = Query(
        default=REVIEW_WORKFLOW_OVERDUE_DEFAULT_HOURS,
        ge=1,
        le=24 * 30,
        alias="overdue_after_hours",
    ),
):
    require_api_key_if_configured(request, for_read=True)
    job = _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    _ensure_job_tenant_read_access(request, job)
    job = _normalize_critic_fatal_flaws_for_job(job_id) or job
    job = _normalize_review_comments_for_job(job_id) or job
    return public_job_review_workflow_sla_payload(
        job_id,
        job,
        overdue_after_hours=overdue_after_hours,
    )


@app.get(
    "/status/{job_id}/review/workflow/sla/profile",
    response_model=JobReviewWorkflowSLAProfilePublicResponse,
    response_model_exclude_none=True,
)
def get_status_review_workflow_sla_profile(job_id: str, request: Request):
    require_api_key_if_configured(request, for_read=True)
    job = _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    _ensure_job_tenant_read_access(request, job)
    job = _normalize_critic_fatal_flaws_for_job(job_id) or job
    job = _normalize_review_comments_for_job(job_id) or job
    return _review_workflow_sla_profile_payload(job_id, job)


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
    job = _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    _ensure_job_tenant_write_access(request, job)
    payload = req or ReviewWorkflowSLARecomputeRequest()
    return _recompute_review_workflow_sla(
        job_id,
        actor=_finding_actor_from_request(request),
        finding_sla_hours_override=payload.finding_sla_hours,
        default_comment_sla_hours=payload.default_comment_sla_hours,
        use_saved_profile=bool(payload.use_saved_profile),
    )


@app.get("/status/{job_id}/review/workflow/export")
def export_status_review_workflow(
    job_id: str,
    request: Request,
    event_type: Optional[str] = None,
    finding_id: Optional[str] = None,
    finding_code: Optional[str] = Query(default=None, alias="finding_code"),
    finding_section: Optional[str] = Query(default=None, alias="finding_section"),
    comment_status: Optional[str] = Query(default=None, alias="comment_status"),
    workflow_state: Optional[str] = Query(default=None, alias="workflow_state"),
    overdue_after_hours: int = Query(
        default=REVIEW_WORKFLOW_OVERDUE_DEFAULT_HOURS,
        ge=1,
        le=24 * 30,
        alias="overdue_after_hours",
    ),
    format: Literal["csv", "json"] = Query(default="csv"),
    gzip_enabled: bool = Query(default=False, alias="gzip"),
):
    require_api_key_if_configured(request, for_read=True)
    workflow_state_filter = str(workflow_state or "").strip().lower() or None
    if workflow_state_filter and workflow_state_filter not in REVIEW_WORKFLOW_STATE_FILTER_VALUES:
        raise HTTPException(status_code=400, detail="Unsupported workflow_state filter")
    finding_section_filter = _validated_filter_token(
        finding_section,
        allowed={"toc", "logframe", "general"},
        detail="Unsupported finding_section filter",
    )
    job = _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    _ensure_job_tenant_read_access(request, job)
    job = _normalize_critic_fatal_flaws_for_job(job_id) or job
    job = _normalize_review_comments_for_job(job_id) or job
    payload = public_job_review_workflow_payload(
        job_id,
        job,
        event_type=(event_type or None),
        finding_id=(finding_id or None),
        finding_code=(str(finding_code or "").strip() or None),
        finding_section=finding_section_filter,
        comment_status=(comment_status or None),
        workflow_state=workflow_state_filter,
        overdue_after_hours=overdue_after_hours,
    )
    return _portfolio_export_response(
        payload=payload,
        filename_prefix=f"grantflow_review_workflow_{job_id}",
        donor_id=None,
        status=None,
        hitl_enabled=None,
        export_format=format,
        gzip_enabled=gzip_enabled,
        csv_renderer=public_job_review_workflow_csv_text,
    )


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
    _ensure_job_tenant_write_access(request, job)

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
    linked_finding_severity: Optional[str] = None
    if linked_finding_id:
        normalized_job = _normalize_critic_fatal_flaws_for_job(job_id) or _get_job(job_id)
        if not normalized_job:
            raise HTTPException(status_code=404, detail="Job not found")
        finding = _find_critic_fatal_flaw(normalized_job, linked_finding_id)
        if not finding:
            raise HTTPException(status_code=400, detail="Unknown linked_finding_id")
        linked_finding_id = finding_primary_id(finding) or linked_finding_id
        linked_finding_severity = str(finding.get("severity") or "").strip().lower() or None
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
        linked_finding_severity=linked_finding_severity,
        request_id=_resolve_request_id(request, req.request_id),
    )


@app.post(
    "/status/{job_id}/comments/{comment_id}/resolve",
    response_model=ReviewCommentPublicResponse,
    response_model_exclude_none=True,
)
def resolve_status_comment(
    job_id: str,
    comment_id: str,
    request: Request,
    request_id: Optional[str] = Query(default=None),
):
    require_api_key_if_configured(request)
    job = _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    _ensure_job_tenant_write_access(request, job)
    return _set_review_comment_status(
        job_id,
        comment_id=comment_id,
        next_status="resolved",
        actor=_finding_actor_from_request(request),
        request_id=_resolve_request_id(request, request_id),
    )


@app.post(
    "/status/{job_id}/comments/{comment_id}/reopen",
    response_model=ReviewCommentPublicResponse,
    response_model_exclude_none=True,
)
def reopen_status_comment(
    job_id: str,
    comment_id: str,
    request: Request,
    request_id: Optional[str] = Query(default=None),
):
    require_api_key_if_configured(request)
    job = _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    _ensure_job_tenant_write_access(request, job)
    return _set_review_comment_status(
        job_id,
        comment_id=comment_id,
        next_status="open",
        actor=_finding_actor_from_request(request),
        request_id=_resolve_request_id(request, request_id),
    )


@app.post("/hitl/approve")
def approve_checkpoint(
    req: HITLApprovalRequest,
    request: Request,
    request_id: Optional[str] = Query(default=None),
):
    require_api_key_if_configured(request)
    request_id_token = _resolve_request_id(request, request_id if request_id is not None else req.request_id)
    feedback = req.feedback if req.approved else (req.feedback or "Rejected")
    idempotency_fingerprint = _idempotency_fingerprint(
        {
            "op": "hitl_approve",
            "checkpoint_id": str(req.checkpoint_id),
            "approved": bool(req.approved),
            "feedback": str(feedback or ""),
        }
    )
    replay = _global_idempotency_replay_response(
        scope="hitl_approve",
        request_id=request_id_token,
        fingerprint=idempotency_fingerprint,
    )
    if replay is not None:
        return replay
    checkpoint = hitl_manager.get_checkpoint(req.checkpoint_id)
    if not checkpoint:
        raise HTTPException(status_code=404, detail="Checkpoint not found")
    _ensure_checkpoint_tenant_write_access(request, checkpoint)
    actor = _finding_actor_from_request(request)
    job_id_for_checkpoint, _job_for_checkpoint = _find_job_by_checkpoint_id(req.checkpoint_id)

    if req.approved:
        hitl_manager.approve(req.checkpoint_id, feedback)
        response = {"status": "approved", "checkpoint_id": req.checkpoint_id}
    else:
        hitl_manager.reject(req.checkpoint_id, feedback)
        response = {"status": "rejected", "checkpoint_id": req.checkpoint_id}
    if job_id_for_checkpoint:
        _record_job_event(
            str(job_id_for_checkpoint),
            "hitl_checkpoint_decision",
            checkpoint_id=req.checkpoint_id,
            checkpoint_stage=checkpoint.get("stage"),
            checkpoint_status=response["status"],
            approved=bool(req.approved),
            feedback=feedback,
            actor=actor,
            request_id=request_id_token,
        )

    if request_id_token:
        response["request_id"] = request_id_token
    _store_global_idempotency_response(
        scope="hitl_approve",
        request_id=request_id_token,
        fingerprint=idempotency_fingerprint,
        response=response,
        persisted=True,
    )
    return response


@app.get("/hitl/pending", response_model=HITLPendingListPublicResponse, response_model_exclude_none=True)
def list_pending_hitl(request: Request, donor_id: Optional[str] = None, tenant_id: Optional[str] = None):
    require_api_key_if_configured(request, for_read=True)
    resolved_tenant_id = _resolve_tenant_id(request, explicit_tenant=tenant_id, require_if_enabled=True)
    pending = hitl_manager.list_pending(donor_id)
    if resolved_tenant_id:
        filtered = []
        for checkpoint in pending:
            checkpoint_tenant_id = _checkpoint_tenant_id(checkpoint)
            if checkpoint_tenant_id != resolved_tenant_id:
                continue
            cp = dict(checkpoint)
            cp["tenant_id"] = checkpoint_tenant_id
            filtered.append(cp)
        pending = filtered
    return {
        "pending_count": len(pending),
        "checkpoints": [public_checkpoint_payload(cp) for cp in pending],
    }


@app.get("/ingest/recent", response_model=IngestRecentListPublicResponse, response_model_exclude_none=True)
def list_recent_ingests(
    request: Request,
    donor_id: Optional[str] = Query(default=None),
    tenant_id: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
):
    require_api_key_if_configured(request, for_read=True)
    resolved_tenant_id = _resolve_tenant_id(request, explicit_tenant=tenant_id, require_if_enabled=True)
    rows = _list_ingest_events(donor_id=donor_id, tenant_id=resolved_tenant_id, limit=limit)
    return public_ingest_recent_payload(rows, donor_id=(donor_id or None), tenant_id=resolved_tenant_id)


@app.get("/ingest/inventory", response_model=IngestInventoryPublicResponse, response_model_exclude_none=True)
def get_ingest_inventory(
    request: Request,
    donor_id: Optional[str] = Query(default=None),
    tenant_id: Optional[str] = Query(default=None),
):
    require_api_key_if_configured(request, for_read=True)
    resolved_tenant_id = _resolve_tenant_id(request, explicit_tenant=tenant_id, require_if_enabled=True)
    rows = _ingest_inventory(donor_id=donor_id, tenant_id=resolved_tenant_id)
    return public_ingest_inventory_payload(rows, donor_id=(donor_id or None), tenant_id=resolved_tenant_id)


@app.get("/ingest/inventory/export")
def export_ingest_inventory(
    request: Request,
    donor_id: Optional[str] = None,
    tenant_id: Optional[str] = Query(default=None),
    format: Literal["csv", "json"] = Query(default="csv"),
    gzip_enabled: bool = Query(default=False, alias="gzip"),
):
    require_api_key_if_configured(request, for_read=True)
    resolved_tenant_id = _resolve_tenant_id(request, explicit_tenant=tenant_id, require_if_enabled=True)
    rows = _ingest_inventory(donor_id=donor_id, tenant_id=resolved_tenant_id)
    payload = public_ingest_inventory_payload(rows, donor_id=(donor_id or None), tenant_id=resolved_tenant_id)
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
    tenant_id: Optional[str] = Form(None),
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

    resolved_tenant_id = _resolve_tenant_id(
        request,
        explicit_tenant=tenant_id,
        client_metadata=metadata,
        require_if_enabled=True,
    )
    namespace = _tenant_rag_namespace(strategy.get_rag_collection(), resolved_tenant_id)
    namespace_normalized = vector_store.normalize_namespace(namespace)
    upload_metadata: Dict[str, Any] = {
        "uploaded_filename": filename,
        "uploaded_content_type": content_type or "application/pdf",
        "donor_id": donor,
        "namespace_normalized": namespace_normalized,
    }
    if resolved_tenant_id:
        upload_metadata["tenant_id"] = resolved_tenant_id
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
        "tenant_id": resolved_tenant_id,
        "namespace": namespace,
        "namespace_normalized": namespace_normalized,
        "filename": filename,
        "result": result_payload,
    }


@app.post("/export")
def export_artifacts(req: ExportRequest, request: Request):
    require_api_key_if_configured(request)
    grounding_gate = _extract_export_grounding_gate(req)
    runtime_grounded_gate = _extract_export_runtime_grounded_quality_gate(req)
    if (
        _configured_export_require_grounded_gate_pass()
        and not req.allow_unsafe_export
        and (bool(runtime_grounded_gate.get("blocking")) or runtime_grounded_gate.get("passed") is False)
    ):
        raise HTTPException(
            status_code=409,
            detail={
                "reason": "runtime_grounded_quality_gate_block",
                "message": (
                    "Export blocked by runtime grounded quality gate pass policy. "
                    "Set allow_unsafe_export=true to override."
                ),
                "grounded_gate": runtime_grounded_gate,
            },
        )
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
    export_contract_gate = _evaluate_export_contract_gate(donor_id=donor_id, toc_draft=toc_draft)
    if req.production_export and not req.allow_unsafe_export and bool(export_contract_gate.get("blocking")):
        raise HTTPException(
            status_code=409,
            detail={
                "reason": "export_contract_policy_block",
                "message": (
                    "Export blocked by strict export contract policy "
                    "(missing required donor sections/sheets). "
                    "Set allow_unsafe_export=true to override, or use production_export=false."
                ),
                "export_contract_gate": export_contract_gate,
            },
        )
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
    export_headers = {
        "X-GrantFlow-Export-Contract-Mode": str(export_contract_gate.get("mode") or ""),
        "X-GrantFlow-Export-Contract-Status": str(export_contract_gate.get("status") or ""),
        "X-GrantFlow-Export-Contract-Summary": str(export_contract_gate.get("summary") or ""),
    }

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
            headers = {
                "Content-Disposition": "attachment; filename=proposal.docx",
                **export_headers,
            }
            return StreamingResponse(
                io.BytesIO(docx_bytes),
                media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                headers=headers,
            )

        if fmt == "xlsx" and xlsx_bytes is not None:
            headers = {
                "Content-Disposition": "attachment; filename=mel.xlsx",
                **export_headers,
            }
            return StreamingResponse(
                io.BytesIO(xlsx_bytes),
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers=headers,
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
                headers={
                    "Content-Disposition": "attachment; filename=grantflow_export.zip",
                    **export_headers,
                },
            )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    raise HTTPException(status_code=400, detail="Unsupported format")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=config.api_host, port=config.api_port, reload=config.debug)
