from __future__ import annotations

import sys  # noqa: F401
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, AsyncIterator, Callable, Dict, Literal, Optional

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from grantflow.api.diagnostics_service import (  # noqa: F401
    _configured_runtime_compatibility_policy_mode,
    _python_runtime_compatibility_status,
)
from grantflow.api.export_helpers import _resolve_export_inputs  # noqa: F401
from grantflow.api.idempotency_store_facade import (  # noqa: F401
    _append_job_event_records,
    _get_job,
    _global_idempotency_record_key,
    _global_idempotency_replay_response,
    _idempotency_fingerprint,
    _idempotency_record_key,
    _idempotency_records,
    _idempotency_replay_response,
    _ingest_inventory,
    _list_ingest_events,
    _list_jobs,
    _normalize_request_id,
    _record_ingest_event,
    _record_job_event,
    _resolve_request_id,
    _set_job,
    _store_global_idempotency_response,
    _store_idempotency_response,
    _update_job,
)
from grantflow.api.orchestrator_service import (  # noqa: F401
    _build_generate_preflight,
    _build_preflight_grounding_policy,
    _configured_export_contract_policy_mode,
    _configured_export_grounding_policy_mode,
    _configured_export_require_grounded_gate_pass,
    _configured_mel_grounding_policy_mode,
    _configured_preflight_grounding_policy_mode,
    _configured_runtime_grounded_quality_gate_mode,
    _dedupe_doc_families,
    _estimate_preflight_architect_claims,
    _evaluate_export_contract_gate,
    _evaluate_export_grounding_policy,
    _evaluate_mel_grounding_policy_from_state,
    _evaluate_runtime_grounded_quality_gate_from_state,
    _export_grounding_policy_thresholds,
    _mel_grounding_policy_thresholds,
    _normalize_grounding_policy_mode,
    _preflight_doc_family_depth_profile,
    _preflight_doc_family_min_uploads_map,
    _preflight_expected_doc_families,
    _preflight_grounding_policy_thresholds,
    _preflight_input_context,
    _preflight_severity_max,
    _runtime_grounded_gate_evidence_row,
    _runtime_grounded_gate_section,
    _runtime_grounded_quality_gate_thresholds,
    _xlsx_contract_validation_context,
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
from grantflow.api.webhooks import send_job_webhook_event  # noqa: F401
from grantflow.core.config import config
from grantflow.core.stores import create_ingest_audit_store_from_env, create_job_store_from_env
from grantflow.core.version import __version__
from grantflow.exporters.excel_builder import build_xlsx_from_logframe  # noqa: F401
from grantflow.exporters.word_builder import build_docx_from_toc  # noqa: F401
from grantflow.memory_bank.ingest import ingest_pdf_to_namespace  # noqa: F401
from grantflow.memory_bank.vector_store import vector_store  # noqa: F401
from grantflow.swarm.hitl import hitl_manager  # noqa: F401
from grantflow.swarm.graph import grantflow_graph  # noqa: F401
from grantflow.swarm.state_contract import (
    normalize_state_contract,  # noqa: F401
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
    from grantflow.api.review_runtime_helpers import _utcnow_iso as _impl

    return _impl()


def _dispatch_pipeline_task(background_tasks: BackgroundTasks, fn: Callable[..., None], *args: Any) -> str:
    from grantflow.api.pipeline_jobs import _dispatch_pipeline_task as _impl

    return _impl(background_tasks, fn, *args)


def _parse_iso_utc(value: Any) -> Optional[datetime]:
    from grantflow.api.review_runtime_helpers import _parse_iso_utc as _impl

    return _impl(value)


def _iso_plus_hours(base_ts: Optional[str], hours: int) -> str:
    from grantflow.api.review_runtime_helpers import _iso_plus_hours as _impl

    return _impl(base_ts, hours)


def _finding_sla_hours(severity: Any, *, finding_sla_hours_override: Optional[Dict[str, int]] = None) -> int:
    from grantflow.api.review_runtime_helpers import _finding_sla_hours as _impl

    return _impl(severity, finding_sla_hours_override=finding_sla_hours_override)


def _comment_sla_hours(
    *,
    linked_finding_severity: Optional[str] = None,
    finding_sla_hours_override: Optional[Dict[str, int]] = None,
    default_comment_sla_hours: Optional[int] = None,
) -> int:
    from grantflow.api.review_runtime_helpers import _comment_sla_hours as _impl

    return _impl(
        linked_finding_severity=linked_finding_severity,
        finding_sla_hours_override=finding_sla_hours_override,
        default_comment_sla_hours=default_comment_sla_hours,
    )


def _finding_actor_from_request(request: Request) -> str:
    from grantflow.api.review_runtime_helpers import _finding_actor_from_request as _impl

    return _impl(request)


def _configured_tenant_authz_configuration_policy_mode() -> str:
    from grantflow.api.diagnostics_service import _configured_tenant_authz_configuration_policy_mode as _impl

    return _impl()


def _tenant_authz_configuration_status() -> dict[str, Any]:
    from grantflow.api.diagnostics_service import _tenant_authz_configuration_status as _impl

    return _impl()


def _attach_export_contract_gate(state: Any) -> Dict[str, Any]:
    from grantflow.api.runtime_gate_helpers import _attach_export_contract_gate as _impl

    return _impl(state)


def _find_job_by_checkpoint_id(checkpoint_id: str) -> tuple[Optional[str], Optional[Dict[str, Any]]]:
    from grantflow.api.review_service import _find_job_by_checkpoint_id as _impl

    return _impl(checkpoint_id)


def _is_hitl_history_event(event: Dict[str, Any]) -> bool:
    from grantflow.api.review_service import _is_hitl_history_event as _impl

    return _impl(event)


def _hitl_history_payload(
    job_id: str,
    job: Dict[str, Any],
    *,
    event_type: Optional[str] = None,
    checkpoint_id: Optional[str] = None,
) -> Dict[str, Any]:
    from grantflow.api.review_service import _hitl_history_payload as _impl

    return _impl(job_id, job, event_type=event_type, checkpoint_id=checkpoint_id)


def _record_hitl_feedback_in_state(state: dict, checkpoint: Dict[str, Any]) -> None:
    from grantflow.api.pipeline_jobs import _record_hitl_feedback_in_state as _impl

    _impl(state, checkpoint)


def _checkpoint_status_token(checkpoint: Dict[str, Any]) -> str:
    from grantflow.api.pipeline_jobs import _checkpoint_status_token as _impl

    return _impl(checkpoint)


def _state_grounding_gate(state: Any) -> Dict[str, Any]:
    from grantflow.api.runtime_gate_helpers import _state_grounding_gate as _impl

    return _impl(state)


def _state_runtime_grounded_quality_gate(state: Any) -> Dict[str, Any]:
    from grantflow.api.runtime_gate_helpers import _state_runtime_grounded_quality_gate as _impl

    return _impl(state)


def _append_runtime_grounded_quality_gate_finding(state: dict, gate: Dict[str, Any]) -> None:
    from grantflow.api.runtime_gate_helpers import _append_runtime_grounded_quality_gate_finding as _impl

    _impl(state, gate)


def _grounding_gate_block_reason(state: Any) -> Optional[str]:
    from grantflow.api.runtime_gate_helpers import _grounding_gate_block_reason as _impl

    return _impl(state)


def _runtime_grounded_quality_gate_block_reason(state: Any) -> Optional[str]:
    from grantflow.api.runtime_gate_helpers import _runtime_grounded_quality_gate_block_reason as _impl

    return _impl(state)


def _mel_grounding_policy_block_reason(state: Any) -> Optional[str]:
    from grantflow.api.runtime_gate_helpers import _mel_grounding_policy_block_reason as _impl

    return _impl(state)


def _job_draft_version_exists_for_section(job: Dict[str, Any], *, section: str, version_id: str) -> bool:
    from grantflow.api.review_service import _job_draft_version_exists_for_section as _impl

    return _impl(job, section=section, version_id=version_id)


def _resolve_sla_profile_for_recompute(
    *,
    job: Dict[str, Any],
    finding_sla_hours_override: Optional[Dict[str, Any]],
    default_comment_sla_hours: Optional[Any],
    use_saved_profile: bool,
) -> tuple[Dict[str, int], int]:
    from grantflow.api.review_service import _resolve_sla_profile_for_recompute as _impl

    return _impl(
        job=job,
        finding_sla_hours_override=finding_sla_hours_override,
        default_comment_sla_hours=default_comment_sla_hours,
        use_saved_profile=use_saved_profile,
    )


def _ensure_finding_due_at(
    item: Dict[str, Any],
    *,
    now_iso: str,
    reset: bool = False,
    finding_sla_hours_override: Optional[Dict[str, int]] = None,
) -> Dict[str, Any]:
    from grantflow.api.review_service import _ensure_finding_due_at as _impl

    return _impl(
        item,
        now_iso=now_iso,
        reset=reset,
        finding_sla_hours_override=finding_sla_hours_override,
    )


def _normalize_critic_fatal_flaws_for_job(job_id: str) -> Optional[Dict[str, Any]]:
    from grantflow.api.review_service import _normalize_critic_fatal_flaws_for_job as _impl

    return _impl(job_id)


def _normalize_review_comments_for_job(job_id: str) -> Optional[Dict[str, Any]]:
    from grantflow.api.review_service import _normalize_review_comments_for_job as _impl

    return _impl(job_id)


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
    from grantflow.api.review_service import _find_critic_fatal_flaw as _impl

    return _impl(job, finding_id)


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
    from grantflow.api.review_service import _linked_finding_severity as _impl

    return _impl(job, linked_finding_id)


def _ensure_comment_due_at(
    comment: Dict[str, Any],
    *,
    job: Dict[str, Any],
    now_iso: str,
    reset: bool = False,
    finding_sla_hours_override: Optional[Dict[str, int]] = None,
    default_comment_sla_hours: Optional[int] = None,
) -> Dict[str, Any]:
    from grantflow.api.review_service import _ensure_comment_due_at as _impl

    return _impl(
        comment,
        job=job,
        now_iso=now_iso,
        reset=reset,
        finding_sla_hours_override=finding_sla_hours_override,
        default_comment_sla_hours=default_comment_sla_hours,
    )


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
    from grantflow.api.review_service import _job_is_canceled as _impl

    return _impl(job_id)


def _dispatch_job_webhook_for_status_change(
    job_id: str,
    previous: Optional[Dict[str, Any]],
    current: Optional[Dict[str, Any]],
) -> None:
    from grantflow.api.review_service import _dispatch_job_webhook_for_status_change as _impl

    _impl(job_id, previous, current)


install_openapi_api_key_security(app)


def _pause_for_hitl(job_id: str, state: dict, stage: Literal["toc", "logframe"], resume_from: HITLStartAt) -> None:
    from grantflow.api.review_service import _pause_for_hitl as _impl

    _impl(job_id, state, stage=stage, resume_from=resume_from)


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
