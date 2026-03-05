from __future__ import annotations

from grantflow.api.app import (
    CRITIC_FINDING_STATUSES,
    CriticFatalFlawPublicResponse,
    CriticFatalFlawStatusUpdatePublicResponse,
    CriticFindingsBulkStatusPublicResponse,
    CriticFindingsBulkStatusRequest,
    CriticFindingsListPublicResponse,
    HITLApprovalRequest,
    HITLPendingListPublicResponse,
    HITLStatus,
    HTTPException,
    JobCommentCreateRequest,
    JobCommentsPublicResponse,
    JobCriticPublicResponse,
    JobHITLHistoryPublicResponse,
    JobReviewWorkflowPublicResponse,
    JobReviewWorkflowSLAHotspotsPublicResponse,
    JobReviewWorkflowSLAHotspotsTrendsPublicResponse,
    JobReviewWorkflowSLAProfilePublicResponse,
    JobReviewWorkflowSLAPublicResponse,
    JobReviewWorkflowSLARecomputePublicResponse,
    JobReviewWorkflowSLATrendsPublicResponse,
    JobReviewWorkflowTrendsPublicResponse,
    Optional,
    Query,
    REVIEW_COMMENT_SECTIONS,
    REVIEW_WORKFLOW_OVERDUE_DEFAULT_HOURS,
    REVIEW_WORKFLOW_STATE_FILTER_VALUES,
    Request,
    ReviewCommentPublicResponse,
    ReviewWorkflowSLARecomputeRequest,
    _append_review_comment,
    _checkpoint_status_token,
    _checkpoint_tenant_id,
    _critic_findings_list_payload,
    _ensure_checkpoint_tenant_write_access,
    _ensure_job_tenant_read_access,
    _ensure_job_tenant_write_access,
    _find_critic_fatal_flaw,
    _find_job_by_checkpoint_id,
    _finding_actor_from_request,
    _get_job,
    _global_idempotency_replay_response,
    _hitl_history_payload,
    _idempotency_fingerprint,
    _job_draft_version_exists_for_section,
    _normalize_critic_fatal_flaws_for_job,
    _normalize_review_comments_for_job,
    _recompute_review_workflow_sla,
    _record_job_event,
    _resolve_request_id,
    _resolve_tenant_id,
    _review_workflow_sla_profile_payload,
    _set_critic_fatal_flaw_status,
    _set_critic_fatal_flaws_status_bulk,
    _set_review_comment_status,
    _store_global_idempotency_response,
    _validated_filter_token,
    finding_primary_id,
    hitl_manager,
    public_checkpoint_payload,
    public_job_comments_payload,
    public_job_critic_payload,
    public_job_review_workflow_payload,
    public_job_review_workflow_sla_hotspots_payload,
    public_job_review_workflow_sla_hotspots_trends_payload,
    public_job_review_workflow_sla_payload,
    public_job_review_workflow_sla_trends_payload,
    public_job_review_workflow_trends_payload,
    require_api_key_if_configured,
)
from grantflow.api.routers import review_router


@review_router.get(
    "/status/{job_id}/hitl/history",
    response_model=JobHITLHistoryPublicResponse,
    response_model_exclude_none=True,
)
def get_status_hitl_history(
    job_id: str,
    request: Request,
    event_type: Optional[str] = Query(default=None),
    checkpoint_id: Optional[str] = Query(default=None),
):
    require_api_key_if_configured(request, for_read=True)
    job = _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    _ensure_job_tenant_read_access(request, job)
    return _hitl_history_payload(
        job_id,
        job,
        event_type=(event_type or None),
        checkpoint_id=(checkpoint_id or None),
    )


@review_router.get(
    "/status/{job_id}/critic",
    response_model=JobCriticPublicResponse,
    response_model_exclude_none=True,
)
def get_status_critic(job_id: str, request: Request):
    require_api_key_if_configured(request, for_read=True)
    job = _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    _ensure_job_tenant_read_access(request, job)
    job = _normalize_critic_fatal_flaws_for_job(job_id) or job
    return public_job_critic_payload(job_id, job)


