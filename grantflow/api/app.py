from __future__ import annotations

import io
import sys  # noqa: F401
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Any, AsyncIterator, Callable, Dict, Literal, Optional

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from openpyxl import load_workbook

from grantflow.api.constants import (
    CRITIC_FINDING_SLA_HOURS,
    GROUNDING_POLICY_MODES,
    REVIEW_COMMENT_DEFAULT_SLA_HOURS,
)
from grantflow.api.export_helpers import _resolve_export_inputs  # noqa: F401
from grantflow.api.public_views import (
    public_job_payload,
)
from grantflow.api.review_helpers import (
    _normalize_comment_sla_hours,
    _normalize_finding_sla_profile,
)
from grantflow.api.routers import include_api_routers
from grantflow.api.schemas import (
    ExportRequest,  # noqa: F401
    GenerateFromPresetRequest,
    GenerateRequest,
)
from grantflow.api.security import (
    install_openapi_api_key_security,
)
from grantflow.api.webhooks import send_job_webhook_event
from grantflow.core.config import config
from grantflow.core.stores import create_ingest_audit_store_from_env, create_job_store_from_env
from grantflow.core.version import __version__
from grantflow.exporters.donor_contracts import (
    DONOR_XLSX_PRIMARY_SHEET,
    evaluate_export_contract_gate,
    normalize_export_contract_policy_mode,
)
from grantflow.exporters.excel_builder import build_xlsx_from_logframe  # noqa: F401
from grantflow.exporters.template_profile import normalize_export_template_key
from grantflow.exporters.word_builder import build_docx_from_toc  # noqa: F401
from grantflow.memory_bank.ingest import ingest_pdf_to_namespace  # noqa: F401
from grantflow.memory_bank.vector_store import vector_store  # noqa: F401
from grantflow.swarm.findings import (
    finding_primary_id,
    state_critic_findings,
    write_state_critic_findings,
)
from grantflow.swarm.graph import grantflow_graph  # noqa: F401
from grantflow.swarm.hitl import HITLStatus, hitl_manager
from grantflow.swarm.state_contract import (
    normalize_state_contract,
    state_donor_id,
)

JOB_STORE = create_job_store_from_env()
INGEST_AUDIT_STORE = create_ingest_audit_store_from_env()
HITLStartAt = Literal["start", "architect", "mel", "critic"]
TERMINAL_JOB_STATUSES = {"done", "error", "canceled"}
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
HITL_HISTORY_EVENT_TYPES = {
    "status_changed",
    "resume_requested",
    "hitl_checkpoint_published",
    "hitl_checkpoint_decision",
    "hitl_checkpoint_canceled",
}


def _job_runner_mode() -> str:
    from grantflow.api.runtime_service import _job_runner_mode as _impl

    return _impl()


def _uses_inmemory_queue_runner() -> bool:
    from grantflow.api.runtime_service import _uses_inmemory_queue_runner as _impl

    return _impl()


def _uses_redis_queue_runner() -> bool:
    from grantflow.api.runtime_service import _uses_redis_queue_runner as _impl

    return _impl()


def _uses_queue_runner() -> bool:
    from grantflow.api.runtime_service import _uses_queue_runner as _impl

    return _impl()


def _dead_letter_alert_threshold() -> int:
    from grantflow.api.diagnostics_service import _dead_letter_alert_threshold as _impl

    return _impl()


def _dead_letter_alert_blocking() -> bool:
    from grantflow.api.diagnostics_service import _dead_letter_alert_blocking as _impl

    return _impl()


def _dispatcher_worker_heartbeat_policy_mode() -> str:
    from grantflow.api.diagnostics_service import _dispatcher_worker_heartbeat_policy_mode as _impl

    return _impl()


def _build_job_runner():
    from grantflow.api.runtime_service import _build_job_runner as _impl

    return _impl()


JOB_RUNNER = _build_job_runner()


def _job_store_mode() -> str:
    from grantflow.api.runtime_service import _job_store_mode as _impl

    return _impl()


def _hitl_store_mode() -> str:
    from grantflow.api.runtime_service import _hitl_store_mode as _impl

    return _impl()


def _ingest_store_mode() -> str:
    from grantflow.api.runtime_service import _ingest_store_mode as _impl

    return _impl()


def _validate_store_backend_alignment() -> None:
    from grantflow.api.runtime_service import _validate_store_backend_alignment as _impl

    _impl()


