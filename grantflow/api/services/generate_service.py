from __future__ import annotations

import uuid
from typing import Any, Callable, Optional

from fastapi import BackgroundTasks, HTTPException


def handle_generate_preflight(
    *,
    req: Any,
    resolve_tenant_id: Callable[..., Optional[str]],
    request: Any,
    donor_get_strategy: Callable[[str], Any],
    build_generate_preflight: Callable[..., Any],
) -> Any:
    donor = req.donor_id.strip()
    if not donor:
        raise HTTPException(status_code=400, detail="Missing donor_id")
    try:
        strategy = donor_get_strategy(donor)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    metadata = dict(req.client_metadata) if isinstance(req.client_metadata, dict) else {}
    tenant_id = resolve_tenant_id(
        request,
        explicit_tenant=req.tenant_id,
        client_metadata=metadata,
        require_if_enabled=True,
    )
    if tenant_id:
        metadata["tenant_id"] = tenant_id
    client_metadata = metadata or None
    return build_generate_preflight(
        donor_id=donor,
        strategy=strategy,
        client_metadata=client_metadata,
    )


def handle_generate(
    *,
    req: Any,
    request: Any,
    background_tasks: BackgroundTasks,
    resolve_tenant_id: Callable[..., Optional[str]],
    donor_get_strategy: Callable[[str], Any],
    build_generate_preflight: Callable[..., Any],
    normalize_state_contract: Callable[[dict[str, Any]], Any],
    set_job: Callable[[str, dict[str, Any]], None],
    record_job_event: Callable[..., None],
    run_hitl_pipeline: Callable[..., Any],
    run_pipeline_to_completion: Callable[..., Any],
    max_iterations: int,
) -> dict[str, Any]:
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
        strategy = donor_get_strategy(donor)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    input_payload = req.input_context or {}
    metadata = dict(req.client_metadata) if isinstance(req.client_metadata, dict) else {}
    tenant_id = resolve_tenant_id(
        request,
        explicit_tenant=req.tenant_id,
        client_metadata=metadata,
        require_if_enabled=True,
    )
    if tenant_id:
        metadata["tenant_id"] = tenant_id
    client_metadata = metadata or None

    preflight = build_generate_preflight(
        donor_id=donor,
        strategy=strategy,
        client_metadata=client_metadata,
    )
    preflight_payload: dict[str, Any] = preflight if isinstance(preflight, dict) else {}
    raw_grounding_policy = preflight_payload.get("grounding_policy")
    grounding_policy: dict[str, Any] = raw_grounding_policy if isinstance(raw_grounding_policy, dict) else {}

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

    if req.strict_preflight and preflight_risk_high:
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
        "max_iterations": max_iterations,
        "critic_score": 0.0,
        "needs_revision": False,
        "critic_notes": {},
        "critic_feedback_history": [],
        "hitl_pending": False,
        "errors": [],
    }
    normalize_state_contract(initial_state)

    set_job(
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

    record_job_event(
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
        background_tasks.add_task(run_hitl_pipeline, job_id, initial_state, "start")
    else:
        background_tasks.add_task(run_pipeline_to_completion, job_id, initial_state)

    return {"status": "accepted", "job_id": job_id, "preflight": preflight_payload}
