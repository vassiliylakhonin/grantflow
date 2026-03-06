from __future__ import annotations

from typing import Optional

from fastapi import HTTPException, Query, Request

from grantflow.api.idempotency_store_facade import _list_jobs
from grantflow.api.filters import _validated_filter_token
from grantflow.api.public_views import (
    REVIEW_WORKFLOW_OVERDUE_DEFAULT_HOURS,
    REVIEW_WORKFLOW_STATE_FILTER_VALUES,
    public_portfolio_metrics_payload,
    public_portfolio_quality_payload,
    public_portfolio_review_workflow_payload,
    public_portfolio_review_workflow_sla_hotspots_payload,
    public_portfolio_review_workflow_sla_hotspots_trends_payload,
    public_portfolio_review_workflow_sla_payload,
    public_portfolio_review_workflow_sla_trends_payload,
    public_portfolio_review_workflow_trends_payload,
)
from grantflow.api.routers import portfolio_router
from grantflow.api.schemas import (
    PortfolioMetricsPublicResponse,
    PortfolioQualityPublicResponse,
    PortfolioReviewWorkflowPublicResponse,
    PortfolioReviewWorkflowSLAHotspotsPublicResponse,
    PortfolioReviewWorkflowSLAHotspotsTrendsPublicResponse,
    PortfolioReviewWorkflowSLAPublicResponse,
    PortfolioReviewWorkflowSLATrendsPublicResponse,
    PortfolioReviewWorkflowTrendsPublicResponse,
)
from grantflow.api.security import require_api_key_if_configured
from grantflow.api.tenant import _filter_jobs_by_tenant, _resolve_tenant_id


@portfolio_router.get(
    "/portfolio/metrics",
    response_model=PortfolioMetricsPublicResponse,
    response_model_exclude_none=True,
)
def get_portfolio_metrics(
    request: Request,
    donor_id: Optional[str] = None,
    tenant_id: Optional[str] = Query(default=None),
    status: Optional[str] = None,
    hitl_enabled: Optional[bool] = Query(default=None),
    warning_level: Optional[str] = None,
    grounding_risk_level: Optional[str] = None,
    toc_text_risk_level: Optional[str] = None,
    mel_risk_level: Optional[str] = None,
):
    require_api_key_if_configured(request, for_read=True)
    resolved_tenant_id = _resolve_tenant_id(request, explicit_tenant=tenant_id, require_if_enabled=True)
    jobs = _filter_jobs_by_tenant(_list_jobs(), resolved_tenant_id)
    return public_portfolio_metrics_payload(
        jobs,
        donor_id=(donor_id or None),
        status=(status or None),
        hitl_enabled=hitl_enabled,
        warning_level=(warning_level or None),
        grounding_risk_level=(grounding_risk_level or None),
        toc_text_risk_level=(toc_text_risk_level or None),
        mel_risk_level=(mel_risk_level or None),
    )


@portfolio_router.get(
    "/portfolio/quality",
    response_model=PortfolioQualityPublicResponse,
    response_model_exclude_none=True,
)
def get_portfolio_quality(
    request: Request,
    donor_id: Optional[str] = None,
    tenant_id: Optional[str] = Query(default=None),
    status: Optional[str] = None,
    hitl_enabled: Optional[bool] = Query(default=None),
    warning_level: Optional[str] = None,
    grounding_risk_level: Optional[str] = None,
    finding_status: Optional[str] = None,
    finding_severity: Optional[str] = None,
    toc_text_risk_level: Optional[str] = None,
    mel_risk_level: Optional[str] = None,
):
    require_api_key_if_configured(request, for_read=True)
    resolved_tenant_id = _resolve_tenant_id(request, explicit_tenant=tenant_id, require_if_enabled=True)
    jobs = _filter_jobs_by_tenant(_list_jobs(), resolved_tenant_id)
    return public_portfolio_quality_payload(
        jobs,
        donor_id=(donor_id or None),
        status=(status or None),
        hitl_enabled=hitl_enabled,
        warning_level=(warning_level or None),
        grounding_risk_level=(grounding_risk_level or None),
        finding_status=(finding_status or None),
        finding_severity=(finding_severity or None),
        toc_text_risk_level=(toc_text_risk_level or None),
        mel_risk_level=(mel_risk_level or None),
    )


