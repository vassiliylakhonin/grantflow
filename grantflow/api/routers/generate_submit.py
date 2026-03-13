from __future__ import annotations

from typing import Any, Callable, Optional

from fastapi import APIRouter, BackgroundTasks, Request

from grantflow.api.schemas import GeneratePreflightRequest, GenerateRequest
from grantflow.api.services.generate_service import handle_generate, handle_generate_preflight

router = APIRouter()

_require_api_key_if_configured: Callable[..., None] | None = None
_resolve_tenant_id: Callable[..., Optional[str]] | None = None
_donor_get_strategy: Callable[[str], Any] | None = None
_build_generate_preflight: Callable[..., Any] | None = None
_normalize_state_contract: Callable[[dict[str, Any]], Any] | None = None
_set_job: Callable[[str, dict[str, Any]], None] | None = None
_record_job_event: Callable[..., None] | None = None
_run_hitl_pipeline: Callable[..., Any] | None = None
_run_pipeline_to_completion: Callable[..., Any] | None = None
_max_iterations: int = 1


def configure_generate_submit_router(
    *,
    require_api_key_if_configured: Callable[..., None],
    resolve_tenant_id: Callable[..., Optional[str]],
    donor_get_strategy: Callable[[str], Any],
    build_generate_preflight: Callable[..., Any],
    normalize_state_contract: Callable[[dict[str, Any]], Any],
    set_job: Callable[[str, dict[str, Any]], None],
    record_job_event: Callable[..., None],
    run_hitl_pipeline: Callable[..., Any],
    run_pipeline_to_completion: Callable[..., Any],
    max_iterations: int,
) -> None:
    global _require_api_key_if_configured
    global _resolve_tenant_id
    global _donor_get_strategy
    global _build_generate_preflight
    global _normalize_state_contract
    global _set_job
    global _record_job_event
    global _run_hitl_pipeline
    global _run_pipeline_to_completion
    global _max_iterations

    _require_api_key_if_configured = require_api_key_if_configured
    _resolve_tenant_id = resolve_tenant_id
    _donor_get_strategy = donor_get_strategy
    _build_generate_preflight = build_generate_preflight
    _normalize_state_contract = normalize_state_contract
    _set_job = set_job
    _record_job_event = record_job_event
    _run_hitl_pipeline = run_hitl_pipeline
    _run_pipeline_to_completion = run_pipeline_to_completion
    _max_iterations = max_iterations


@router.post("/generate/preflight")
def generate_preflight(req: GeneratePreflightRequest, request: Request):
    _require_api_key_if_configured(request)
    return handle_generate_preflight(
        req=req,
        resolve_tenant_id=_resolve_tenant_id,
        request=request,
        donor_get_strategy=_donor_get_strategy,
        build_generate_preflight=_build_generate_preflight,
    )


@router.post("/generate")
async def generate(req: GenerateRequest, background_tasks: BackgroundTasks, request: Request):
    _require_api_key_if_configured(request)
    return handle_generate(
        req=req,
        request=request,
        background_tasks=background_tasks,
        resolve_tenant_id=_resolve_tenant_id,
        donor_get_strategy=_donor_get_strategy,
        build_generate_preflight=_build_generate_preflight,
        normalize_state_contract=_normalize_state_contract,
        set_job=_set_job,
        record_job_event=_record_job_event,
        run_hitl_pipeline=_run_hitl_pipeline,
        run_pipeline_to_completion=_run_pipeline_to_completion,
        max_iterations=_max_iterations,
    )
