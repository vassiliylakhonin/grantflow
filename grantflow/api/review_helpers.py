from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import HTTPException

from grantflow.api.constants import CRITIC_FINDING_SLA_HOURS, REVIEW_COMMENT_DEFAULT_SLA_HOURS
from grantflow.api.public_views import (
    REVIEW_WORKFLOW_OVERDUE_DEFAULT_HOURS,
    _critic_triage_summary_payload,
    public_job_review_workflow_payload,
)


def _normalize_finding_sla_profile(
    finding_sla_hours: Optional[Dict[str, Any]],
    *,
    default: Optional[Dict[str, int]] = None,
) -> Dict[str, int]:
    profile: Dict[str, int] = dict(default or CRITIC_FINDING_SLA_HOURS)
    if not isinstance(finding_sla_hours, dict):
        return profile
    for raw_key, raw_value in finding_sla_hours.items():
        key = str(raw_key or "").strip().lower()
        if key not in CRITIC_FINDING_SLA_HOURS:
            raise HTTPException(status_code=400, detail=f"Unsupported SLA severity key: {raw_key}")
        try:
            value = int(raw_value)
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail=f"Invalid SLA hours for {key}") from None
        if value <= 0 or value > 24 * 365:
            raise HTTPException(status_code=400, detail=f"SLA hours for {key} must be within 1..8760")
        profile[key] = value
    return profile


def _normalize_comment_sla_hours(default_comment_sla_hours: Optional[Any]) -> int:
    if default_comment_sla_hours is None:
        return int(REVIEW_COMMENT_DEFAULT_SLA_HOURS)
    try:
        value = int(default_comment_sla_hours)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid default_comment_sla_hours") from None
    if value <= 0 or value > 24 * 365:
        raise HTTPException(status_code=400, detail="default_comment_sla_hours must be within 1..8760")
    return value


def _review_workflow_sla_profile_payload(job_id: str, job: Dict[str, Any]) -> Dict[str, Any]:
    client_metadata = job.get("client_metadata")
    metadata = client_metadata if isinstance(client_metadata, dict) else {}
    saved_profile = metadata.get("sla_profile")
    saved_profile_dict = saved_profile if isinstance(saved_profile, dict) else {}
    has_saved_profile = bool(saved_profile_dict)

    finding_sla_hours_default = dict(CRITIC_FINDING_SLA_HOURS)
    comment_sla_default = int(REVIEW_COMMENT_DEFAULT_SLA_HOURS)
    source = "default"
    saved_profile_valid = True
    saved_profile_error: Optional[str] = None
    finding_sla_hours = finding_sla_hours_default
    default_comment_sla_hours = comment_sla_default

    if has_saved_profile:
        try:
            finding_sla_hours = _normalize_finding_sla_profile(
                saved_profile_dict.get("finding_sla_hours"),
                default=finding_sla_hours_default,
            )
            default_comment_sla_hours = _normalize_comment_sla_hours(
                saved_profile_dict.get("default_comment_sla_hours")
            )
            source = "saved"
        except HTTPException as exc:
            saved_profile_valid = False
            saved_profile_error = str(exc.detail)
            finding_sla_hours = finding_sla_hours_default
            default_comment_sla_hours = comment_sla_default
            source = "default"

    return {
        "job_id": str(job_id),
        "status": str(job.get("status") or ""),
        "source": source,
        "finding_sla_hours": finding_sla_hours,
        "default_comment_sla_hours": default_comment_sla_hours,
        "saved_profile_available": has_saved_profile,
        "saved_profile_valid": saved_profile_valid,
        "saved_profile_error": saved_profile_error,
        "saved_profile_updated_at": str(saved_profile_dict.get("updated_at") or "").strip() or None,
        "saved_profile_updated_by": str(saved_profile_dict.get("updated_by") or "").strip() or None,
    }


def _critic_findings_list_payload(
    job_id: str,
    job: Dict[str, Any],
    *,
    finding_status: Optional[str] = None,
    severity: Optional[str] = None,
    section: Optional[str] = None,
    version_id: Optional[str] = None,
    workflow_state: Optional[str] = None,
    include_resolved: bool = True,
    overdue_after_hours: int = REVIEW_WORKFLOW_OVERDUE_DEFAULT_HOURS,
) -> Dict[str, Any]:
    workflow_payload = public_job_review_workflow_payload(
        job_id,
        job,
        workflow_state=workflow_state,
        overdue_after_hours=overdue_after_hours,
    )
    findings_raw = workflow_payload.get("findings")
    findings = [dict(item) for item in findings_raw if isinstance(item, dict)] if isinstance(findings_raw, list) else []

    filtered: list[Dict[str, Any]] = []
    for row in findings:
        row_status = str(row.get("status") or "open").strip().lower()
        row_severity = str(row.get("severity") or "").strip().lower()
        row_section = str(row.get("section") or "").strip().lower()
        row_version_id = str(row.get("version_id") or "").strip() or None
        row_workflow_state = str(row.get("workflow_state") or "").strip().lower()

        if not include_resolved and row_status == "resolved":
            continue
        if finding_status is not None and row_status != finding_status:
            continue
        if severity is not None and row_severity != severity:
            continue
        if section is not None and row_section != section:
            continue
        if version_id is not None and row_version_id != version_id:
            continue
        if workflow_state is not None and row_workflow_state != workflow_state:
            continue
        filtered.append(row)

    finding_status_counts = {"open": 0, "acknowledged": 0, "resolved": 0}
    finding_severity_counts = {"high": 0, "medium": 0, "low": 0}
    pending_finding_count = 0
    overdue_finding_count = 0
    for row in filtered:
        row_status = str(row.get("status") or "open").strip().lower()
        row_severity = str(row.get("severity") or "").strip().lower()
        row_workflow_state = str(row.get("workflow_state") or "").strip().lower()
        if row_status in finding_status_counts:
            finding_status_counts[row_status] += 1
        if row_severity in finding_severity_counts:
            finding_severity_counts[row_severity] += 1
        if row_workflow_state == "pending":
            pending_finding_count += 1
        elif row_workflow_state == "overdue":
            overdue_finding_count += 1

    return {
        "job_id": str(job_id),
        "status": str(job.get("status") or ""),
        "filters": {
            "status": finding_status,
            "severity": severity,
            "section": section,
            "version_id": version_id,
            "workflow_state": workflow_state,
            "include_resolved": bool(include_resolved),
            "overdue_after_hours": int(overdue_after_hours),
        },
        "summary": {
            "finding_count": len(filtered),
            "open_finding_count": int(finding_status_counts.get("open", 0)),
            "acknowledged_finding_count": int(finding_status_counts.get("acknowledged", 0)),
            "resolved_finding_count": int(finding_status_counts.get("resolved", 0)),
            "pending_finding_count": pending_finding_count,
            "overdue_finding_count": overdue_finding_count,
            "finding_status_counts": finding_status_counts,
            "finding_severity_counts": finding_severity_counts,
            "triage_summary": _critic_triage_summary_payload(filtered),
        },
        "findings": filtered,
    }
