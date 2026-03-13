from __future__ import annotations

from typing import Any, Callable, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request

router = APIRouter()

_require_api_key_if_configured: Callable[..., None] | None = None
_get_job: Callable[[str], Optional[dict[str, Any]]] | None = None
_update_job: Callable[..., None] | None = None
_record_job_event: Callable[..., None] | None = None
_resume_target_from_checkpoint: Callable[..., str] | None = None
_record_hitl_feedback_in_state: Callable[..., None] | None = None
_run_hitl_pipeline: Callable[..., Any] | None = None
_hitl_manager: Any = None
_hitl_status_pending: Any = None


def configure_generate_write_router(
    *,
    require_api_key_if_configured: Callable[..., None],
    get_job: Callable[[str], Optional[dict[str, Any]]],
    update_job: Callable[..., None],
    record_job_event: Callable[..., None],
    resume_target_from_checkpoint: Callable[..., str],
    record_hitl_feedback_in_state: Callable[..., None],
    run_hitl_pipeline: Callable[..., Any],
    hitl_manager: Any,
    hitl_status_pending: Any,
) -> None:
    global _require_api_key_if_configured
    global _get_job
    global _update_job
    global _record_job_event
    global _resume_target_from_checkpoint
    global _record_hitl_feedback_in_state
    global _run_hitl_pipeline
    global _hitl_manager
    global _hitl_status_pending

    _require_api_key_if_configured = require_api_key_if_configured
    _get_job = get_job
    _update_job = update_job
    _record_job_event = record_job_event
    _resume_target_from_checkpoint = resume_target_from_checkpoint
    _record_hitl_feedback_in_state = record_hitl_feedback_in_state
    _run_hitl_pipeline = run_hitl_pipeline
    _hitl_manager = hitl_manager
    _hitl_status_pending = hitl_status_pending


@router.post("/cancel/{job_id}")
def cancel_job(job_id: str, request: Request):
    _require_api_key_if_configured(request)
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
        checkpoint = _hitl_manager.get_checkpoint(str(checkpoint_id))
        if checkpoint and checkpoint.get("status") == _hitl_status_pending:
            _hitl_manager.cancel(str(checkpoint_id), "Canceled by user")

    _update_job(
        job_id,
        status="canceled",
        cancellation_reason="Canceled by user",
        canceled=True,
    )
    _record_job_event(job_id, "job_canceled", previous_status=status, reason="Canceled by user")
    return {"status": "canceled", "job_id": job_id, "previous_status": status}


@router.post("/resume/{job_id}")
async def resume_job(job_id: str, background_tasks: BackgroundTasks, request: Request):
    _require_api_key_if_configured(request)
    job = _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.get("status") != "pending_hitl":
        raise HTTPException(status_code=409, detail="Job is not waiting for HITL review")

    checkpoint_id = job.get("checkpoint_id")
    if not checkpoint_id:
        raise HTTPException(status_code=409, detail="Checkpoint missing for pending HITL job")

    checkpoint = _hitl_manager.get_checkpoint(checkpoint_id)
    if not checkpoint:
        raise HTTPException(status_code=404, detail="Checkpoint not found")
    if checkpoint.get("status") == _hitl_status_pending:
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
