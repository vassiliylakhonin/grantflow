from __future__ import annotations

from typing import Any, Dict, Literal, Optional

from fastapi import HTTPException

from grantflow.api.constants import (
    CRITIC_FINDING_SLA_HOURS,
    HITL_HISTORY_EVENT_TYPES,
    REVIEW_COMMENT_DEFAULT_SLA_HOURS,
    STATUS_WEBHOOK_EVENTS,
)
from grantflow.api.idempotency_store_facade import _get_job, _list_jobs, _record_job_event, _set_job, _update_job
from grantflow.api.public_views import public_job_payload
from grantflow.api.review_helpers import _normalize_comment_sla_hours, _normalize_finding_sla_profile
from grantflow.api.review_runtime_helpers import (
    _checkpoint_status_token,
    _clear_hitl_runtime_state,
    _comment_sla_hours,
    _finding_sla_hours,
    _iso_plus_hours,
    _utcnow_iso,
)
from grantflow.api.webhooks import send_job_webhook_event
from grantflow.swarm.findings import finding_primary_id, state_critic_findings, write_state_critic_findings
from grantflow.swarm.hitl import HITLStatus, hitl_manager
from grantflow.swarm.state_contract import normalize_state_contract, state_donor_id

HITLStartAt = Literal["start", "architect", "mel", "critic"]


def _find_job_by_checkpoint_id(checkpoint_id: str) -> tuple[Optional[str], Optional[Dict[str, Any]]]:
    token = str(checkpoint_id or "").strip()
    if not token:
        return None, None
    for job_id, job in _list_jobs().items():
        if not isinstance(job, dict):
            continue
        if str(job.get("checkpoint_id") or "").strip() == token:
            return str(job_id), job
    return None, None


def _is_hitl_history_event(event: Dict[str, Any]) -> bool:
    event_type = str(event.get("type") or "").strip()
    if event_type not in HITL_HISTORY_EVENT_TYPES:
        return False
    if event_type != "status_changed":
        return True
    from_status = str(event.get("from_status") or "").strip().lower()
    to_status = str(event.get("to_status") or "").strip().lower()
    return from_status == "pending_hitl" or to_status == "pending_hitl"


def _hitl_history_payload(
    job_id: str,
    job: Dict[str, Any],
    *,
    event_type: Optional[str] = None,
    checkpoint_id: Optional[str] = None,
) -> Dict[str, Any]:
    event_type_filter = str(event_type or "").strip() or None
    if event_type_filter and event_type_filter not in HITL_HISTORY_EVENT_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported event_type filter")
    checkpoint_filter = str(checkpoint_id or "").strip() or None
    raw_events_value = job.get("job_events")
    raw_events: list[Any] = raw_events_value if isinstance(raw_events_value, list) else []
    events: list[Dict[str, Any]] = []
    for row in raw_events:
        if not isinstance(row, dict) or not _is_hitl_history_event(row):
            continue
        row_type = str(row.get("type") or "").strip()
        row_checkpoint_id = str(row.get("checkpoint_id") or "").strip() or None
        if event_type_filter and row_type != event_type_filter:
            continue
        if checkpoint_filter and row_checkpoint_id != checkpoint_filter:
            continue
        status = str(row.get("status") or "").strip()
        from_status = str(row.get("from_status") or "").strip()
        to_status = str(row.get("to_status") or "").strip()
        event: Dict[str, Any] = {
            "event_id": row.get("event_id"),
            "ts": row.get("ts"),
            "type": row_type,
            "from_status": from_status or None,
            "to_status": to_status or None,
            "status": status or None,
            "checkpoint_id": row_checkpoint_id,
            "checkpoint_stage": str(row.get("checkpoint_stage") or row.get("stage") or "").strip() or None,
            "checkpoint_status": str(row.get("checkpoint_status") or "").strip() or None,
            "resuming_from": str(row.get("resuming_from") or "").strip() or None,
            "approved": row.get("approved") if isinstance(row.get("approved"), bool) else None,
            "feedback": str(row.get("feedback") or "").strip() or None,
            "actor": str(row.get("actor") or "").strip() or None,
            "request_id": str(row.get("request_id") or "").strip() or None,
            "reason": str(row.get("reason") or "").strip() or None,
            "backend": str(row.get("backend") or "").strip() or None,
        }
        events.append(event)
    events.sort(key=lambda item: str(item.get("ts") or ""), reverse=True)
    event_type_counts: Dict[str, int] = {}
    for row in events:
        row_type = str(row.get("type") or "").strip()
        if row_type:
            event_type_counts[row_type] = int(event_type_counts.get(row_type, 0)) + 1
    return {
        "job_id": str(job_id),
        "status": str(job.get("status") or ""),
        "filters": {"event_type": event_type_filter, "checkpoint_id": checkpoint_filter},
        "event_count": len(events),
        "event_type_counts": event_type_counts,
        "events": events,
    }


