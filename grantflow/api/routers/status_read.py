from __future__ import annotations

from typing import Any, Callable, Optional

from fastapi import APIRouter, HTTPException, Query, Request

from grantflow.api.schemas import (
    JobCitationsPublicResponse,
    JobCriticPublicResponse,
    JobDiffPublicResponse,
    JobEventsPublicResponse,
    JobExportPayloadPublicResponse,
    JobMetricsPublicResponse,
    JobQualitySummaryPublicResponse,
    JobStatusPublicResponse,
    JobVersionsPublicResponse,
)

router = APIRouter()

_require_api_key_if_configured: Callable[..., None] | None = None
_get_job: Callable[[str], Optional[dict[str, Any]]] | None = None
_normalize_critic_fatal_flaws_for_job: Callable[[str], Optional[dict[str, Any]]] | None = None
_ingest_inventory: Callable[..., list[dict[str, Any]]] | None = None

_public_job_payload: Callable[..., dict[str, Any]] | None = None
_public_job_citations_payload: Callable[..., dict[str, Any]] | None = None
_public_job_export_payload: Callable[..., dict[str, Any]] | None = None
_public_job_versions_payload: Callable[..., dict[str, Any]] | None = None
_public_job_diff_payload: Callable[..., dict[str, Any]] | None = None
_public_job_events_payload: Callable[..., dict[str, Any]] | None = None
_public_job_metrics_payload: Callable[..., dict[str, Any]] | None = None
_public_job_quality_payload: Callable[..., dict[str, Any]] | None = None
_public_job_critic_payload: Callable[..., dict[str, Any]] | None = None


def configure_status_read_router(
    *,
    require_api_key_if_configured: Callable[..., None],
    get_job: Callable[[str], Optional[dict[str, Any]]],
    normalize_critic_fatal_flaws_for_job: Callable[[str], Optional[dict[str, Any]]],
    ingest_inventory: Callable[..., list[dict[str, Any]]],
    public_job_payload: Callable[..., dict[str, Any]],
    public_job_citations_payload: Callable[..., dict[str, Any]],
    public_job_export_payload: Callable[..., dict[str, Any]],
    public_job_versions_payload: Callable[..., dict[str, Any]],
    public_job_diff_payload: Callable[..., dict[str, Any]],
    public_job_events_payload: Callable[..., dict[str, Any]],
    public_job_metrics_payload: Callable[..., dict[str, Any]],
    public_job_quality_payload: Callable[..., dict[str, Any]],
    public_job_critic_payload: Callable[..., dict[str, Any]],
) -> None:
    global _require_api_key_if_configured
    global _get_job
    global _normalize_critic_fatal_flaws_for_job
    global _ingest_inventory
    global _public_job_payload
    global _public_job_citations_payload
    global _public_job_export_payload
    global _public_job_versions_payload
    global _public_job_diff_payload
    global _public_job_events_payload
    global _public_job_metrics_payload
    global _public_job_quality_payload
    global _public_job_critic_payload

    _require_api_key_if_configured = require_api_key_if_configured
    _get_job = get_job
    _normalize_critic_fatal_flaws_for_job = normalize_critic_fatal_flaws_for_job
    _ingest_inventory = ingest_inventory
    _public_job_payload = public_job_payload
    _public_job_citations_payload = public_job_citations_payload
    _public_job_export_payload = public_job_export_payload
    _public_job_versions_payload = public_job_versions_payload
    _public_job_diff_payload = public_job_diff_payload
    _public_job_events_payload = public_job_events_payload
    _public_job_metrics_payload = public_job_metrics_payload
    _public_job_quality_payload = public_job_quality_payload
    _public_job_critic_payload = public_job_critic_payload


def _job_or_404(job_id: str) -> dict[str, Any]:
    job = _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/status/{job_id}", response_model=JobStatusPublicResponse, response_model_exclude_none=True)