@review_router.get(
    "/status/{job_id}/critic/findings",
    response_model=CriticFindingsListPublicResponse,
    response_model_exclude_none=True,
)
def get_status_critic_findings(
    job_id: str,
    request: Request,
    status: Optional[str] = Query(default=None),
    severity: Optional[str] = Query(default=None),
    section: Optional[str] = Query(default=None),
    version_id: Optional[str] = Query(default=None),
    workflow_state: Optional[str] = Query(default=None),
    include_resolved: bool = True,
    overdue_after_hours: int = REVIEW_WORKFLOW_OVERDUE_DEFAULT_HOURS,
):
    require_api_key_if_configured(request, for_read=True)
    job = _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    _ensure_job_tenant_read_access(request, job)
    job = _normalize_critic_fatal_flaws_for_job(job_id) or job

    finding_status = _validated_filter_token(
        status,
        allowed=CRITIC_FINDING_STATUSES,
        detail="Unsupported finding status filter",
    )
    finding_severity = _validated_filter_token(
        severity,
        allowed={"high", "medium", "low"},
        detail="Unsupported finding severity filter",
    )
    finding_section = _validated_filter_token(
        section,
        allowed={"toc", "logframe", "general"},
        detail="Unsupported finding section filter",
    )
    finding_workflow_state = _validated_filter_token(
        workflow_state,
        allowed=set(REVIEW_WORKFLOW_STATE_FILTER_VALUES) | {"resolved"},
        detail="Unsupported workflow_state filter",
    )
    if overdue_after_hours <= 0:
        raise HTTPException(status_code=400, detail="overdue_after_hours must be > 0")

    return _critic_findings_list_payload(
        job_id,
        job,
        finding_status=finding_status,
        severity=finding_severity,
        section=finding_section,
        version_id=(str(version_id or "").strip() or None),
        workflow_state=finding_workflow_state,
        include_resolved=bool(include_resolved),
        overdue_after_hours=int(overdue_after_hours),
    )


@review_router.get(
    "/status/{job_id}/critic/findings/{finding_id}",
    response_model=CriticFatalFlawPublicResponse,
    response_model_exclude_none=True,
)
def get_status_critic_finding(
    job_id: str,
    finding_id: str,
    request: Request,
    overdue_after_hours: int = REVIEW_WORKFLOW_OVERDUE_DEFAULT_HOURS,
):
    require_api_key_if_configured(request, for_read=True)
    job = _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    _ensure_job_tenant_read_access(request, job)
    job = _normalize_critic_fatal_flaws_for_job(job_id) or job

    if overdue_after_hours <= 0:
        raise HTTPException(status_code=400, detail="overdue_after_hours must be > 0")

    payload = _critic_findings_list_payload(
        job_id,
        job,
        overdue_after_hours=int(overdue_after_hours),
    )
    findings = payload.get("findings")
    for item in findings if isinstance(findings, list) else []:
        if not isinstance(item, dict):
            continue
        if finding_primary_id(item) == finding_id:
            return item
    raise HTTPException(status_code=404, detail="Critic finding not found")


@review_router.post(
    "/status/{job_id}/critic/findings/{finding_id}/ack",
    response_model=CriticFatalFlawStatusUpdatePublicResponse,
    response_model_exclude_none=True,
)
def acknowledge_status_critic_finding(
    job_id: str,
    finding_id: str,
    request: Request,
    dry_run: bool = False,
    if_match_status: Optional[str] = Query(default=None),
    request_id: Optional[str] = Query(default=None),
):
    require_api_key_if_configured(request)
    job = _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    _ensure_job_tenant_write_access(request, job)
    return _set_critic_fatal_flaw_status(
        job_id,
        finding_id=finding_id,
        next_status="acknowledged",
        actor=_finding_actor_from_request(request),
        dry_run=bool(dry_run),
        if_match_status=(if_match_status or None),
        request_id=_resolve_request_id(request, request_id),
    )


