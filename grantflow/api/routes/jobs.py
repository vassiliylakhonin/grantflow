from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import BackgroundTasks, HTTPException, Query, Request

from grantflow.api.bid_no_bid import evaluate_bid_no_bid
from grantflow.api.idempotency_store_facade import (
    _get_job,
    _ingest_inventory,
    _record_job_event,
    _set_job,
    _update_job,
)
from grantflow.api.pipeline_jobs import (
    _checkpoint_status_token,
    _clear_hitl_runtime_state,
    _dispatch_pipeline_task,
    _record_hitl_feedback_in_state,
    _resume_target_from_checkpoint,
)
from grantflow.api.review_service import _normalize_critic_fatal_flaws_for_job
from grantflow.api.runtime_service import (
    _job_runner_mode,
    _uses_redis_queue_runner,
)
from grantflow.api.idempotency import (
    _global_idempotency_replay_response,
    _idempotency_fingerprint,
    _idempotency_replay_response,
    _resolve_request_id,
    _store_global_idempotency_response,
    _store_idempotency_response,
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
from grantflow.api.presets_service import _dispatch_generate_from_preset, _resolve_preflight_request_context
from grantflow.api.schemas import (
    BidNoBidRequest,
    BidNoBidResponse,
    BidNoBidTrailResponse,
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


def _app_module():
    from grantflow.api import app as api_app_module

    return api_app_module


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _bid_no_bid_freshness_signature(job: Dict[str, Any]) -> Dict[str, Any]:
    raw_state = job.get("state")
    state_dict: Dict[str, Any] = raw_state if isinstance(raw_state, dict) else {}

    raw_critic_notes = state_dict.get("critic_notes")
    critic_notes: Dict[str, Any] = raw_critic_notes if isinstance(raw_critic_notes, dict) else {}

    raw_fatal_flaws = critic_notes.get("fatal_flaws")
    fatal_flaws: list[Any] = raw_fatal_flaws if isinstance(raw_fatal_flaws, list) else []

    open_findings = 0
    for item in fatal_flaws:
        if not isinstance(item, dict):
            continue
        status = str(item.get("status") or "open").strip().lower()
        if status in {"open", "pending", "in_progress", "acknowledged"}:
            open_findings += 1

    raw_comments = job.get("review_comments")
    comments: list[Any] = raw_comments if isinstance(raw_comments, list) else []
    open_comments = 0
    for item in comments:
        if not isinstance(item, dict):
            continue
        status = str(item.get("status") or "open").strip().lower()
        if status in {"open", "pending", "in_progress", "acknowledged"}:
            open_comments += 1

    return {
        "open_critic_findings": open_findings,
        "open_review_comments": open_comments,
        "needs_revision": bool(state_dict.get("needs_revision")),
    }


def _decision_change_fields(previous: Dict[str, Any] | None, current: Dict[str, Any]) -> list[str]:
    if not previous:
        return ["initial_decision"]

    changed: list[str] = []
    for key in ("verdict", "weighted_score", "hard_blockers", "preset_profile"):
        if previous.get(key) != current.get(key):
            changed.append(key)
    return changed or ["metadata_refresh"]


def _append_bid_no_bid_trail(
    *,
    state_dict: Dict[str, Any],
    previous_decision: Dict[str, Any] | None,
    current_decision: Dict[str, Any],
    reason: str,
    actor: str,
) -> Dict[str, Any]:
    trail_raw = state_dict.get("bid_no_bid_decision_trail")
    trail: list[Dict[str, Any]] = (
        [item for item in trail_raw if isinstance(item, dict)] if isinstance(trail_raw, list) else []
    )

    entry = {
        "at": _utc_now_iso(),
        "reason": reason,
        "actor": actor,
        "changed_fields": _decision_change_fields(previous_decision, current_decision),
        "from_verdict": previous_decision.get("verdict") if isinstance(previous_decision, dict) else None,
        "to_verdict": current_decision.get("verdict"),
        "from_score": previous_decision.get("weighted_score") if isinstance(previous_decision, dict) else None,
        "to_score": current_decision.get("weighted_score"),
    }
    trail.append(entry)
    if len(trail) > 50:
        trail = trail[-50:]

    next_state = dict(state_dict)
    next_state["bid_no_bid_decision_trail"] = trail
    return next_state


def _maybe_refresh_bid_no_bid_decision(job_id: str, job: Dict[str, Any]) -> Dict[str, Any]:
    raw_state = job.get("state")
    state_dict: Dict[str, Any] = raw_state if isinstance(raw_state, dict) else {}

    raw_decision = state_dict.get("bid_no_bid_decision")
    decision: Dict[str, Any] | None = raw_decision if isinstance(raw_decision, dict) else None
    if not decision:
        return job

    raw_inputs = decision.get("inputs")
    inputs: Dict[str, Any] = raw_inputs if isinstance(raw_inputs, dict) else {}
    raw_scores = inputs.get("scores")
    scores: Dict[str, Any] | None = raw_scores if isinstance(raw_scores, dict) else None
    if not scores:
        return job

    raw_previous_sig = decision.get("freshness_signature")
    previous_sig: Dict[str, Any] | None = raw_previous_sig if isinstance(raw_previous_sig, dict) else None
    current_sig = _bid_no_bid_freshness_signature(job)
    stale = bool(previous_sig != current_sig)

    if not stale:
        return job

    refreshed = evaluate_bid_no_bid(
        scores={k: int(v) for k, v in scores.items()},
        donor_profile=inputs.get("donor_profile"),
        weight_overrides=inputs.get("weight_overrides") if isinstance(inputs.get("weight_overrides"), dict) else None,
        mandatory_eligibility_gap=bool(inputs.get("mandatory_eligibility_gap")),
        conflict_of_interest=bool(inputs.get("conflict_of_interest")),
    )

    next_decision = {
        **refreshed,
        "inputs": inputs,
        "freshness_signature": current_sig,
        "decision_stale": False,
        "decision_updated_at": _utc_now_iso(),
    }
    next_state = dict(state_dict)
    next_state["bid_no_bid_decision"] = next_decision
    next_state = _append_bid_no_bid_trail(
        state_dict=next_state,
        previous_decision=decision,
        current_decision=next_decision,
        reason="auto_refresh_quality_drift",
        actor="system",
    )
    updated = _update_job(job_id, state=next_state)
    if isinstance(updated, dict):
        return updated
    return _get_job(job_id) or job


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
    return _app_module()._build_generate_preflight(
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
    preflight = _app_module()._build_generate_preflight(
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
                queue_backend = _dispatch_pipeline_task(
                    background_tasks, _app_module()._run_hitl_pipeline_by_job_id, job_id, "start"
                )
            else:
                queue_backend = _dispatch_pipeline_task(
                    background_tasks, _app_module()._run_hitl_pipeline, job_id, initial_state, "start"
                )
        else:
            if _uses_redis_queue_runner():
                queue_backend = _dispatch_pipeline_task(
                    background_tasks, _app_module()._run_pipeline_to_completion_by_job_id, job_id
                )
            else:
                queue_backend = _dispatch_pipeline_task(
                    background_tasks, _app_module()._run_pipeline_to_completion, job_id, initial_state
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
            queue_backend = _dispatch_pipeline_task(
                background_tasks, _app_module()._run_hitl_pipeline_by_job_id, job_id, start_at
            )
        else:
            queue_backend = _dispatch_pipeline_task(
                background_tasks,
                _app_module()._run_hitl_pipeline,
                job_id,
                state,
                start_at,
            )
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
    job = _maybe_refresh_bid_no_bid_decision(job_id, job)
    job_tenant_id = _job_tenant_id(job)
    donor = _job_donor_id(job)
    inventory_rows = _ingest_inventory(donor_id=donor or None, tenant_id=job_tenant_id)
    return public_job_quality_payload(job_id, job, ingest_inventory_rows=inventory_rows)


@jobs_router.post(
    "/status/{job_id}/decision/bid-no-bid",
    response_model=BidNoBidResponse,
    response_model_exclude_none=True,
)
def post_status_bid_no_bid_decision(job_id: str, payload: BidNoBidRequest, request: Request):
    require_api_key_if_configured(request)
    job = _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    _ensure_job_tenant_write_access(request, job)

    scores = {
        "strategic_fit": payload.strategic_fit,
        "win_probability": payload.win_probability,
        "budget_margin": payload.budget_margin,
        "delivery_capacity": payload.delivery_capacity,
        "compliance_readiness": payload.compliance_readiness,
        "partner_strength": payload.partner_strength,
        "timeline_realism": payload.timeline_realism,
        "evidence_strength": payload.evidence_strength,
    }

    invalid_fields = [key for key, value in scores.items() if int(value) < 0 or int(value) > 100]
    if invalid_fields:
        raise HTTPException(status_code=400, detail=f"Scores must be between 0 and 100: {', '.join(invalid_fields)}")

    decision = evaluate_bid_no_bid(
        scores=scores,
        donor_profile=payload.donor_profile,
        weight_overrides=payload.weight_overrides,
        mandatory_eligibility_gap=payload.mandatory_eligibility_gap,
        conflict_of_interest=payload.conflict_of_interest,
    )

    state_dict = job.get("state") if isinstance(job.get("state"), dict) else {}
    previous_decision = (
        state_dict.get("bid_no_bid_decision") if isinstance(state_dict.get("bid_no_bid_decision"), dict) else None
    )
    next_state = dict(state_dict)
    decision_updated_at = _utc_now_iso()
    next_state["bid_no_bid_decision"] = {
        **decision,
        "inputs": {
            "scores": scores,
            "donor_profile": payload.donor_profile,
            "weight_overrides": payload.weight_overrides,
            "mandatory_eligibility_gap": bool(payload.mandatory_eligibility_gap),
            "conflict_of_interest": bool(payload.conflict_of_interest),
        },
        "freshness_signature": _bid_no_bid_freshness_signature(job),
        "decision_stale": False,
        "decision_updated_at": decision_updated_at,
    }
    next_state = _append_bid_no_bid_trail(
        state_dict=next_state,
        previous_decision=previous_decision,
        current_decision=next_state["bid_no_bid_decision"],
        reason="manual_update",
        actor="user",
    )
    _update_job(job_id, state=next_state)
    return {
        **decision,
        "decision_stale": False,
        "decision_updated_at": decision_updated_at,
    }


@jobs_router.get(
    "/status/{job_id}/decision/bid-no-bid/trail",
    response_model=BidNoBidTrailResponse,
    response_model_exclude_none=True,
)
def get_status_bid_no_bid_trail(job_id: str, request: Request):
    require_api_key_if_configured(request, for_read=True)
    job = _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    _ensure_job_tenant_read_access(request, job)

    state_dict = job.get("state") if isinstance(job.get("state"), dict) else {}
    trail_raw = state_dict.get("bid_no_bid_decision_trail")
    trail = [item for item in trail_raw if isinstance(item, dict)] if isinstance(trail_raw, list) else []
    return {"entries": trail}


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
