from __future__ import annotations

import uuid
from typing import Any, Dict, Optional

from fastapi import BackgroundTasks, HTTPException, Query, Request

from grantflow.api.app import (
    _build_generate_preflight,
    _checkpoint_status_token,
    _clear_hitl_runtime_state,
    _dispatch_generate_from_preset,
    _dispatch_pipeline_task,
    _get_job,
    _global_idempotency_replay_response,
    _idempotency_fingerprint,
    _idempotency_replay_response,
    _ingest_inventory,
    _job_runner_mode,
    _normalize_critic_fatal_flaws_for_job,
    _record_hitl_feedback_in_state,
    _record_job_event,
    _resolve_preflight_request_context,
    _resolve_request_id,
    _resume_target_from_checkpoint,
    _run_hitl_pipeline,
    _run_hitl_pipeline_by_job_id,
    _run_pipeline_to_completion,
    _run_pipeline_to_completion_by_job_id,
    _set_job,
    _store_global_idempotency_response,
    _store_idempotency_response,
    _update_job,
    _uses_redis_queue_runner,
)
from grantflow.api.public_views import (
    public_job_citations_payload,
    public_job_diff_payload,
    public_job_events_payload,
    public_job_grounding_gate_payload,
    public_job_metrics_payload,
    public_job_payload,
    public_job_quality_payload,
    public_job_versions_payload,
)
from grantflow.api.schemas import (
    GenerateAcceptedPublicResponse,
    GenerateFromPresetAcceptedPublicResponse,
    GenerateFromPresetBatchRequest,
    GenerateFromPresetBatchPublicResponse,
    GenerateFromPresetRequest,
    GeneratePreflightRequest,
    GeneratePreflightPublicResponse,
    GenerateRequest,
    JobCitationsPublicResponse,
    JobDiffPublicResponse,
    JobEventsPublicResponse,
    JobGroundingGatePublicResponse,
    JobMetricsPublicResponse,
    JobQualitySummaryPublicResponse,
    JobStatusPublicResponse,
    JobVersionsPublicResponse,
)
from grantflow.api.security import require_api_key_if_configured
from grantflow.api.tenant import (
    _ensure_job_tenant_read_access,
    _ensure_job_tenant_write_access,
    _job_donor_id,
    _job_tenant_id,
    _resolve_tenant_id,
)
from grantflow.api.routers import jobs_router
from grantflow.core.config import config
from grantflow.core.strategies.factory import DonorFactory
from grantflow.swarm.hitl import HITLStatus, hitl_manager
from grantflow.swarm.state_contract import build_graph_state, normalize_state_contract