@review_router.post(
    "/status/{job_id}/critic/findings/{finding_id}/open",
    response_model=CriticFatalFlawStatusUpdatePublicResponse,
    response_model_exclude_none=True,
)
def reopen_status_critic_finding(
    job_id: str,
    finding_id: str,
    request: Request,
    dry_run: bool = False,
    if_match_status: Optional[str] = Query(default=None),
    request_id: Optional[str] = Query(default=None),
):
    require_api_key_if_configured(request)
    job = _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    _ensure_job_tenant_write_access(request, job)
    return _set_critic_fatal_flaw_status(
        job_id,
        finding_id=finding_id,
        next_status="open",
        actor=_finding_actor_from_request(request),
        dry_run=bool(dry_run),
        if_match_status=(if_match_status or None),
        request_id=_resolve_request_id(request, request_id),
    )


@review_router.post(
    "/status/{job_id}/critic/findings/{finding_id}/resolve",
    response_model=CriticFatalFlawStatusUpdatePublicResponse,
    response_model_exclude_none=True,
)
def resolve_status_critic_finding(
    job_id: str,
    finding_id: str,
    request: Request,
    dry_run: bool = False,
    if_match_status: Optional[str] = Query(default=None),
    request_id: Optional[str] = Query(default=None),
):
    require_api_key_if_configured(request)
    job = _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    _ensure_job_tenant_write_access(request, job)
    return _set_critic_fatal_flaw_status(
        job_id,
        finding_id=finding_id,
        next_status="resolved",
        actor=_finding_actor_from_request(request),
        dry_run=bool(dry_run),
        if_match_status=(if_match_status or None),
        request_id=_resolve_request_id(request, request_id),
    )


@review_router.post(
    "/status/{job_id}/critic/findings/bulk-status",
    response_model=CriticFindingsBulkStatusPublicResponse,
    response_model_exclude_none=True,
)
def bulk_status_critic_findings(job_id: str, req: CriticFindingsBulkStatusRequest, request: Request):
    require_api_key_if_configured(request)
    job = _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    _ensure_job_tenant_write_access(request, job)
    next_status = str(req.next_status or "").strip().lower()
    return _set_critic_fatal_flaws_status_bulk(
        job_id,
        next_status=next_status,
        actor=_finding_actor_from_request(request),
        dry_run=bool(req.dry_run),
        request_id=_resolve_request_id(request, req.request_id),
        if_match_status=(req.if_match_status or None),
        apply_to_all=bool(req.apply_to_all),
        finding_status=(req.finding_status or None),
        severity=(req.severity or None),
        section=(req.section or None),
        finding_ids=req.finding_ids,
    )


@review_router.get(
    "/status/{job_id}/comments",
    response_model=JobCommentsPublicResponse,
    response_model_exclude_none=True,
)
def get_status_comments(
    job_id: str,
    request: Request,
    section: Optional[str] = None,
    comment_status: Optional[str] = Query(default=None, alias="status"),
    version_id: Optional[str] = None,
):
    require_api_key_if_configured(request, for_read=True)
    job = _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    _ensure_job_tenant_read_access(request, job)
    job = _normalize_critic_fatal_flaws_for_job(job_id) or job
    job = _normalize_review_comments_for_job(job_id) or job
    return public_job_comments_payload(
        job_id,
        job,
        section=section,
        comment_status=comment_status,
        version_id=version_id,
    )


@review_router.get(
    "/status/{job_id}/review/workflow",
    response_model=JobReviewWorkflowPublicResponse,
    response_model_exclude_none=True,
)
def get_status_review_workflow(
    job_id: str,
    request: Request,
    event_type: Optional[str] = None,
    finding_id: Optional[str] = None,
    finding_code: Optional[str] = Query(default=None, alias="finding_code"),
    finding_section: Optional[str] = Query(default=None, alias="finding_section"),
    comment_status: Optional[str] = Query(default=None, alias="comment_status"),
    workflow_state: Optional[str] = Query(default=None, alias="workflow_state"),
    overdue_after_hours: int = Query(
        default=REVIEW_WORKFLOW_OVERDUE_DEFAULT_HOURS,
        ge=1,
        le=24 * 30,
        alias="overdue_after_hours",
    ),
):
    require_api_key_if_configured(request, for_read=True)
    workflow_state_filter = str(workflow_state or "").strip().lower() or None
    if workflow_state_filter and workflow_state_filter not in REVIEW_WORKFLOW_STATE_FILTER_VALUES:
        raise HTTPException(status_code=400, detail="Unsupported workflow_state filter")
    finding_section_filter = _validated_filter_token(
        finding_section,
        allowed={"toc", "logframe", "general"},
        detail="Unsupported finding_section filter",
    )
    job = _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    _ensure_job_tenant_read_access(request, job)
    job = _normalize_critic_fatal_flaws_for_job(job_id) or job
    job = _normalize_review_comments_for_job(job_id) or job
    return public_job_review_workflow_payload(
        job_id,
        job,
        event_type=(event_type or None),
        finding_id=(finding_id or None),
        finding_code=(str(finding_code or "").strip() or None),
        finding_section=finding_section_filter,
        comment_status=(comment_status or None),
        workflow_state=workflow_state_filter,
        overdue_after_hours=overdue_after_hours,
    )