def _job_draft_version_exists_for_section(job: Dict[str, Any], *, section: str, version_id: str) -> bool:
    state = job.get("state")
    if not isinstance(state, dict):
        return False
    raw_versions = state.get("draft_versions")
    if not isinstance(raw_versions, list):
        return False
    for item in raw_versions:
        if not isinstance(item, dict):
            continue
        if str(item.get("version_id") or "") != version_id:
            continue
        if str(item.get("section") or "") != section:
            continue
        return True
    return False


def _resolve_sla_profile_for_recompute(
    *,
    job: Dict[str, Any],
    finding_sla_hours_override: Optional[Dict[str, Any]],
    default_comment_sla_hours: Optional[Any],
    use_saved_profile: bool,
) -> tuple[Dict[str, int], int]:
    base_finding = dict(CRITIC_FINDING_SLA_HOURS)
    base_comment = int(REVIEW_COMMENT_DEFAULT_SLA_HOURS)

    if use_saved_profile:
        client_metadata = job.get("client_metadata")
        metadata = client_metadata if isinstance(client_metadata, dict) else {}
        saved_profile = metadata.get("sla_profile")
        saved_dict = saved_profile if isinstance(saved_profile, dict) else {}
        saved_finding = saved_dict.get("finding_sla_hours")
        saved_comment = saved_dict.get("default_comment_sla_hours")
        base_finding = _normalize_finding_sla_profile(saved_finding, default=base_finding)
        base_comment = _normalize_comment_sla_hours(saved_comment)

    resolved_finding = _normalize_finding_sla_profile(finding_sla_hours_override, default=base_finding)
    if default_comment_sla_hours is None:
        resolved_comment = base_comment
    else:
        resolved_comment = _normalize_comment_sla_hours(default_comment_sla_hours)
    return resolved_finding, resolved_comment


def _ensure_finding_due_at(
    item: Dict[str, Any],
    *,
    now_iso: str,
    reset: bool = False,
    finding_sla_hours_override: Optional[Dict[str, int]] = None,
) -> Dict[str, Any]:
    current = dict(item)
    status = str(current.get("status") or "open").strip().lower()
    if status == "resolved":
        return current
    if not reset and str(current.get("due_at") or "").strip():
        return current
    sla_hours = _finding_sla_hours(current.get("severity"), finding_sla_hours_override=finding_sla_hours_override)
    base_ts = None
    if status == "acknowledged":
        base_ts = str(current.get("acknowledged_at") or current.get("updated_at") or now_iso)
    else:
        base_ts = str(current.get("updated_at") or now_iso)
    current["due_at"] = _iso_plus_hours(base_ts, sla_hours)
    current["sla_hours"] = sla_hours
    return current


def _normalize_critic_fatal_flaws_for_job(job_id: str) -> Optional[Dict[str, Any]]:
    job = _get_job(job_id)
    if not job:
        return None
    state = job.get("state")
    if not isinstance(state, dict):
        return job
    raw_flaws = state_critic_findings(state, default_source="rules")
    if not raw_flaws:
        return job

    now_iso = _utcnow_iso()
    normalized_with_due = [_ensure_finding_due_at(item, now_iso=now_iso) for item in raw_flaws]
    existing_notes_raw = state.get("critic_notes")
    existing_notes: Dict[str, Any] = existing_notes_raw if isinstance(existing_notes_raw, dict) else {}
    existing_notes_flaws = (
        existing_notes.get("fatal_flaws") if isinstance(existing_notes.get("fatal_flaws"), list) else []
    )
    existing_state_flaws = state.get("critic_fatal_flaws") if isinstance(state.get("critic_fatal_flaws"), list) else []
    changed = normalized_with_due != existing_notes_flaws or normalized_with_due != existing_state_flaws

    if not changed:
        return job

    next_state = dict(state)
    write_state_critic_findings(
        next_state, normalized_with_due, previous_items=normalized_with_due, default_source="rules"
    )
    return _update_job(job_id, state=next_state)


def _find_critic_fatal_flaw(job: Dict[str, Any], finding_id: str) -> Optional[Dict[str, Any]]:
    state = job.get("state")
    if not isinstance(state, dict):
        return None
    flaws = state_critic_findings(state, default_source="rules")
    for item in flaws:
        if not isinstance(item, dict):
            continue
        if finding_primary_id(item) == finding_id:
            return item
    return None


def _linked_finding_severity(job: Dict[str, Any], linked_finding_id: Optional[str]) -> Optional[str]:
    token = str(linked_finding_id or "").strip()
    if not token:
        return None
    finding = _find_critic_fatal_flaw(job, token)
    if not isinstance(finding, dict):
        return None
    severity = str(finding.get("severity") or "").strip().lower()
    return severity or None


