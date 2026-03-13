from __future__ import annotations

from typing import Any, Callable, Literal, Optional

from fastapi import APIRouter, HTTPException, Query, Request

from grantflow.api.schemas import (
    JobReviewWorkflowPublicResponse,
    JobReviewWorkflowSLAPublicResponse,
    JobReviewWorkflowSLAProfilePublicResponse,
)

router = APIRouter()

_require_api_key_if_configured: Callable[..., None] | None = None
_normalize_critic_fatal_flaws_for_job: Callable[[str], Optional[dict[str, Any]]] | None = None
_get_job: Callable[[str], Optional[dict[str, Any]]] | None = None
_normalize_review_comments_for_job: Callable[[str], Optional[dict[str, Any]]] | None = None
_public_job_review_workflow_payload: Callable[..., dict[str, Any]] | None = None
_public_job_review_workflow_sla_payload: Callable[..., dict[str, Any]] | None = None
_review_workflow_sla_profile_payload: Callable[..., dict[str, Any]] | None = None
_portfolio_export_response: Callable[..., Any] | None = None
_public_job_review_workflow_csv_text: Callable[..., str] | None = None
_review_workflow_overdue_default_hours: int = 72
_review_workflow_state_filter_values: set[str] = set()


def configure_review_workflow_read_router(
    *,
    require_api_key_if_configured: Callable[..., None],
    normalize_critic_fatal_flaws_for_job: Callable[[str], Optional[dict[str, Any]]],
    get_job: Callable[[str], Optional[dict[str, Any]]],
    normalize_review_comments_for_job: Callable[[str], Optional[dict[str, Any]]],
    public_job_review_workflow_payload: Callable[..., dict[str, Any]],
    public_job_review_workflow_sla_payload: Callable[..., dict[str, Any]],
    review_workflow_sla_profile_payload: Callable[..., dict[str, Any]],
    portfolio_export_response: Callable[..., Any],
    public_job_review_workflow_csv_text: Callable[..., str],
    review_workflow_overdue_default_hours: int,
    review_workflow_state_filter_values: set[str],
) -> None:
    global _require_api_key_if_configured
    global _normalize_critic_fatal_flaws_for_job
    global _get_job
    global _normalize_review_comments_for_job
    global _public_job_review_workflow_payload
    global _public_job_review_workflow_sla_payload
    global _review_workflow_sla_profile_payload
    global _portfolio_export_response
    global _public_job_review_workflow_csv_text
    global _review_workflow_overdue_default_hours
    global _review_workflow_state_filter_values

    _require_api_key_if_configured = require_api_key_if_configured
    _normalize_critic_fatal_flaws_for_job = normalize_critic_fatal_flaws_for_job
    _get_job = get_job
    _normalize_review_comments_for_job = normalize_review_comments_for_job
    _public_job_review_workflow_payload = public_job_review_workflow_payload
    _public_job_review_workflow_sla_payload = public_job_review_workflow_sla_payload
    _review_workflow_sla_profile_payload = review_workflow_sla_profile_payload
    _portfolio_export_response = portfolio_export_response
    _public_job_review_workflow_csv_text = public_job_review_workflow_csv_text
    _review_workflow_overdue_default_hours = int(review_workflow_overdue_default_hours)
    _review_workflow_state_filter_values = set(review_workflow_state_filter_values)


def _normalized_job_or_404(job_id: str) -> dict[str, Any]:
    job = _normalize_critic_fatal_flaws_for_job(job_id) or _get_job(job_id)
    job = _normalize_review_comments_for_job(job_id) or job
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get(
    "/status/{job_id}/review/workflow",
    response_model=JobReviewWorkflowPublicResponse,
    response_model_exclude_none=True,
)
def get_status_review_workflow(
    job_id: str,
    request: Request,
    event_type: Optional[str] = None,
    finding_id: Optional[str] = None,
    comment_status: Optional[str] = Query(default=None, alias="comment_status"),
    workflow_state: Optional[str] = Query(default=None, alias="workflow_state"),
    overdue_after_hours: int = Query(default=_review_workflow_overdue_default_hours, ge=1, le=24 * 30, alias="overdue_after_hours"),
):
    _require_api_key_if_configured(request, for_read=True)
    workflow_state_filter = str(workflow_state or "").strip().lower() or None
    if workflow_state_filter and workflow_state_filter not in _review_workflow_state_filter_values:
        raise HTTPException(status_code=400, detail="Unsupported workflow_state filter")

    job = _normalized_job_or_404(job_id)
    return _public_job_review_workflow_payload(
        job_id,
        job,
        event_type=(event_type or None),
        finding_id=(finding_id or None),
        comment_status=(comment_status or None),
        workflow_state=workflow_state_filter,
        overdue_after_hours=overdue_after_hours,
    )


@router.get(
    "/status/{job_id}/review/workflow/sla",
    response_model=JobReviewWorkflowSLAPublicResponse,
    response_model_exclude_none=True,
)
def get_status_review_workflow_sla(
    job_id: str,
    request: Request,
    overdue_after_hours: int = Query(default=_review_workflow_overdue_default_hours, ge=1, le=24 * 30, alias="overdue_after_hours"),
):
    _require_api_key_if_configured(request, for_read=True)
    job = _normalized_job_or_404(job_id)
    return _public_job_review_workflow_sla_payload(job_id, job, overdue_after_hours=overdue_after_hours)


@router.get(
    "/status/{job_id}/review/workflow/sla/profile",
    response_model=JobReviewWorkflowSLAProfilePublicResponse,
    response_model_exclude_none=True,
)
def get_status_review_workflow_sla_profile(job_id: str, request: Request):
    _require_api_key_if_configured(request, for_read=True)
    job = _normalized_job_or_404(job_id)
    return _review_workflow_sla_profile_payload(job_id, job)


@router.get("/status/{job_id}/review/workflow/export")
def export_status_review_workflow(
    job_id: str,
    request: Request,
    event_type: Optional[str] = None,
    finding_id: Optional[str] = None,
    comment_status: Optional[str] = Query(default=None, alias="comment_status"),
    workflow_state: Optional[str] = Query(default=None, alias="workflow_state"),
    overdue_after_hours: int = Query(default=_review_workflow_overdue_default_hours, ge=1, le=24 * 30, alias="overdue_after_hours"),
    format: Literal["csv", "json"] = Query(default="csv"),
    gzip_enabled: bool = Query(default=False, alias="gzip"),
):
    _require_api_key_if_configured(request, for_read=True)
    workflow_state_filter = str(workflow_state or "").strip().lower() or None
    if workflow_state_filter and workflow_state_filter not in _review_workflow_state_filter_values:
        raise HTTPException(status_code=400, detail="Unsupported workflow_state filter")

    job = _normalized_job_or_404(job_id)
    payload = _public_job_review_workflow_payload(
        job_id,
        job,
        event_type=(event_type or None),
        finding_id=(finding_id or None),
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
        csv_renderer=_public_job_review_workflow_csv_text,
    )