@review_router.get(
    "/status/{job_id}/review/workflow/trends",
    response_model=JobReviewWorkflowTrendsPublicResponse,
    response_model_exclude_none=True,
)
def get_status_review_workflow_trends(
    job_id: str,
    request: Request,
    event_type: Optional[str] = None,
    finding_id: Optional[str] = None,
    finding_code: Optional[str] = Query(default=None, alias="finding_code"),
    finding_section: Optional[str] = Query(default=None, alias="finding_section"),
    comment_status: Optional[str] = Query(default=None, alias="comment_status"),
    workflow_state: Optional[str] = Query(default=None, alias="workflow_state"),
    overdue_after_hours: int = Query(
        default=REVIEW_WORKFLOW_OVERDUE_DEFAULT_HOURS,
        ge=1,
        le=24 * 30,
        alias="overdue_after_hours",
    ),
):
    require_api_key_if_configured(request, for_read=True)
    workflow_state_filter = str(workflow_state or "").strip().lower() or None
    if workflow_state_filter and workflow_state_filter not in REVIEW_WORKFLOW_STATE_FILTER_VALUES:
        raise HTTPException(status_code=400, detail="Unsupported workflow_state filter")
    finding_section_filter = _validated_filter_token(
        finding_section,
        allowed={"toc", "logframe", "general"},
        detail="Unsupported finding_section filter",
    )
    job = _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    _ensure_job_tenant_read_access(request, job)
    job = _normalize_critic_fatal_flaws_for_job(job_id) or job
    job = _normalize_review_comments_for_job(job_id) or job
    return public_job_review_workflow_trends_payload(
        job_id,
        job,
        event_type=(event_type or None),
        finding_id=(finding_id or None),
        finding_code=(str(finding_code or "").strip() or None),
        finding_section=finding_section_filter,
        comment_status=(comment_status or None),
        workflow_state=workflow_state_filter,
        overdue_after_hours=overdue_after_hours,
    )


@review_router.get(
    "/status/{job_id}/review/workflow/sla",
    response_model=JobReviewWorkflowSLAPublicResponse,
    response_model_exclude_none=True,
)
def get_status_review_workflow_sla(
    job_id: str,
    request: Request,
    finding_id: Optional[str] = None,
    finding_code: Optional[str] = Query(default=None, alias="finding_code"),
    finding_section: Optional[str] = Query(default=None, alias="finding_section"),
    comment_status: Optional[str] = Query(default=None, alias="comment_status"),
    workflow_state: Optional[str] = Query(default=None, alias="workflow_state"),
    overdue_after_hours: int = Query(
        default=REVIEW_WORKFLOW_OVERDUE_DEFAULT_HOURS,
        ge=1,
        le=24 * 30,
        alias="overdue_after_hours",
    ),
):
    require_api_key_if_configured(request, for_read=True)
    workflow_state_filter = str(workflow_state or "").strip().lower() or None
    if workflow_state_filter and workflow_state_filter not in REVIEW_WORKFLOW_STATE_FILTER_VALUES:
        raise HTTPException(status_code=400, detail="Unsupported workflow_state filter")
    finding_section_filter = _validated_filter_token(
        finding_section,
        allowed={"toc", "logframe", "general"},
        detail="Unsupported finding_section filter",
    )
    job = _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    _ensure_job_tenant_read_access(request, job)
    job = _normalize_critic_fatal_flaws_for_job(job_id) or job
    job = _normalize_review_comments_for_job(job_id) or job
    return public_job_review_workflow_sla_payload(
        job_id,
        job,
        finding_id=(finding_id or None),
        finding_code=(str(finding_code or "").strip() or None),
        finding_section=finding_section_filter,
        comment_status=(comment_status or None),
        workflow_state=workflow_state_filter,
        overdue_after_hours=overdue_after_hours,
    )


