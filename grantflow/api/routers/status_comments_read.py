from __future__ import annotations

from typing import Any, Callable, Optional

from fastapi import APIRouter, HTTPException, Query, Request

from grantflow.api.schemas import JobCommentsPublicResponse

router = APIRouter()

_require_api_key_if_configured: Callable[..., None] | None = None
_normalize_critic_fatal_flaws_for_job: Callable[[str], Optional[dict[str, Any]]] | None = None
_get_job: Callable[[str], Optional[dict[str, Any]]] | None = None
_normalize_review_comments_for_job: Callable[[str], Optional[dict[str, Any]]] | None = None
_public_job_comments_payload: Callable[..., dict[str, Any]] | None = None


def configure_status_comments_read_router(
    *,
    require_api_key_if_configured: Callable[..., None],
    normalize_critic_fatal_flaws_for_job: Callable[[str], Optional[dict[str, Any]]],
    get_job: Callable[[str], Optional[dict[str, Any]]],
    normalize_review_comments_for_job: Callable[[str], Optional[dict[str, Any]]],
    public_job_comments_payload: Callable[..., dict[str, Any]],
) -> None:
    global _require_api_key_if_configured
    global _normalize_critic_fatal_flaws_for_job
    global _get_job
    global _normalize_review_comments_for_job
    global _public_job_comments_payload

    _require_api_key_if_configured = require_api_key_if_configured
    _normalize_critic_fatal_flaws_for_job = normalize_critic_fatal_flaws_for_job
    _get_job = get_job
    _normalize_review_comments_for_job = normalize_review_comments_for_job
    _public_job_comments_payload = public_job_comments_payload


@router.get(
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
    _require_api_key_if_configured(request, for_read=True)
    job = _normalize_critic_fatal_flaws_for_job(job_id) or _get_job(job_id)
    job = _normalize_review_comments_for_job(job_id) or job
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return _public_job_comments_payload(
        job_id,
        job,
        section=section,
        comment_status=comment_status,
        version_id=version_id,
    )