@jobs_router.post(
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


@jobs_router.post(
    "/generate/from-preset",
    response_model=GenerateFromPresetAcceptedPublicResponse,
    response_model_exclude_none=True,
)
async def generate_from_preset(
    req: GenerateFromPresetRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    request_id: Optional[str] = Query(default=None),
):
    require_api_key_if_configured(request)
    return await _dispatch_generate_from_preset(
        req,
        background_tasks,
        request,
        request_id=request_id,
    )


@jobs_router.post(
    "/generate/from-preset/batch",
    response_model=GenerateFromPresetBatchPublicResponse,
    response_model_exclude_none=True,
)
async def generate_from_preset_batch(
    req: GenerateFromPresetBatchRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    request_id: Optional[str] = Query(default=None),
):
    require_api_key_if_configured(request)
    items = list(req.items or [])
    if not items:
        raise HTTPException(status_code=400, detail="items must be non-empty")
    if len(items) > 25:
        raise HTTPException(status_code=400, detail="items limit exceeded (max 25)")

    results: list[dict[str, Any]] = []
    accepted_count = 0
    error_count = 0
    request_id_prefix = str(request_id or "").strip()

    for idx, item in enumerate(items):
        preset_key = str(item.preset_key or "").strip()
        if request_id_prefix:
            item_request_id = f"{request_id_prefix}:{idx}"[:120]
        else:
            item_request_id = None
        try:
            result = await _dispatch_generate_from_preset(
                item,
                background_tasks,
                request,
                request_id=item_request_id,
            )
            row = dict(result) if isinstance(result, dict) else {"result": result}
            row["index"] = idx
            results.append(row)
            accepted_count += 1
        except HTTPException as exc:
            error_count += 1
            error_row = {
                "index": idx,
                "preset_key": preset_key,
                "status": "error",
                "http_status": int(exc.status_code),
                "error": exc.detail,
            }
            results.append(error_row)
            if not req.continue_on_error:
                raise HTTPException(
                    status_code=exc.status_code,
                    detail={
                        "reason": "generate_from_preset_batch_item_failed",
                        "index": idx,
                        "preset_key": preset_key,
                        "item_error": exc.detail,
                        "results": results,
                    },
                ) from exc

    return {
        "status": "accepted" if error_count == 0 else "partial_error",
        "total": len(items),
        "accepted_count": accepted_count,
        "error_count": error_count,
        "results": results,
    }


@jobs_router.post(
    "/generate",
    response_model=GenerateAcceptedPublicResponse,
    response_model_exclude_none=True,
)
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
            if _uses_redis_queue_runner():
                queue_backend = _dispatch_pipeline_task(background_tasks, _run_hitl_pipeline_by_job_id, job_id, "start")
            else:
                queue_backend = _dispatch_pipeline_task(
                    background_tasks, _run_hitl_pipeline, job_id, initial_state, "start"
                )
        else:
            if _uses_redis_queue_runner():
                queue_backend = _dispatch_pipeline_task(background_tasks, _run_pipeline_to_completion_by_job_id, job_id)
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


@jobs_router.post("/cancel/{job_id}")
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


@jobs_router.post("/resume/{job_id}")
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
    checkpoint_status = _checkpoint_status_token(checkpoint)
    if checkpoint_status == HITLStatus.PENDING.value:
        raise HTTPException(status_code=409, detail="Checkpoint is still pending approval")
    if checkpoint_status not in {HITLStatus.APPROVED.value, HITLStatus.REJECTED.value}:
        raise HTTPException(status_code=409, detail="Checkpoint must be approved or rejected before resume")

    checkpoint_stage = str(checkpoint.get("stage") or "").strip().lower()
    job_checkpoint_stage = str(job.get("checkpoint_stage") or "").strip().lower()
    if checkpoint_stage and job_checkpoint_stage and checkpoint_stage != job_checkpoint_stage:
        raise HTTPException(status_code=409, detail="Checkpoint stage does not match job pending stage")

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
        checkpoint_status=checkpoint_status,
    )
    _record_job_event(
        job_id,
        "resume_requested",
        checkpoint_id=str(checkpoint_id),
        checkpoint_status=checkpoint_status,
        resuming_from=start_at,
        request_id=request_id_token,
    )
    try:
        if _uses_redis_queue_runner():
            queue_backend = _dispatch_pipeline_task(background_tasks, _run_hitl_pipeline_by_job_id, job_id, start_at)
        else:
            queue_backend = _dispatch_pipeline_task(background_tasks, _run_hitl_pipeline, job_id, state, start_at)
    except HTTPException as exc:
        _update_job(
            job_id,
            status="pending_hitl",
            state=state,
            resume_from=job.get("resume_from"),
            checkpoint_id=checkpoint_id,
            checkpoint_stage=checkpoint_stage,
            checkpoint_status=checkpoint_status,
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
        "checkpoint_status": checkpoint_status,
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


@jobs_router.get("/status/{job_id}", response_model=JobStatusPublicResponse, response_model_exclude_none=True)
def get_status(job_id: str, request: Request):
    require_api_key_if_configured(request, for_read=True)
    job = _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    _ensure_job_tenant_read_access(request, job)
    return public_job_payload(job)


@jobs_router.get(
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


@jobs_router.get(
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


@jobs_router.get(
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


@jobs_router.get(
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


@jobs_router.get(
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


@jobs_router.get(
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


@jobs_router.get(
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