def get_status(job_id: str, request: Request):
    _require_api_key_if_configured(request, for_read=True)
    return _public_job_payload(_job_or_404(job_id))


@router.get("/status/{job_id}/citations", response_model=JobCitationsPublicResponse, response_model_exclude_none=True)
def get_status_citations(job_id: str, request: Request):
    _require_api_key_if_configured(request, for_read=True)
    job = _job_or_404(job_id)
    return _public_job_citations_payload(job_id, job)


@router.get(
    "/status/{job_id}/export-payload",
    response_model=JobExportPayloadPublicResponse,
    response_model_exclude_none=True,
)
def get_status_export_payload(job_id: str, request: Request):
    _require_api_key_if_configured(request, for_read=True)
    job = _normalize_critic_fatal_flaws_for_job(job_id) or _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    state = job.get("state")
    state_dict = state if isinstance(state, dict) else {}
    donor = str(
        state_dict.get("donor_id")
        or state_dict.get("donor")
        or ((job.get("client_metadata") or {}) if isinstance(job.get("client_metadata"), dict) else {}).get("donor_id")
        or ""
    ).strip()
    inventory_rows = _ingest_inventory(donor_id=donor or None)
    return _public_job_export_payload(job_id, job, ingest_inventory_rows=inventory_rows)


@router.get("/status/{job_id}/versions", response_model=JobVersionsPublicResponse, response_model_exclude_none=True)
def get_status_versions(job_id: str, request: Request, section: Optional[str] = None):
    _require_api_key_if_configured(request, for_read=True)
    job = _job_or_404(job_id)
    return _public_job_versions_payload(job_id, job, section=section)


@router.get("/status/{job_id}/diff", response_model=JobDiffPublicResponse, response_model_exclude_none=True)
def get_status_diff(
    job_id: str,
    request: Request,
    section: Optional[str] = None,
    from_version_id: Optional[str] = Query(default=None),
    to_version_id: Optional[str] = Query(default=None),
):
    _require_api_key_if_configured(request, for_read=True)
    job = _job_or_404(job_id)
    return _public_job_diff_payload(
        job_id,
        job,
        section=section,
        from_version_id=from_version_id,
        to_version_id=to_version_id,
    )


@router.get("/status/{job_id}/events", response_model=JobEventsPublicResponse, response_model_exclude_none=True)
def get_status_events(job_id: str, request: Request):
    _require_api_key_if_configured(request, for_read=True)
    job = _job_or_404(job_id)
    return _public_job_events_payload(job_id, job)


@router.get("/status/{job_id}/metrics", response_model=JobMetricsPublicResponse, response_model_exclude_none=True)
def get_status_metrics(job_id: str, request: Request):
    _require_api_key_if_configured(request, for_read=True)
    job = _job_or_404(job_id)
    return _public_job_metrics_payload(job_id, job)


@router.get("/status/{job_id}/quality", response_model=JobQualitySummaryPublicResponse, response_model_exclude_none=True)
def get_status_quality(job_id: str, request: Request):
    _require_api_key_if_configured(request, for_read=True)
    job = _normalize_critic_fatal_flaws_for_job(job_id) or _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    state = job.get("state")
    state_dict = state if isinstance(state, dict) else {}
    donor = str(
        state_dict.get("donor_id")
        or state_dict.get("donor")
        or ((job.get("client_metadata") or {}) if isinstance(job.get("client_metadata"), dict) else {}).get("donor_id")
        or ""
    ).strip()
    inventory_rows = _ingest_inventory(donor_id=donor or None)
    return _public_job_quality_payload(job_id, job, ingest_inventory_rows=inventory_rows)


@router.get("/status/{job_id}/critic", response_model=JobCriticPublicResponse, response_model_exclude_none=True)
def get_status_critic(job_id: str, request: Request):
    _require_api_key_if_configured(request, for_read=True)
    job = _normalize_critic_fatal_flaws_for_job(job_id) or _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return _public_job_critic_payload(job_id, job)
