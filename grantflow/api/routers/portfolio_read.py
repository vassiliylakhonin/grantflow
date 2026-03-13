from __future__ import annotations

from typing import Any, Callable, Literal, Optional

from fastapi import APIRouter, Query, Request

from grantflow.api.schemas import PortfolioMetricsPublicResponse, PortfolioQualityPublicResponse

router = APIRouter()

_require_api_key_if_configured: Callable[..., None] | None = None
_list_jobs: Callable[[], list[dict[str, Any]]] | None = None
_public_portfolio_metrics_payload: Callable[..., dict[str, Any]] | None = None
_public_portfolio_quality_payload: Callable[..., dict[str, Any]] | None = None
_portfolio_export_response: Callable[..., Any] | None = None
_public_portfolio_metrics_csv_text: Callable[..., str] | None = None
_public_portfolio_quality_csv_text: Callable[..., str] | None = None


def configure_portfolio_read_router(
    *,
    require_api_key_if_configured: Callable[..., None],
    list_jobs: Callable[[], list[dict[str, Any]]],
    public_portfolio_metrics_payload: Callable[..., dict[str, Any]],
    public_portfolio_quality_payload: Callable[..., dict[str, Any]],
    portfolio_export_response: Callable[..., Any],
    public_portfolio_metrics_csv_text: Callable[..., str],
    public_portfolio_quality_csv_text: Callable[..., str],
) -> None:
    global _require_api_key_if_configured
    global _list_jobs
    global _public_portfolio_metrics_payload
    global _public_portfolio_quality_payload
    global _portfolio_export_response
    global _public_portfolio_metrics_csv_text
    global _public_portfolio_quality_csv_text

    _require_api_key_if_configured = require_api_key_if_configured
    _list_jobs = list_jobs
    _public_portfolio_metrics_payload = public_portfolio_metrics_payload
    _public_portfolio_quality_payload = public_portfolio_quality_payload
    _portfolio_export_response = portfolio_export_response
    _public_portfolio_metrics_csv_text = public_portfolio_metrics_csv_text
    _public_portfolio_quality_csv_text = public_portfolio_quality_csv_text


@router.get("/portfolio/metrics", response_model=PortfolioMetricsPublicResponse, response_model_exclude_none=True)
def get_portfolio_metrics(
    request: Request,
    donor_id: Optional[str] = None,
    status: Optional[str] = None,
    hitl_enabled: Optional[bool] = Query(default=None),
    warning_level: Optional[str] = None,
    grounding_risk_level: Optional[str] = None,
):
    _require_api_key_if_configured(request, for_read=True)
    jobs = _list_jobs()
    return _public_portfolio_metrics_payload(
        jobs,
        donor_id=(donor_id or None),
        status=(status or None),
        hitl_enabled=hitl_enabled,
        warning_level=(warning_level or None),
        grounding_risk_level=(grounding_risk_level or None),
    )


@router.get("/portfolio/metrics/export")
def export_portfolio_metrics(
    request: Request,
    donor_id: Optional[str] = None,
    status: Optional[str] = None,
    hitl_enabled: Optional[bool] = Query(default=None),
    warning_level: Optional[str] = None,
    grounding_risk_level: Optional[str] = None,
    format: Literal["csv", "json"] = Query(default="csv"),
    gzip_enabled: bool = Query(default=False, alias="gzip"),
):
    _require_api_key_if_configured(request, for_read=True)
    jobs = _list_jobs()
    payload = _public_portfolio_metrics_payload(
        jobs,
        donor_id=(donor_id or None),
        status=(status or None),
        hitl_enabled=hitl_enabled,
        warning_level=(warning_level or None),
        grounding_risk_level=(grounding_risk_level or None),
    )

    return _portfolio_export_response(
        payload=payload,
        filename_prefix="grantflow_portfolio_metrics",
        donor_id=donor_id,
        status=status,
        hitl_enabled=hitl_enabled,
        export_format=format,
        gzip_enabled=gzip_enabled,
        csv_renderer=_public_portfolio_metrics_csv_text,
    )


@router.get("/portfolio/quality", response_model=PortfolioQualityPublicResponse, response_model_exclude_none=True)
def get_portfolio_quality(
    request: Request,
    donor_id: Optional[str] = None,
    status: Optional[str] = None,
    hitl_enabled: Optional[bool] = Query(default=None),
    warning_level: Optional[str] = None,
    grounding_risk_level: Optional[str] = None,
    finding_status: Optional[str] = None,
    finding_severity: Optional[str] = None,
):
    _require_api_key_if_configured(request, for_read=True)
    jobs = _list_jobs()
    return _public_portfolio_quality_payload(
        jobs,
        donor_id=(donor_id or None),
        status=(status or None),
        hitl_enabled=hitl_enabled,
        warning_level=(warning_level or None),
        grounding_risk_level=(grounding_risk_level or None),
        finding_status=(finding_status or None),
        finding_severity=(finding_severity or None),
    )


@router.get("/portfolio/quality/export")
def export_portfolio_quality(
    request: Request,
    donor_id: Optional[str] = None,
    status: Optional[str] = None,
    hitl_enabled: Optional[bool] = Query(default=None),
    warning_level: Optional[str] = None,
    grounding_risk_level: Optional[str] = None,
    finding_status: Optional[str] = None,
    finding_severity: Optional[str] = None,
    format: Literal["csv", "json"] = Query(default="csv"),
    gzip_enabled: bool = Query(default=False, alias="gzip"),
):
    _require_api_key_if_configured(request, for_read=True)
    jobs = _list_jobs()
    payload = _public_portfolio_quality_payload(
        jobs,
        donor_id=(donor_id or None),
        status=(status or None),
        hitl_enabled=hitl_enabled,
        warning_level=(warning_level or None),
        grounding_risk_level=(grounding_risk_level or None),
        finding_status=(finding_status or None),
        finding_severity=(finding_severity or None),
    )

    return _portfolio_export_response(
        payload=payload,
        filename_prefix="grantflow_portfolio_quality",
        donor_id=donor_id,
        status=status,
        hitl_enabled=hitl_enabled,
        export_format=format,
        gzip_enabled=gzip_enabled,
        csv_renderer=_public_portfolio_quality_csv_text,
    )