@review_router.get(
    "/status/{job_id}/review/workflow/sla/trends",
    response_model=JobReviewWorkflowSLATrendsPublicResponse,
    response_model_exclude_none=True,
)
def get_status_review_workflow_sla_trends(
    job_id: str,
    request: Request,
    finding_id: Optional[str] = None,
    finding_code: Optional[str] = Query(default=None, alias="finding_code"),
    finding_section: Optional[str] = Query(default=None, alias="finding_section"),
    comment_status: Optional[str] = Query(default=None, alias="comment_status"),
    workflow_state: Optional[str] = Query(default=None, alias="workflow_state"),
    overdue_after_hours: int = Query(
        default=REVIEW_WORKFLOW_OVERDUE_DEFAULT_HOURS,
        ge=1,
        le=24 * 30,
        alias="overdue_after_hours",
    ),
):
    require_api_key_if_configured(request, for_read=True)
    workflow_state_filter = str(workflow_state or "").strip().lower() or None
    if workflow_state_filter and workflow_state_filter not in REVIEW_WORKFLOW_STATE_FILTER_VALUES:
        raise HTTPException(status_code=400, detail="Unsupported workflow_state filter")
    finding_section_filter = _validated_filter_token(
        finding_section,
        allowed={"toc", "logframe", "general"},
        detail="Unsupported finding_section filter",
    )
    job = _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    _ensure_job_tenant_read_access(request, job)
    job = _normalize_critic_fatal_flaws_for_job(job_id) or job
    job = _normalize_review_comments_for_job(job_id) or job
    return public_job_review_workflow_sla_trends_payload(
        job_id,
        job,
        finding_id=(finding_id or None),
        finding_code=(str(finding_code or "").strip() or None),
        finding_section=finding_section_filter,
        comment_status=(comment_status or None),
        workflow_state=workflow_state_filter,
        overdue_after_hours=overdue_after_hours,
    )


@review_router.get(
    "/status/{job_id}/review/workflow/sla/hotspots",
    response_model=JobReviewWorkflowSLAHotspotsPublicResponse,
    response_model_exclude_none=True,
)
def get_status_review_workflow_sla_hotspots(
    job_id: str,
    request: Request,
    finding_id: Optional[str] = None,
    finding_code: Optional[str] = Query(default=None, alias="finding_code"),
    finding_section: Optional[str] = Query(default=None, alias="finding_section"),
    comment_status: Optional[str] = Query(default=None, alias="comment_status"),
    workflow_state: Optional[str] = Query(default=None, alias="workflow_state"),
    overdue_after_hours: int = Query(
        default=REVIEW_WORKFLOW_OVERDUE_DEFAULT_HOURS,
        ge=1,
        le=24 * 30,
        alias="overdue_after_hours",
    ),
    top_limit: int = Query(default=10, ge=1, le=200, alias="top_limit"),
    hotspot_kind: Optional[str] = Query(default=None, alias="hotspot_kind"),
    hotspot_severity: Optional[str] = Query(default=None, alias="hotspot_severity"),
    min_overdue_hours: Optional[float] = Query(default=None, ge=0.0, le=24 * 365, alias="min_overdue_hours"),
):
    require_api_key_if_configured(request, for_read=True)
    workflow_state_filter = str(workflow_state or "").strip().lower() or None
    if workflow_state_filter and workflow_state_filter not in REVIEW_WORKFLOW_STATE_FILTER_VALUES:
        raise HTTPException(status_code=400, detail="Unsupported workflow_state filter")
    finding_section_filter = _validated_filter_token(
        finding_section,
        allowed={"toc", "logframe", "general"},
        detail="Unsupported finding_section filter",
    )
    hotspot_kind_filter = _validated_filter_token(
        hotspot_kind,
        allowed={"finding", "comment"},
        detail="Unsupported hotspot_kind filter",
    )
    hotspot_severity_filter = _validated_filter_token(
        hotspot_severity,
        allowed={"high", "medium", "low", "unknown"},
        detail="Unsupported hotspot_severity filter",
    )
    job = _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    _ensure_job_tenant_read_access(request, job)
    job = _normalize_critic_fatal_flaws_for_job(job_id) or job
    job = _normalize_review_comments_for_job(job_id) or job
    return public_job_review_workflow_sla_hotspots_payload(
        job_id,
        job,
        finding_id=(finding_id or None),
        finding_code=(str(finding_code or "").strip() or None),
        finding_section=finding_section_filter,
        comment_status=(comment_status or None),
        workflow_state=workflow_state_filter,
        overdue_after_hours=overdue_after_hours,
        top_limit=top_limit,
        hotspot_kind=hotspot_kind_filter,
        hotspot_severity=hotspot_severity_filter,
        min_overdue_hours=min_overdue_hours,
    )


