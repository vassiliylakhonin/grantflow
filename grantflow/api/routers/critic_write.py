from __future__ import annotations

from typing import Any, Callable

from fastapi import APIRouter, Request

from grantflow.api.schemas import CriticFatalFlawPublicResponse, CriticFindingsBulkStatusPublicResponse

router = APIRouter()

_require_api_key_if_configured: Callable[..., None] | None = None
_set_critic_fatal_flaw_status: Callable[..., dict[str, Any]] | None = None
_set_critic_fatal_flaws_status_bulk: Callable[..., dict[str, Any]] | None = None
_finding_actor_from_request: Callable[[Request], str] | None = None


def configure_critic_write_router(
    *,
    require_api_key_if_configured: Callable[..., None],
    set_critic_fatal_flaw_status: Callable[..., dict[str, Any]],
    set_critic_fatal_flaws_status_bulk: Callable[..., dict[str, Any]],
    finding_actor_from_request: Callable[[Request], str],
) -> None:
    global _require_api_key_if_configured
    global _set_critic_fatal_flaw_status
    global _set_critic_fatal_flaws_status_bulk
    global _finding_actor_from_request

    _require_api_key_if_configured = require_api_key_if_configured
    _set_critic_fatal_flaw_status = set_critic_fatal_flaw_status
    _set_critic_fatal_flaws_status_bulk = set_critic_fatal_flaws_status_bulk
    _finding_actor_from_request = finding_actor_from_request


@router.post(
    "/status/{job_id}/critic/findings/{finding_id}/ack",
    response_model=CriticFatalFlawPublicResponse,
    response_model_exclude_none=True,
)
def acknowledge_status_critic_finding(job_id: str, finding_id: str, request: Request):
    _require_api_key_if_configured(request)
    return _set_critic_fatal_flaw_status(
        job_id,
        finding_id=finding_id,
        next_status="acknowledged",
        actor=_finding_actor_from_request(request),
    )


@router.post(
    "/status/{job_id}/critic/findings/{finding_id}/open",
    response_model=CriticFatalFlawPublicResponse,
    response_model_exclude_none=True,
)
def reopen_status_critic_finding(job_id: str, finding_id: str, request: Request):
    _require_api_key_if_configured(request)
    return _set_critic_fatal_flaw_status(
        job_id,
        finding_id=finding_id,
        next_status="open",
        actor=_finding_actor_from_request(request),
    )


@router.post(
    "/status/{job_id}/critic/findings/{finding_id}/resolve",
    response_model=CriticFatalFlawPublicResponse,
    response_model_exclude_none=True,
)
def resolve_status_critic_finding(job_id: str, finding_id: str, request: Request):
    _require_api_key_if_configured(request)
    return _set_critic_fatal_flaw_status(
        job_id,
        finding_id=finding_id,
        next_status="resolved",
        actor=_finding_actor_from_request(request),
    )


@router.post(
    "/status/{job_id}/critic/findings/bulk-status",
    response_model=CriticFindingsBulkStatusPublicResponse,
    response_model_exclude_none=True,
)
def bulk_status_critic_findings(job_id: str, req: Any, request: Request):
    _require_api_key_if_configured(request)
    next_status = str(req.next_status or "").strip().lower()
    return _set_critic_fatal_flaws_status_bulk(
        job_id,
        next_status=next_status,
        actor=_finding_actor_from_request(request),
        apply_to_all=bool(req.apply_to_all),
        finding_status=(req.finding_status or None),
        severity=(req.severity or None),
        section=(req.section or None),
        finding_ids=req.finding_ids,
    )