def _validate_tenant_authz_configuration() -> None:
    from grantflow.api.runtime_service import _validate_tenant_authz_configuration as _impl

    _impl()


def _validate_runtime_compatibility_configuration() -> None:
    from grantflow.api.runtime_service import _validate_runtime_compatibility_configuration as _impl

    _impl()


def _deployment_environment() -> str:
    from grantflow.api.runtime_service import _deployment_environment as _impl

    return _impl()


def _is_production_environment() -> bool:
    from grantflow.api.runtime_service import _is_production_environment as _impl

    return _impl()


def _require_api_key_on_startup() -> bool:
    from grantflow.api.runtime_service import _require_api_key_on_startup as _impl

    return _impl()


def _validate_api_key_startup_security() -> None:
    from grantflow.api.runtime_service import _validate_api_key_startup_security as _impl

    _impl()


@asynccontextmanager
async def _app_lifespan(_: FastAPI) -> AsyncIterator[None]:
    from grantflow.api.runtime_service import _app_lifespan as _impl

    async with _impl(_):
        yield


app = FastAPI(
    title="GrantFlow API",
    description="Enterprise-grade grant proposal automation",
    version=__version__,
    lifespan=_app_lifespan,
)


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _dispatch_pipeline_task(background_tasks: BackgroundTasks, fn: Callable[..., None], *args: Any) -> str:
    from grantflow.api.pipeline_jobs import _dispatch_pipeline_task as _impl

    return _impl(background_tasks, fn, *args)


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
    from grantflow.api.idempotency import _normalize_request_id as _impl

    return _impl(value)


def _resolve_request_id(request: Request, explicit_request_id: Optional[str] = None) -> Optional[str]:
    from grantflow.api.idempotency import _resolve_request_id as _impl

    return _impl(request, explicit_request_id)


def _idempotency_fingerprint(payload: Dict[str, Any]) -> str:
    from grantflow.api.idempotency import _idempotency_fingerprint as _impl

    return _impl(payload)


def _idempotency_record_key(scope: str, request_id: str) -> str:
    from grantflow.api.idempotency import _idempotency_record_key as _impl

    return _impl(scope, request_id)