def _ensure_comment_due_at(
    comment: Dict[str, Any],
    *,
    job: Dict[str, Any],
    now_iso: str,
    reset: bool = False,
    finding_sla_hours_override: Optional[Dict[str, int]] = None,
    default_comment_sla_hours: Optional[int] = None,
) -> Dict[str, Any]:
    current = dict(comment)
    status = str(current.get("status") or "open").strip().lower()
    if status == "resolved":
        return current
    if not reset and str(current.get("due_at") or "").strip():
        if not current.get("sla_hours"):
            inferred_sla = _comment_sla_hours(
                linked_finding_severity=_linked_finding_severity(
                    job, str(current.get("linked_finding_id") or "").strip()
                ),
                finding_sla_hours_override=finding_sla_hours_override,
                default_comment_sla_hours=default_comment_sla_hours,
            )
            current["sla_hours"] = inferred_sla
        return current
    linked_finding_id = str(current.get("linked_finding_id") or "").strip() or None
    severity = _linked_finding_severity(job, linked_finding_id)
    sla_hours = _comment_sla_hours(
        linked_finding_severity=severity,
        finding_sla_hours_override=finding_sla_hours_override,
        default_comment_sla_hours=default_comment_sla_hours,
    )
    base_ts = str(current.get("updated_ts") or current.get("ts") or now_iso)
    current["sla_hours"] = sla_hours
    current["due_at"] = _iso_plus_hours(base_ts, sla_hours)
    return current


def _normalize_review_comments_for_job(job_id: str) -> Optional[Dict[str, Any]]:
    job = _get_job(job_id)
    if not job:
        return None
    raw_comments = job.get("review_comments")
    if not isinstance(raw_comments, list):
        return job
    comments = [c for c in raw_comments if isinstance(c, dict)]
    now_iso = _utcnow_iso()
    normalized_comments = [_ensure_comment_due_at(comment, job=job, now_iso=now_iso) for comment in comments]
    if normalized_comments == comments:
        return job
    return _update_job(job_id, review_comments=normalized_comments[-500:])


def _job_is_canceled(job_id: str) -> bool:
    job = _get_job(job_id)
    return bool(job and job.get("status") == "canceled")


def _dispatch_job_webhook_for_status_change(
    job_id: str,
    previous: Optional[Dict[str, Any]],
    current: Optional[Dict[str, Any]],
) -> None:
    if not current:
        return

    previous_status = (previous or {}).get("status")
    current_status = current.get("status")
    if previous_status == current_status:
        return

    event_name = STATUS_WEBHOOK_EVENTS.get(str(current_status))
    if not event_name:
        return

    webhook_url = str(current.get("webhook_url") or (previous or {}).get("webhook_url") or "").strip()
    if not webhook_url:
        return

    webhook_secret = current.get("webhook_secret") or (previous or {}).get("webhook_secret")
    public_payload = public_job_payload(current)
    from grantflow.api import app as api_app_module

    sender = getattr(api_app_module, "send_job_webhook_event", send_job_webhook_event)
    try:
        sender(
            url=webhook_url,
            secret=str(webhook_secret) if webhook_secret else None,
            event=event_name,
            job_id=job_id,
            job=public_payload,
        )
    except Exception:
        pass


def _pause_for_hitl(job_id: str, state: dict, stage: Literal["toc", "logframe"], resume_from: HITLStartAt) -> None:
    existing_checkpoint_id = str(state.get("hitl_checkpoint_id") or "").strip() or None
    if _job_is_canceled(job_id):
        if existing_checkpoint_id:
            hitl_manager.cancel(existing_checkpoint_id, "Canceled before HITL checkpoint was published")
        return
    _clear_hitl_runtime_state(state, clear_pending=False)
    state["hitl_pending"] = True
    normalize_state_contract(state)
    donor_id = state_donor_id(state, default="unknown")
    checkpoint_id = existing_checkpoint_id
    if checkpoint_id:
        checkpoint = hitl_manager.get_checkpoint(checkpoint_id)
        checkpoint_stage = str(checkpoint.get("stage") or "").strip().lower() if isinstance(checkpoint, dict) else ""
        checkpoint_status = _checkpoint_status_token(checkpoint) if isinstance(checkpoint, dict) else ""
        if not checkpoint or checkpoint_status != HITLStatus.PENDING.value or checkpoint_stage != stage:
            if isinstance(checkpoint, dict) and checkpoint_status == HITLStatus.PENDING.value and checkpoint_id:
                hitl_manager.cancel(checkpoint_id, "Superseded by new HITL checkpoint")
            checkpoint_id = None
    if not checkpoint_id:
        checkpoint_id = hitl_manager.create_checkpoint(stage, state, donor_id)
    if _job_is_canceled(job_id):
        hitl_manager.cancel(checkpoint_id, "Canceled before HITL checkpoint was published")
        return
    _set_job(
        job_id,
        {
            "status": "pending_hitl",
            "state": state,
            "checkpoint_id": checkpoint_id,
            "checkpoint_stage": stage,
            "resume_from": resume_from,
            "hitl_enabled": True,
        },
    )
    _record_job_event(
        job_id,
        "hitl_checkpoint_published",
        checkpoint_id=checkpoint_id,
        checkpoint_stage=stage,
        resume_from=resume_from,
    )