@review_router.get(
    "/status/{job_id}/review/workflow/sla/hotspots/trends",
    response_model=JobReviewWorkflowSLAHotspotsTrendsPublicResponse,
    response_model_exclude_none=True,
)
def get_status_review_workflow_sla_hotspots_trends(
    job_id: str,
    request: Request,
    finding_id: Optional[str] = None,
    finding_code: Optional[str] = Query(default=None, alias="finding_code"),
    finding_section: Optional[str] = Query(default=None, alias="finding_section"),
    comment_status: Optional[str] = Query(default=None, alias="comment_status"),
    workflow_state: Optional[str] = Query(default=None, alias="workflow_state"),
    overdue_after_hours: int = Query(
        default=REVIEW_WORKFLOW_OVERDUE_DEFAULT_HOURS,
        ge=1,
        le=24 * 30,
        alias="overdue_after_hours",
    ),
    top_limit: int = Query(default=10, ge=1, le=200, alias="top_limit"),
    hotspot_kind: Optional[str] = Query(default=None, alias="hotspot_kind"),
    hotspot_severity: Optional[str] = Query(default=None, alias="hotspot_severity"),
    min_overdue_hours: Optional[float] = Query(default=None, ge=0.0, le=24 * 365, alias="min_overdue_hours"),
):
    require_api_key_if_configured(request, for_read=True)
    workflow_state_filter = str(workflow_state or "").strip().lower() or None
    if workflow_state_filter and workflow_state_filter not in REVIEW_WORKFLOW_STATE_FILTER_VALUES:
        raise HTTPException(status_code=400, detail="Unsupported workflow_state filter")
    finding_section_filter = _validated_filter_token(
        finding_section,
        allowed={"toc", "logframe", "general"},
        detail="Unsupported finding_section filter",
    )
    hotspot_kind_filter = _validated_filter_token(
        hotspot_kind,
        allowed={"finding", "comment"},
        detail="Unsupported hotspot_kind filter",
    )
    hotspot_severity_filter = _validated_filter_token(
        hotspot_severity,
        allowed={"high", "medium", "low", "unknown"},
        detail="Unsupported hotspot_severity filter",
    )
    job = _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    _ensure_job_tenant_read_access(request, job)
    job = _normalize_critic_fatal_flaws_for_job(job_id) or job
    job = _normalize_review_comments_for_job(job_id) or job
    return public_job_review_workflow_sla_hotspots_trends_payload(
        job_id,
        job,
        finding_id=(finding_id or None),
        finding_code=(str(finding_code or "").strip() or None),
        finding_section=finding_section_filter,
        comment_status=(comment_status or None),
        workflow_state=workflow_state_filter,
        overdue_after_hours=overdue_after_hours,
        top_limit=top_limit,
        hotspot_kind=hotspot_kind_filter,
        hotspot_severity=hotspot_severity_filter,
        min_overdue_hours=min_overdue_hours,
    )


@review_router.get(
    "/status/{job_id}/review/workflow/sla/profile",
    response_model=JobReviewWorkflowSLAProfilePublicResponse,
    response_model_exclude_none=True,
)
def get_status_review_workflow_sla_profile(job_id: str, request: Request):
    require_api_key_if_configured(request, for_read=True)
    job = _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    _ensure_job_tenant_read_access(request, job)
    job = _normalize_critic_fatal_flaws_for_job(job_id) or job
    job = _normalize_review_comments_for_job(job_id) or job
    return _review_workflow_sla_profile_payload(job_id, job)


