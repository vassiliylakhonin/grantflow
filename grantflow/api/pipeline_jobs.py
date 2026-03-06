from __future__ import annotations

from typing import Any, Callable, Dict, Literal

from fastapi import BackgroundTasks, HTTPException

from grantflow.api.constants import RUNTIME_PIPELINE_STATE_KEYS, TERMINAL_JOB_STATUSES
from grantflow.api.idempotency_store_facade import _get_job, _record_job_event, _set_job
from grantflow.api.orchestrator_service import _evaluate_runtime_grounded_quality_gate_from_state
from grantflow.api.review_service import _job_is_canceled, _pause_for_hitl
from grantflow.api.review_runtime_helpers import _checkpoint_status_token, _clear_hitl_runtime_state
from grantflow.api.runtime_gate_helpers import (
    _append_runtime_grounded_quality_gate_finding,
    _attach_export_contract_gate,
    _grounding_gate_block_reason,
    _mel_grounding_policy_block_reason,
    _runtime_grounded_quality_gate_block_reason,
)
from grantflow.api.runtime_service import _job_runner_mode, _uses_queue_runner
from grantflow.swarm.hitl import HITLStatus
from grantflow.swarm.state_contract import normalize_state_contract

HITLStartAt = Literal["start", "architect", "mel", "critic"]


def _job_runner():
    from grantflow.api import app as api_app_module

    return api_app_module.JOB_RUNNER


def _graph():
    from grantflow.api import app as api_app_module

    return api_app_module.grantflow_graph


def _dispatch_pipeline_task(background_tasks: BackgroundTasks, fn: Callable[..., None], *args: Any) -> str:
    if _uses_queue_runner():
        accepted = _job_runner().submit(fn, *args)
        if not accepted:
            raise HTTPException(status_code=503, detail="Job queue is full. Retry shortly.")
        return _job_runner_mode()
    background_tasks.add_task(fn, *args)
    return "background_tasks"


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
        final_state = _graph().invoke(initial_state)
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


def _run_pipeline_to_completion_by_job_id(job_id: str) -> None:
    job = _get_job(job_id)
    if not isinstance(job, dict):
        return
    status = str(job.get("status") or "").strip().lower()
    if status in TERMINAL_JOB_STATUSES:
        return
    if status == "pending_hitl":
        return
    if status not in {"accepted", "running"}:
        return
    state = job.get("state")
    if not isinstance(state, dict):
        _set_job(job_id, {"status": "error", "error": "Job state is missing or invalid", "hitl_enabled": False})
        return
    _run_pipeline_to_completion(job_id, state)


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
        final_state = _graph().invoke(state)
        if _job_is_canceled(job_id):
            return
        normalize_state_contract(final_state)
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


def _run_hitl_pipeline_by_job_id(job_id: str, start_at: HITLStartAt) -> None:
    job = _get_job(job_id)
    if not isinstance(job, dict):
        return
    status = str(job.get("status") or "").strip().lower()
    if status in TERMINAL_JOB_STATUSES:
        return
    if status == "pending_hitl":
        return
    if status not in {"accepted", "running"}:
        return
    state = job.get("state")
    if not isinstance(state, dict):
        _set_job(job_id, {"status": "error", "error": "Job state is missing or invalid", "hitl_enabled": True})
        return
    _run_hitl_pipeline(job_id, state, start_at)


def _resume_target_from_checkpoint(checkpoint: Dict[str, Any], default_resume_from: str | None) -> HITLStartAt:
    stage = str(checkpoint.get("stage") or "").strip().lower()
    status = _checkpoint_status_token(checkpoint)

    if status == HITLStatus.APPROVED.value:
        if stage == "toc":
            return "mel"
        if stage == "logframe":
            return "critic"

    if status == HITLStatus.REJECTED.value:
        if stage == "toc":
            return "architect"
        if stage == "logframe":
            return "mel"

    if status in {HITLStatus.APPROVED.value, HITLStatus.REJECTED.value} and default_resume_from in {
        "start",
        "architect",
        "mel",
        "critic",
    }:
        return default_resume_from  # type: ignore[return-value]

    raise ValueError("Checkpoint must be approved or rejected before resume")