@portfolio_router.get(
    "/portfolio/review-workflow",
    response_model=PortfolioReviewWorkflowPublicResponse,
    response_model_exclude_none=True,
)
def get_portfolio_review_workflow(
    request: Request,
    donor_id: Optional[str] = None,
    tenant_id: Optional[str] = Query(default=None),
    status: Optional[str] = None,
    hitl_enabled: Optional[bool] = Query(default=None),
    warning_level: Optional[str] = None,
    grounding_risk_level: Optional[str] = None,
    toc_text_risk_level: Optional[str] = None,
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
    resolved_tenant_id = _resolve_tenant_id(request, explicit_tenant=tenant_id, require_if_enabled=True)
    jobs = _filter_jobs_by_tenant(_list_jobs(), resolved_tenant_id)
    return public_portfolio_review_workflow_payload(
        jobs,
        donor_id=(donor_id or None),
        status=(status or None),
        hitl_enabled=hitl_enabled,
        warning_level=(warning_level or None),
        grounding_risk_level=(grounding_risk_level or None),
        toc_text_risk_level=(toc_text_risk_level or None),
        event_type=(event_type or None),
        finding_id=(finding_id or None),
        finding_code=(str(finding_code or "").strip() or None),
        finding_section=finding_section_filter,
        comment_status=(comment_status or None),
        workflow_state=workflow_state_filter,
        overdue_after_hours=overdue_after_hours,
    )


@portfolio_router.get(
    "/portfolio/review-workflow/sla",
    response_model=PortfolioReviewWorkflowSLAPublicResponse,
    response_model_exclude_none=True,
)
def get_portfolio_review_workflow_sla(
    request: Request,
    donor_id: Optional[str] = None,
    tenant_id: Optional[str] = Query(default=None),
    status: Optional[str] = None,
    hitl_enabled: Optional[bool] = Query(default=None),
    warning_level: Optional[str] = None,
    grounding_risk_level: Optional[str] = None,
    toc_text_risk_level: Optional[str] = None,
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
    resolved_tenant_id = _resolve_tenant_id(request, explicit_tenant=tenant_id, require_if_enabled=True)
    jobs = _filter_jobs_by_tenant(_list_jobs(), resolved_tenant_id)
    return public_portfolio_review_workflow_sla_payload(
        jobs,
        donor_id=(donor_id or None),
        status=(status or None),
        hitl_enabled=hitl_enabled,
        warning_level=(warning_level or None),
        grounding_risk_level=(grounding_risk_level or None),
        toc_text_risk_level=(toc_text_risk_level or None),
        finding_id=(finding_id or None),
        finding_code=(str(finding_code or "").strip() or None),
        finding_section=finding_section_filter,
        comment_status=(comment_status or None),
        workflow_state=workflow_state_filter,
        overdue_after_hours=overdue_after_hours,
        top_limit=top_limit,
    )


@portfolio_router.get(
    "/portfolio/review-workflow/sla/hotspots",
    response_model=PortfolioReviewWorkflowSLAHotspotsPublicResponse,
    response_model_exclude_none=True,
)
def get_portfolio_review_workflow_sla_hotspots(
    request: Request,
    donor_id: Optional[str] = None,
    tenant_id: Optional[str] = Query(default=None),
    status: Optional[str] = None,
    hitl_enabled: Optional[bool] = Query(default=None),
    warning_level: Optional[str] = None,
    grounding_risk_level: Optional[str] = None,
    toc_text_risk_level: Optional[str] = None,
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
    resolved_tenant_id = _resolve_tenant_id(request, explicit_tenant=tenant_id, require_if_enabled=True)
    jobs = _filter_jobs_by_tenant(_list_jobs(), resolved_tenant_id)
    return public_portfolio_review_workflow_sla_hotspots_payload(
        jobs,
        donor_id=(donor_id or None),
        status=(status or None),
        hitl_enabled=hitl_enabled,
        warning_level=(warning_level or None),
        grounding_risk_level=(grounding_risk_level or None),
        toc_text_risk_level=(toc_text_risk_level or None),
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


@portfolio_router.get(
    "/portfolio/review-workflow/sla/hotspots/trends",
    response_model=PortfolioReviewWorkflowSLAHotspotsTrendsPublicResponse,
    response_model_exclude_none=True,
)
def get_portfolio_review_workflow_sla_hotspots_trends(
    request: Request,
    donor_id: Optional[str] = None,
    tenant_id: Optional[str] = Query(default=None),
    status: Optional[str] = None,
    hitl_enabled: Optional[bool] = Query(default=None),
    warning_level: Optional[str] = None,
    grounding_risk_level: Optional[str] = None,
    toc_text_risk_level: Optional[str] = None,
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
    resolved_tenant_id = _resolve_tenant_id(request, explicit_tenant=tenant_id, require_if_enabled=True)
    jobs = _filter_jobs_by_tenant(_list_jobs(), resolved_tenant_id)
    return public_portfolio_review_workflow_sla_hotspots_trends_payload(
        jobs,
        donor_id=(donor_id or None),
        status=(status or None),
        hitl_enabled=hitl_enabled,
        warning_level=(warning_level or None),
        grounding_risk_level=(grounding_risk_level or None),
        toc_text_risk_level=(toc_text_risk_level or None),
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


@portfolio_router.get(
    "/portfolio/review-workflow/trends",
    response_model=PortfolioReviewWorkflowTrendsPublicResponse,
    response_model_exclude_none=True,
)
def get_portfolio_review_workflow_trends(
    request: Request,
    donor_id: Optional[str] = None,
    tenant_id: Optional[str] = Query(default=None),
    status: Optional[str] = None,
    hitl_enabled: Optional[bool] = Query(default=None),
    warning_level: Optional[str] = None,
    grounding_risk_level: Optional[str] = None,
    toc_text_risk_level: Optional[str] = None,
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
    resolved_tenant_id = _resolve_tenant_id(request, explicit_tenant=tenant_id, require_if_enabled=True)
    jobs = _filter_jobs_by_tenant(_list_jobs(), resolved_tenant_id)
    return public_portfolio_review_workflow_trends_payload(
        jobs,
        donor_id=(donor_id or None),
        status=(status or None),
        hitl_enabled=hitl_enabled,
        warning_level=(warning_level or None),
        grounding_risk_level=(grounding_risk_level or None),
        toc_text_risk_level=(toc_text_risk_level or None),
        event_type=(event_type or None),
        finding_id=(finding_id or None),
        finding_code=(str(finding_code or "").strip() or None),
        finding_section=finding_section_filter,
        comment_status=(comment_status or None),
        workflow_state=workflow_state_filter,
        overdue_after_hours=overdue_after_hours,
    )


@portfolio_router.get(
    "/portfolio/review-workflow/sla/trends",
    response_model=PortfolioReviewWorkflowSLATrendsPublicResponse,
    response_model_exclude_none=True,
)
def get_portfolio_review_workflow_sla_trends(
    request: Request,
    donor_id: Optional[str] = None,
    tenant_id: Optional[str] = Query(default=None),
    status: Optional[str] = None,
    hitl_enabled: Optional[bool] = Query(default=None),
    warning_level: Optional[str] = None,
    grounding_risk_level: Optional[str] = None,
    toc_text_risk_level: Optional[str] = None,
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
    resolved_tenant_id = _resolve_tenant_id(request, explicit_tenant=tenant_id, require_if_enabled=True)
    jobs = _filter_jobs_by_tenant(_list_jobs(), resolved_tenant_id)
    return public_portfolio_review_workflow_sla_trends_payload(
        jobs,
        donor_id=(donor_id or None),
        status=(status or None),
        hitl_enabled=hitl_enabled,
        warning_level=(warning_level or None),
        grounding_risk_level=(grounding_risk_level or None),
        toc_text_risk_level=(toc_text_risk_level or None),
        finding_id=(finding_id or None),
        finding_code=(str(finding_code or "").strip() or None),
        finding_section=finding_section_filter,
        comment_status=(comment_status or None),
        workflow_state=workflow_state_filter,
        overdue_after_hours=overdue_after_hours,
    )