def _idempotency_records(job: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    from grantflow.api.idempotency import _idempotency_records as _impl

    return _impl(job)


def _idempotency_replay_response(
    job: Dict[str, Any],
    *,
    scope: str,
    request_id: Optional[str],
    fingerprint: str,
) -> Optional[Dict[str, Any]]:
    from grantflow.api.idempotency import _idempotency_replay_response as _impl

    return _impl(job, scope=scope, request_id=request_id, fingerprint=fingerprint)


def _store_idempotency_response(
    job_id: str,
    *,
    scope: str,
    request_id: Optional[str],
    fingerprint: str,
    response: Dict[str, Any],
    persisted: bool,
) -> None:
    from grantflow.api.idempotency import _store_idempotency_response as _impl

    _impl(
        job_id,
        scope=scope,
        request_id=request_id,
        fingerprint=fingerprint,
        response=response,
        persisted=persisted,
    )


def _global_idempotency_record_key(scope: str, request_id: str) -> str:
    from grantflow.api.idempotency import _global_idempotency_record_key as _impl

    return _impl(scope, request_id)


def _global_idempotency_replay_response(
    *,
    scope: str,
    request_id: Optional[str],
    fingerprint: str,
) -> Optional[Dict[str, Any]]:
    from grantflow.api.idempotency import _global_idempotency_replay_response as _impl

    return _impl(scope=scope, request_id=request_id, fingerprint=fingerprint)


def _store_global_idempotency_response(
    *,
    scope: str,
    request_id: Optional[str],
    fingerprint: str,
    response: Dict[str, Any],
    persisted: bool,
) -> None:
    from grantflow.api.idempotency import _store_global_idempotency_response as _impl

    _impl(
        scope=scope,
        request_id=request_id,
        fingerprint=fingerprint,
        response=response,
        persisted=persisted,
    )


def _append_job_event_records(
    previous: Optional[Dict[str, Any]],
    next_payload: Dict[str, Any],
) -> Dict[str, Any]:
    from grantflow.api.job_store_service import _append_job_event_records as _impl

    return _impl(previous, next_payload)


def _record_job_event(job_id: str, event_type: str, **fields: Any) -> None:
    from grantflow.api.job_store_service import _record_job_event as _impl

    _impl(job_id, event_type, **fields)


def _record_ingest_event(
    *,
    donor_id: str,
    namespace: str,
    filename: str,
    content_type: str,
    metadata: Optional[Dict[str, Any]] = None,
    result: Optional[Dict[str, Any]] = None,
) -> None:
    from grantflow.api.job_store_service import _record_ingest_event as _impl

    _impl(
        donor_id=donor_id,
        namespace=namespace,
        filename=filename,
        content_type=content_type,
        metadata=metadata,
        result=result,
    )


def _configured_tenant_authz_configuration_policy_mode() -> str:
    from grantflow.api.diagnostics_service import _configured_tenant_authz_configuration_policy_mode as _impl

    return _impl()


def _tenant_authz_configuration_status() -> dict[str, Any]:
    from grantflow.api.diagnostics_service import _tenant_authz_configuration_status as _impl

    return _impl()


def _list_ingest_events(
    *,
    donor_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
    limit: int = 50,
) -> list[Dict[str, Any]]:
    from grantflow.api.job_store_service import _list_ingest_events as _impl

    return _impl(donor_id=donor_id, tenant_id=tenant_id, limit=limit)


def _ingest_inventory(*, donor_id: Optional[str] = None, tenant_id: Optional[str] = None) -> list[Dict[str, Any]]:
    from grantflow.api.job_store_service import _ingest_inventory as _impl

    return _impl(donor_id=donor_id, tenant_id=tenant_id)


def _dedupe_doc_families(values: list[Any]) -> list[str]:
    from grantflow.api.preflight_service import _dedupe_doc_families as _impl

    return _impl(values)


def _preflight_expected_doc_families(
    *,
    donor_id: str,
    client_metadata: Optional[Dict[str, Any]],
) -> list[str]:
    from grantflow.api.preflight_service import _preflight_expected_doc_families as _impl

    return _impl(donor_id=donor_id, client_metadata=client_metadata)


def _preflight_doc_family_min_uploads_map(
    *,
    expected_doc_families: list[str],
    client_metadata: Optional[Dict[str, Any]],
) -> Dict[str, int]:
    from grantflow.api.preflight_service import _preflight_doc_family_min_uploads_map as _impl

    return _impl(
        expected_doc_families=expected_doc_families,
        client_metadata=client_metadata,
    )


def _preflight_doc_family_depth_profile(
    *,
    expected_doc_families: list[str],
    doc_family_counts: Dict[str, Any],
    min_uploads_by_family: Dict[str, int],
) -> Dict[str, Any]:
    from grantflow.api.preflight_service import _preflight_doc_family_depth_profile as _impl

    return _impl(
        expected_doc_families=expected_doc_families,
        doc_family_counts=doc_family_counts,
        min_uploads_by_family=min_uploads_by_family,
    )


def _preflight_input_context(client_metadata: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    from grantflow.api.preflight_service import _preflight_input_context as _impl

    return _impl(client_metadata)


def _preflight_severity_max(severities: list[str]) -> str:
    from grantflow.api.preflight_service import _preflight_severity_max as _impl

    return _impl(severities)


def _normalize_grounding_policy_mode(raw_mode: Any) -> str:
    mode = str(raw_mode or "warn").strip().lower()
    if mode not in GROUNDING_POLICY_MODES:
        return "warn"
    return mode


def _configured_runtime_compatibility_policy_mode() -> str:
    from grantflow.api.diagnostics_service import _configured_runtime_compatibility_policy_mode as _impl

    return _impl()


def _python_runtime_compatibility_status() -> Dict[str, Any]:
    from grantflow.api.diagnostics_service import _python_runtime_compatibility_status as _impl

    return _impl()


def _configured_preflight_grounding_policy_mode() -> str:
    from grantflow.api.preflight_service import _configured_preflight_grounding_policy_mode as _impl

    return _impl()


def _configured_runtime_grounded_quality_gate_mode() -> str:
    from grantflow.api.runtime_grounded_gate_service import _configured_runtime_grounded_quality_gate_mode as _impl

    return _impl()


def _runtime_grounded_quality_gate_thresholds() -> Dict[str, Any]:
    from grantflow.api.runtime_grounded_gate_service import _runtime_grounded_quality_gate_thresholds as _impl

    return _impl()


def _runtime_grounded_gate_section(citation: Dict[str, Any]) -> str:
    from grantflow.api.runtime_grounded_gate_service import _runtime_grounded_gate_section as _impl

    return _impl(citation)


def _runtime_grounded_gate_evidence_row(citation: Dict[str, Any]) -> Dict[str, Any]:
    from grantflow.api.runtime_grounded_gate_service import _runtime_grounded_gate_evidence_row as _impl

    return _impl(citation)


def _evaluate_runtime_grounded_quality_gate_from_state(state: Any) -> Dict[str, Any]:
    from grantflow.api.runtime_grounded_gate_service import (
        _evaluate_runtime_grounded_quality_gate_from_state as _impl,
    )

    return _impl(state)


def _configured_mel_grounding_policy_mode() -> str:
    from grantflow.api.grounding_policy_service import _configured_mel_grounding_policy_mode as _impl

    return _impl()


def _mel_grounding_policy_thresholds() -> Dict[str, Any]:
    from grantflow.api.grounding_policy_service import _mel_grounding_policy_thresholds as _impl

    return _impl()


def _evaluate_mel_grounding_policy_from_state(state: Any) -> Dict[str, Any]:
    from grantflow.api.grounding_policy_service import _evaluate_mel_grounding_policy_from_state as _impl

    return _impl(state)


def _configured_export_grounding_policy_mode() -> str:
    from grantflow.api.grounding_policy_service import _configured_export_grounding_policy_mode as _impl

    return _impl()


def _configured_export_require_grounded_gate_pass() -> bool:
    from grantflow.api.grounding_policy_service import _configured_export_require_grounded_gate_pass as _impl

    return _impl()


def _export_grounding_policy_thresholds() -> Dict[str, Any]:
    from grantflow.api.grounding_policy_service import _export_grounding_policy_thresholds as _impl

    return _impl()


def _evaluate_export_grounding_policy(citations: list[dict[str, Any]]) -> Dict[str, Any]:
    from grantflow.api.grounding_policy_service import _evaluate_export_grounding_policy as _impl

    return _impl(citations)


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
    workbook_primary_sheet_headers: Optional[list[str]] = None,
) -> Dict[str, Any]:
    return evaluate_export_contract_gate(
        donor_id=donor_id,
        toc_payload=toc_draft,
        policy_mode=_configured_export_contract_policy_mode(),
        workbook_sheetnames=workbook_sheetnames,
        workbook_primary_sheet_headers=workbook_primary_sheet_headers,
    )


def _xlsx_contract_validation_context(
    xlsx_payload: bytes,
    *,
    donor_id: str,
) -> tuple[list[str], list[str]]:
    workbook = load_workbook(io.BytesIO(xlsx_payload), data_only=True, read_only=True)
    try:
        sheetnames = list(workbook.sheetnames)
        donor_key = normalize_export_template_key(donor_id)
        primary_sheet = DONOR_XLSX_PRIMARY_SHEET.get(donor_key)
        if not primary_sheet or primary_sheet not in workbook.sheetnames:
            return sheetnames, []
        sheet = workbook[primary_sheet]
        header_row = next(sheet.iter_rows(min_row=1, max_row=1, values_only=True), ())
        headers = [str(value).strip() for value in header_row if str(value or "").strip()]
        return sheetnames, headers
    finally:
        workbook.close()


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
    from grantflow.api.preflight_service import _preflight_grounding_policy_thresholds as _impl

    return _impl()


def _estimate_preflight_architect_claims(
    *,
    donor_id: str,
    strategy: Any,
    namespace: str,
    input_context: Optional[Dict[str, Any]],
    tenant_id: Optional[str] = None,
    architect_rag_enabled: bool = True,
) -> Dict[str, Any]:
    from grantflow.api.preflight_service import _estimate_preflight_architect_claims as _impl

    return _impl(
        donor_id=donor_id,
        strategy=strategy,
        namespace=namespace,
        input_context=input_context,
        tenant_id=tenant_id,
        architect_rag_enabled=architect_rag_enabled,
    )


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
    from grantflow.api.preflight_service import _build_preflight_grounding_policy as _impl

    return _impl(
        coverage_rate=coverage_rate,
        depth_coverage_rate=depth_coverage_rate,
        namespace_empty=namespace_empty,
        inventory_total_uploads=inventory_total_uploads,
        missing_doc_families=missing_doc_families,
        depth_gap_doc_families=depth_gap_doc_families,
        architect_claims=architect_claims,
    )


def _build_generate_preflight(
    *,
    donor_id: str,
    strategy: Any,
    client_metadata: Optional[Dict[str, Any]],
    tenant_id: Optional[str] = None,
    architect_rag_enabled: bool = True,
) -> Dict[str, Any]:
    from grantflow.api.preflight_service import _build_generate_preflight as _impl

    return _impl(
        donor_id=donor_id,
        strategy=strategy,
        client_metadata=client_metadata,
        tenant_id=tenant_id,
        architect_rag_enabled=architect_rag_enabled,
    )


def _set_job(job_id: str, payload: Dict[str, Any]) -> None:
    from grantflow.api.job_store_service import _set_job as _impl

    _impl(job_id, payload)


def _update_job(job_id: str, **patch: Any) -> Dict[str, Any]:
    from grantflow.api.job_store_service import _update_job as _impl

    return _impl(job_id, **patch)


def _get_job(job_id: str) -> Optional[Dict[str, Any]]:
    from grantflow.api.job_store_service import _get_job as _impl

    return _impl(job_id)


def _list_jobs() -> Dict[str, Dict[str, Any]]:
    from grantflow.api.job_store_service import _list_jobs as _impl

    return _impl()


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


def _record_hitl_feedback_in_state(state: dict, checkpoint: Dict[str, Any]) -> None:
    from grantflow.api.pipeline_jobs import _record_hitl_feedback_in_state as _impl

    _impl(state, checkpoint)


def _checkpoint_status_token(checkpoint: Dict[str, Any]) -> str:
    from grantflow.api.pipeline_jobs import _checkpoint_status_token as _impl

    return _impl(checkpoint)


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
    from grantflow.api.review_mutations import _recompute_review_workflow_sla as _impl

    return _impl(
        job_id,
        actor=actor,
        finding_sla_hours_override=finding_sla_hours_override,
        default_comment_sla_hours=default_comment_sla_hours,
        use_saved_profile=use_saved_profile,
    )


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
    from grantflow.api.review_mutations import _set_critic_fatal_flaw_status as _impl

    return _impl(
        job_id,
        finding_id=finding_id,
        next_status=next_status,
        actor=actor,
        dry_run=dry_run,
        if_match_status=if_match_status,
        request_id=request_id,
    )


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
    from grantflow.api.review_mutations import _set_critic_fatal_flaws_status_bulk as _impl

    return _impl(
        job_id,
        next_status=next_status,
        actor=actor,
        dry_run=dry_run,
        request_id=request_id,
        if_match_status=if_match_status,
        apply_to_all=apply_to_all,
        finding_status=finding_status,
        severity=severity,
        section=section,
        finding_ids=finding_ids,
    )


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
    from grantflow.api.review_mutations import _append_review_comment as _impl

    return _impl(
        job_id,
        section=section,
        message=message,
        author=author,
        version_id=version_id,
        linked_finding_id=linked_finding_id,
        linked_finding_severity=linked_finding_severity,
        request_id=request_id,
    )


def _set_review_comment_status(
    job_id: str,
    *,
    comment_id: str,
    next_status: str,
    actor: Optional[str] = None,
    request_id: Optional[str] = None,
) -> Dict[str, Any]:
    from grantflow.api.review_mutations import _set_review_comment_status as _impl

    return _impl(
        job_id,
        comment_id=comment_id,
        next_status=next_status,
        actor=actor,
        request_id=request_id,
    )


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
        checkpoint_stage = str(checkpoint.get("stage") or "").strip().lower() if isinstance(checkpoint, dict) else ""
        checkpoint_status = _checkpoint_status_token(checkpoint) if isinstance(checkpoint, dict) else ""
        if not checkpoint or checkpoint_status != HITLStatus.PENDING.value or checkpoint_stage != stage:
            if isinstance(checkpoint, dict) and checkpoint_status == HITLStatus.PENDING.value and checkpoint_id:
                hitl_manager.cancel(checkpoint_id, "Superseded by new HITL checkpoint")
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
    from grantflow.api.pipeline_jobs import _run_pipeline_to_completion as _impl

    _impl(job_id, initial_state)


def _run_pipeline_to_completion_by_job_id(job_id: str) -> None:
    from grantflow.api.pipeline_jobs import _run_pipeline_to_completion_by_job_id as _impl

    _impl(job_id)


def _run_hitl_pipeline(job_id: str, state: dict, start_at: HITLStartAt) -> None:
    from grantflow.api.pipeline_jobs import _run_hitl_pipeline as _impl

    _impl(job_id, state, start_at)


def _run_hitl_pipeline_by_job_id(job_id: str, start_at: HITLStartAt) -> None:
    from grantflow.api.pipeline_jobs import _run_hitl_pipeline_by_job_id as _impl

    _impl(job_id, start_at)


def _resume_target_from_checkpoint(checkpoint: Dict[str, Any], default_resume_from: str | None) -> HITLStartAt:
    from grantflow.api.pipeline_jobs import _resume_target_from_checkpoint as _impl

    return _impl(checkpoint, default_resume_from)


def _clear_hitl_runtime_state(state: dict, *, clear_pending: bool) -> None:
    from grantflow.api.pipeline_jobs import _clear_hitl_runtime_state as _impl

    _impl(state, clear_pending=clear_pending)


def _configuration_warnings() -> list[dict[str, Any]]:
    from grantflow.api.diagnostics_service import _configuration_warnings as _impl

    return _impl()


def _health_diagnostics() -> dict[str, Any]:
    from grantflow.api.diagnostics_service import _health_diagnostics as _impl

    return _impl()


def _vector_store_readiness() -> dict[str, Any]:
    from grantflow.api.diagnostics_service import _vector_store_readiness as _impl

    return _impl()


def _redis_queue_admin_runner(required_methods: tuple[str, ...]) -> Any:
    if not _uses_redis_queue_runner():
        raise HTTPException(
            status_code=409,
            detail="Dead-letter queue management requires GRANTFLOW_JOB_RUNNER_MODE=redis_queue",
        )
    runner = JOB_RUNNER
    for method_name in required_methods:
        if not callable(getattr(runner, method_name, None)):
            raise HTTPException(
                status_code=409, detail="Redis queue admin operations are unavailable in current runner"
            )
    return runner


def _generate_preset_rows_for_public() -> list[dict[str, Any]]:
    from grantflow.api.presets_service import _generate_preset_rows_for_public as _impl

    return _impl()


def _demo_preset_bundle_payload() -> dict[str, Any]:
    from grantflow.api.presets_service import _demo_preset_bundle_payload as _impl

    return _impl()


def _resolve_preflight_request_context(
    *,
    request: Request,
    donor_id: str,
    tenant_id: Optional[str] = None,
    client_metadata: Optional[Dict[str, Any]] = None,
    input_context: Optional[Dict[str, Any]] = None,
    expected_doc_families: Optional[list[str]] = None,
) -> tuple[str, Any, Optional[Dict[str, Any]]]:
    from grantflow.api.presets_service import _resolve_preflight_request_context as _impl

    return _impl(
        request=request,
        donor_id=donor_id,
        tenant_id=tenant_id,
        client_metadata=client_metadata,
        input_context=input_context,
        expected_doc_families=expected_doc_families,
    )


def _resolve_generate_payload_from_preset(
    preset_key: str,
    *,
    preset_type: Literal["auto", "legacy", "rbm"],
) -> tuple[str, Dict[str, Any]]:
    from grantflow.api.presets_service import _resolve_generate_payload_from_preset as _impl

    return _impl(preset_key, preset_type=preset_type)


def _build_generate_request_from_preset(req: GenerateFromPresetRequest) -> tuple[GenerateRequest, str]:
    from grantflow.api.presets_service import _build_generate_request_from_preset as _impl

    return _impl(req)


async def _dispatch_generate_from_preset(
    req: GenerateFromPresetRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    *,
    request_id: Optional[str] = None,
):
    from grantflow.api.presets_service import _dispatch_generate_from_preset as _impl

    return await _impl(req, background_tasks, request, request_id=request_id)


def _load_route_modules() -> None:
    from grantflow.api.routes import exports as _exports_routes
    from grantflow.api.routes import ingest as _ingest_routes
    from grantflow.api.routes import jobs as _jobs_routes
    from grantflow.api.routes import portfolio_read as _portfolio_read_routes
    from grantflow.api.routes import presets as _presets_routes
    from grantflow.api.routes import queue_admin as _queue_admin_routes
    from grantflow.api.routes import review as _review_routes
    from grantflow.api.routes import system as _system_routes

    _ = (
        _exports_routes,
        _ingest_routes,
        _jobs_routes,
        _portfolio_read_routes,
        _presets_routes,
        _queue_admin_routes,
        _review_routes,
        _system_routes,
    )


_load_route_modules()
include_api_routers(app)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=config.api_host, port=config.api_port, reload=config.debug)