@review_router.post(
    "/status/{job_id}/review/workflow/sla/recompute",
    response_model=JobReviewWorkflowSLARecomputePublicResponse,
    response_model_exclude_none=True,
)
def recompute_status_review_workflow_sla(
    job_id: str,
    request: Request,
    req: Optional[ReviewWorkflowSLARecomputeRequest] = None,
):
    require_api_key_if_configured(request)
    job = _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    _ensure_job_tenant_write_access(request, job)
    payload = req or ReviewWorkflowSLARecomputeRequest()
    return _recompute_review_workflow_sla(
        job_id,
        actor=_finding_actor_from_request(request),
        finding_sla_hours_override=payload.finding_sla_hours,
        default_comment_sla_hours=payload.default_comment_sla_hours,
        use_saved_profile=bool(payload.use_saved_profile),
    )


@review_router.post(
    "/status/{job_id}/comments",
    response_model=ReviewCommentPublicResponse,
    response_model_exclude_none=True,
)
def add_status_comment(job_id: str, req: JobCommentCreateRequest, request: Request):
    require_api_key_if_configured(request)
    job = _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    _ensure_job_tenant_write_access(request, job)

    section = (req.section or "").strip().lower()
    if section not in REVIEW_COMMENT_SECTIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported section: {section or req.section}")

    message = (req.message or "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="Missing comment message")
    if len(message) > 4000:
        raise HTTPException(status_code=400, detail="Comment message is too long")

    author = (req.author or "").strip() or None
    version_id = (req.version_id or "").strip() or None
    linked_finding_id = (req.linked_finding_id or "").strip() or None
    if version_id and not _job_draft_version_exists_for_section(job, section=section, version_id=version_id):
        raise HTTPException(status_code=400, detail="Unknown version_id for requested section")
    linked_finding_severity: Optional[str] = None
    if linked_finding_id:
        normalized_job = _normalize_critic_fatal_flaws_for_job(job_id) or _get_job(job_id)
        if not normalized_job:
            raise HTTPException(status_code=404, detail="Job not found")
        finding = _find_critic_fatal_flaw(normalized_job, linked_finding_id)
        if not finding:
            raise HTTPException(status_code=400, detail="Unknown linked_finding_id")
        linked_finding_id = finding_primary_id(finding) or linked_finding_id
        linked_finding_severity = str(finding.get("severity") or "").strip().lower() or None
        finding_section = str(finding.get("section") or "")
        if section != "general" and finding_section and section != finding_section:
            raise HTTPException(status_code=400, detail="linked_finding_id section does not match comment section")

    return _append_review_comment(
        job_id,
        section=section,
        message=message,
        author=author,
        version_id=version_id,
        linked_finding_id=linked_finding_id,
        linked_finding_severity=linked_finding_severity,
        request_id=_resolve_request_id(request, req.request_id),
    )


@review_router.post(
    "/status/{job_id}/comments/{comment_id}/resolve",
    response_model=ReviewCommentPublicResponse,
    response_model_exclude_none=True,
)
def resolve_status_comment(
    job_id: str,
    comment_id: str,
    request: Request,
    request_id: Optional[str] = Query(default=None),
):
    require_api_key_if_configured(request)
    job = _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    _ensure_job_tenant_write_access(request, job)
    return _set_review_comment_status(
        job_id,
        comment_id=comment_id,
        next_status="resolved",
        actor=_finding_actor_from_request(request),
        request_id=_resolve_request_id(request, request_id),
    )


@review_router.post(
    "/status/{job_id}/comments/{comment_id}/reopen",
    response_model=ReviewCommentPublicResponse,
    response_model_exclude_none=True,
)
def reopen_status_comment(
    job_id: str,
    comment_id: str,
    request: Request,
    request_id: Optional[str] = Query(default=None),
):
    require_api_key_if_configured(request)
    job = _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    _ensure_job_tenant_write_access(request, job)
    return _set_review_comment_status(
        job_id,
        comment_id=comment_id,
        next_status="open",
        actor=_finding_actor_from_request(request),
        request_id=_resolve_request_id(request, request_id),
    )


@review_router.post("/hitl/approve")
def approve_checkpoint(
    req: HITLApprovalRequest,
    request: Request,
    request_id: Optional[str] = Query(default=None),
):
    require_api_key_if_configured(request)
    request_id_token = _resolve_request_id(request, request_id if request_id is not None else req.request_id)
    feedback = req.feedback if req.approved else (req.feedback or "Rejected")
    idempotency_fingerprint = _idempotency_fingerprint(
        {
            "op": "hitl_approve",
            "checkpoint_id": str(req.checkpoint_id),
            "approved": bool(req.approved),
            "feedback": str(feedback or ""),
        }
    )
    replay = _global_idempotency_replay_response(
        scope="hitl_approve",
        request_id=request_id_token,
        fingerprint=idempotency_fingerprint,
    )
    if replay is not None:
        return replay
    checkpoint = hitl_manager.get_checkpoint(req.checkpoint_id)
    if not checkpoint:
        raise HTTPException(status_code=404, detail="Checkpoint not found")
    _ensure_checkpoint_tenant_write_access(request, checkpoint)
    current_status = _checkpoint_status_token(checkpoint)
    target_status = HITLStatus.APPROVED.value if req.approved else HITLStatus.REJECTED.value
    if current_status != HITLStatus.PENDING.value:
        if current_status == target_status:
            response = {"status": target_status, "checkpoint_id": req.checkpoint_id, "already_decided": True}
            if request_id_token:
                response["request_id"] = request_id_token
            _store_global_idempotency_response(
                scope="hitl_approve",
                request_id=request_id_token,
                fingerprint=idempotency_fingerprint,
                response=response,
                persisted=True,
            )
            return response
        raise HTTPException(status_code=409, detail=f"Checkpoint already finalized with status: {current_status}")
    actor = _finding_actor_from_request(request)
    job_id_for_checkpoint, _job_for_checkpoint = _find_job_by_checkpoint_id(req.checkpoint_id)

    if req.approved:
        changed = hitl_manager.approve(req.checkpoint_id, feedback)
        response = {"status": HITLStatus.APPROVED.value, "checkpoint_id": req.checkpoint_id}
    else:
        changed = hitl_manager.reject(req.checkpoint_id, feedback)
        response = {"status": HITLStatus.REJECTED.value, "checkpoint_id": req.checkpoint_id}
    if not changed:
        raise HTTPException(status_code=409, detail="Checkpoint transition failed due to concurrent update")
    if job_id_for_checkpoint:
        _record_job_event(
            str(job_id_for_checkpoint),
            "hitl_checkpoint_decision",
            checkpoint_id=req.checkpoint_id,
            checkpoint_stage=checkpoint.get("stage"),
            checkpoint_status=response["status"],
            approved=bool(req.approved),
            feedback=feedback,
            actor=actor,
            request_id=request_id_token,
        )

    if request_id_token:
        response["request_id"] = request_id_token
    _store_global_idempotency_response(
        scope="hitl_approve",
        request_id=request_id_token,
        fingerprint=idempotency_fingerprint,
        response=response,
        persisted=True,
    )
    return response


@review_router.get("/hitl/pending", response_model=HITLPendingListPublicResponse, response_model_exclude_none=True)
def list_pending_hitl(request: Request, donor_id: Optional[str] = None, tenant_id: Optional[str] = None):
    require_api_key_if_configured(request, for_read=True)
    resolved_tenant_id = _resolve_tenant_id(request, explicit_tenant=tenant_id, require_if_enabled=True)
    pending = hitl_manager.list_pending(donor_id)
    if resolved_tenant_id:
        filtered = []
        for checkpoint in pending:
            checkpoint_tenant_id = _checkpoint_tenant_id(checkpoint)
            if checkpoint_tenant_id != resolved_tenant_id:
                continue
            cp = dict(checkpoint)
            cp["tenant_id"] = checkpoint_tenant_id
            filtered.append(cp)
        pending = filtered
    return {
        "pending_count": len(pending),
        "checkpoints": [public_checkpoint_payload(cp) for cp in pending],
    }
