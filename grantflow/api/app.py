from __future__ import annotations

import sys  # noqa: F401
from contextlib import asynccontextmanager
from typing import AsyncIterator, Literal

from fastapi import FastAPI

from grantflow.api.compat_exports import (  # noqa: F401
    _append_runtime_grounded_quality_gate_finding,
    _attach_export_contract_gate,
    _build_generate_request_from_preset,
    _build_job_runner,
    _checkpoint_status_token,
    _clear_hitl_runtime_state,
    _comment_sla_hours,
    _configuration_warnings,
    _configured_tenant_authz_configuration_policy_mode,
    _dead_letter_alert_blocking,
    _dead_letter_alert_threshold,
    _demo_preset_bundle_payload,
    _deployment_environment,
    _dispatch_generate_from_preset,
    _dispatch_job_webhook_for_status_change,
    _dispatch_pipeline_task,
    _dispatcher_worker_heartbeat_policy_mode,
    _ensure_comment_due_at,
    _ensure_finding_due_at,
    _find_critic_fatal_flaw,
    _find_job_by_checkpoint_id,
    _finding_actor_from_request,
    _finding_sla_hours,
    _generate_preset_rows_for_public,
    _grounding_gate_block_reason,
    _health_diagnostics,
    _hitl_history_payload,
    _hitl_store_mode,
    _ingest_store_mode,
    _is_hitl_history_event,
    _is_production_environment,
    _job_draft_version_exists_for_section,
    _job_is_canceled,
    _job_runner_mode,
    _job_store_mode,
    _iso_plus_hours,
    _linked_finding_severity,
    _mel_grounding_policy_block_reason,
    _normalize_critic_fatal_flaws_for_job,
    _normalize_review_comments_for_job,
    _parse_iso_utc,
    _pause_for_hitl,
    _record_hitl_feedback_in_state,
    _recompute_review_workflow_sla,
    _redis_queue_admin_runner,
    _require_api_key_on_startup,
    _require_persistent_stores_on_startup,
    _resolve_generate_payload_from_preset,
    _resolve_preflight_request_context,
    _resolve_sla_profile_for_recompute,
    _resume_target_from_checkpoint,
    _run_hitl_pipeline,
    _run_hitl_pipeline_by_job_id,
    _run_pipeline_to_completion,
    _run_pipeline_to_completion_by_job_id,
    _runtime_grounded_quality_gate_block_reason,
    _set_critic_fatal_flaw_status,
    _set_critic_fatal_flaws_status_bulk,
    _set_review_comment_status,
    _state_grounding_gate,
    _state_runtime_grounded_quality_gate,
    _tenant_authz_configuration_status,
    _uses_inmemory_queue_runner,
    _uses_queue_runner,
    _uses_redis_queue_runner,
    _utcnow_iso,
    _validate_api_key_startup_security,
    _validate_persistent_store_startup_security,
    _validate_runtime_compatibility_configuration,
    _validate_store_backend_alignment,
    _validate_tenant_authz_configuration,
    _vector_store_readiness,
)
from grantflow.api.constants import (  # noqa: F401
    HITL_HISTORY_EVENT_TYPES,
    RUNTIME_PIPELINE_STATE_KEYS,
    STATUS_WEBHOOK_EVENTS,
    TERMINAL_JOB_STATUSES,
)
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
from grantflow.api.schemas import ExportRequest  # noqa: F401
from grantflow.api.security import install_openapi_api_key_security
from grantflow.api.webhooks import send_job_webhook_event  # noqa: F401
from grantflow.core.config import config
from grantflow.core.stores import create_ingest_audit_store_from_env, create_job_store_from_env
from grantflow.core.version import __version__
from grantflow.exporters.excel_builder import build_xlsx_from_logframe  # noqa: F401
from grantflow.exporters.word_builder import build_docx_from_toc  # noqa: F401
from grantflow.memory_bank.ingest import ingest_pdf_to_namespace  # noqa: F401
from grantflow.memory_bank.vector_store import vector_store  # noqa: F401
from grantflow.swarm.graph import grantflow_graph  # noqa: F401
from grantflow.swarm.hitl import hitl_manager  # noqa: F401
from grantflow.swarm.state_contract import normalize_state_contract  # noqa: F401

JOB_STORE = create_job_store_from_env()
INGEST_AUDIT_STORE = create_ingest_audit_store_from_env()
HITLStartAt = Literal["start", "architect", "mel", "critic"]
JOB_RUNNER = _build_job_runner()


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

install_openapi_api_key_security(app)


def _import_route_modules_for_registration() -> None:
    """Import route modules for their router side effects before include_api_routers()."""
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


_import_route_modules_for_registration()
include_api_routers(app)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=config.api_host, port=config.api_port, reload=config.debug)
