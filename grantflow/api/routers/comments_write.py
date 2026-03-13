from __future__ import annotations

from typing import Any, Callable, Optional

from fastapi import APIRouter, HTTPException, Request

from grantflow.api.schemas import ReviewCommentPublicResponse

router = APIRouter()

_require_api_key_if_configured: Callable[..., None] | None = None
_get_job: Callable[[str], Optional[dict[str, Any]]] | None = None
_job_draft_version_exists_for_section: Callable[..., bool] | None = None
_normalize_critic_fatal_flaws_for_job: Callable[[str], Optional[dict[str, Any]]] | None = None
_find_critic_fatal_flaw: Callable[..., Optional[dict[str, Any]]] | None = None
_finding_primary_id: Callable[[dict[str, Any]], Optional[str]] | None = None
_append_review_comment: Callable[..., dict[str, Any]] | None = None
_set_review_comment_status: Callable[..., dict[str, Any]] | None = None
_review_comment_sections: set[str] = {"toc", "logframe", "general"}


def configure_comments_write_router(
    *,
    require_api_key_if_configured: Callable[..., None],
    get_job: Callable[[str], Optional[dict[str, Any]]],
    job_draft_version_exists_for_section: Callable[..., bool],
    normalize_critic_fatal_flaws_for_job: Callable[[str], Optional[dict[str, Any]]],
    find_critic_fatal_flaw: Callable[..., Optional[dict[str, Any]]],
    finding_primary_id: Callable[[dict[str, Any]], Optional[str]],
    append_review_comment: Callable[..., dict[str, Any]],
    set_review_comment_status: Callable[..., dict[str, Any]],
    review_comment_sections: set[str],
) -> None:
    global _require_api_key_if_configured
    global _get_job
    global _job_draft_version_exists_for_section
    global _normalize_critic_fatal_flaws_for_job
    global _find_critic_fatal_flaw
    global _finding_primary_id
    global _append_review_comment
    global _set_review_comment_status
    global _review_comment_sections

    _require_api_key_if_configured = require_api_key_if_configured
    _get_job = get_job
    _job_draft_version_exists_for_section = job_draft_version_exists_for_section
    _normalize_critic_fatal_flaws_for_job = normalize_critic_fatal_flaws_for_job
    _find_critic_fatal_flaw = find_critic_fatal_flaw
    _finding_primary_id = finding_primary_id
    _append_review_comment = append_review_comment
    _set_review_comment_status = set_review_comment_status
    _review_comment_sections = set(review_comment_sections)


@router.post(
    "/status/{job_id}/comments",
    response_model=ReviewCommentPublicResponse,
    response_model_exclude_none=True,
)
def add_status_comment(job_id: str, req: dict[str, Any], request: Request):
    _require_api_key_if_configured(request)
    job = _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    section_raw = req.get("section")
    section = str(section_raw or "").strip().lower()
    if section not in _review_comment_sections:
        raise HTTPException(status_code=400, detail=f"Unsupported section: {section or section_raw}")

    message = str(req.get("message") or "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="Missing comment message")
    if len(message) > 4000:
        raise HTTPException(status_code=400, detail="Comment message is too long")

    author = str(req.get("author") or "").strip() or None
    version_id = str(req.get("version_id") or "").strip() or None
    linked_finding_id = str(req.get("linked_finding_id") or "").strip() or None

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
        linked_finding_id = _finding_primary_id(finding) or linked_finding_id
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
    )


@router.post(
    "/status/{job_id}/comments/{comment_id}/resolve",
    response_model=ReviewCommentPublicResponse,
    response_model_exclude_none=True,
)
def resolve_status_comment(job_id: str, comment_id: str, request: Request):
    _require_api_key_if_configured(request)
    return _set_review_comment_status(job_id, comment_id=comment_id, next_status="resolved")


@router.post(
    "/status/{job_id}/comments/{comment_id}/reopen",
    response_model=ReviewCommentPublicResponse,
    response_model_exclude_none=True,
)
def reopen_status_comment(job_id: str, comment_id: str, request: Request):
    _require_api_key_if_configured(request)
    return _set_review_comment_status(job_id, comment_id=comment_id, next_status="open")
