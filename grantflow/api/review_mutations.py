from __future__ import annotations

import uuid
from typing import Any, Dict, Optional

from fastapi import HTTPException

from grantflow.api import app as api_app_module
from grantflow.api.constants import CRITIC_FINDING_STATUSES
from grantflow.api.public_views import REVIEW_WORKFLOW_OVERDUE_DEFAULT_HOURS, public_job_review_workflow_sla_payload
from grantflow.swarm.findings import canonicalize_findings, finding_primary_id, state_critic_findings, write_state_critic_findings


def _recompute_review_workflow_sla(
    job_id: str,
    *,
    actor: Optional[str] = None,
    finding_sla_hours_override: Optional[Dict[str, Any]] = None,
    default_comment_sla_hours: Optional[Any] = None,
    use_saved_profile: bool = False,
) -> Dict[str, Any]:
    job = api_app_module._normalize_critic_fatal_flaws_for_job(job_id) or api_app_module._get_job(job_id)
    job = api_app_module._normalize_review_comments_for_job(job_id) or job
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    now_iso = api_app_module._utcnow_iso()
    actor_value = str(actor or "").strip() or "api_user"
    applied_finding_sla_hours, applied_default_comment_sla_hours = api_app_module._resolve_sla_profile_for_recompute(
        job=job,
        finding_sla_hours_override=finding_sla_hours_override,
        default_comment_sla_hours=default_comment_sla_hours,
        use_saved_profile=bool(use_saved_profile),
    )

    state = job.get("state")
    state_dict = state if isinstance(state, dict) else {}
    flaws = state_critic_findings(state_dict, default_source="rules")

    finding_checked_count = len(flaws)
    finding_updated_count = 0
    next_flaws: list[Dict[str, Any]] = []
    for item in flaws:
        current = dict(item)
        recomputed = api_app_module._ensure_finding_due_at(
            current,
            now_iso=now_iso,
            reset=True,
            finding_sla_hours_override=applied_finding_sla_hours,
        )
        if recomputed != current:
            finding_updated_count += 1
        next_flaws.append(recomputed)

    next_state = state_dict
    state_changed = False
    existing_notes_raw = state_dict.get("critic_notes")
    existing_notes: Dict[str, Any] = existing_notes_raw if isinstance(existing_notes_raw, dict) else {}
    existing_notes_flaws = (
        existing_notes.get("fatal_flaws") if isinstance(existing_notes.get("fatal_flaws"), list) else []
    )
    existing_state_flaws = (
        state_dict.get("critic_fatal_flaws") if isinstance(state_dict.get("critic_fatal_flaws"), list) else []
    )
    if isinstance(state, dict) and (next_flaws != existing_notes_flaws or next_flaws != existing_state_flaws):
        next_state = dict(state_dict)
        write_state_critic_findings(next_state, next_flaws, previous_items=next_flaws, default_source="rules")
        state_changed = True

    working_job = dict(job)
    if state_changed:
        working_job["state"] = next_state

    raw_comments = job.get("review_comments")
    comments = [c for c in raw_comments if isinstance(c, dict)] if isinstance(raw_comments, list) else []
    comment_checked_count = len(comments)
    comment_updated_count = 0
    next_comments: list[Dict[str, Any]] = []
    for comment in comments:
        current = dict(comment)
        recomputed = api_app_module._ensure_comment_due_at(
            current,
            job=working_job,
            now_iso=now_iso,
            reset=True,
            finding_sla_hours_override=applied_finding_sla_hours,
            default_comment_sla_hours=applied_default_comment_sla_hours,
        )
        if recomputed != current:
            comment_updated_count += 1
        next_comments.append(recomputed)

    update_payload: Dict[str, Any] = {}
    if state_changed:
        update_payload["state"] = next_state
    if next_comments != comments:
        update_payload["review_comments"] = next_comments[-500:]

    client_metadata = job.get("client_metadata")
    metadata = dict(client_metadata) if isinstance(client_metadata, dict) else {}
    sla_profile = {
        "finding_sla_hours": dict(applied_finding_sla_hours),
        "default_comment_sla_hours": int(applied_default_comment_sla_hours),
        "updated_at": now_iso,
        "updated_by": actor_value,
    }
    if metadata.get("sla_profile") != sla_profile:
        metadata["sla_profile"] = sla_profile
        update_payload["client_metadata"] = metadata

    if update_payload:
        job = api_app_module._update_job(job_id, **update_payload) or api_app_module._get_job(job_id) or job

    total_updated_count = finding_updated_count + comment_updated_count
    api_app_module._record_job_event(
        job_id,
        "review_workflow_sla_recomputed",
        actor=actor_value,
        finding_checked_count=finding_checked_count,
        comment_checked_count=comment_checked_count,
        finding_updated_count=finding_updated_count,
        comment_updated_count=comment_updated_count,
        total_updated_count=total_updated_count,
        use_saved_profile=bool(use_saved_profile),
        applied_finding_sla_hours=applied_finding_sla_hours,
        applied_default_comment_sla_hours=applied_default_comment_sla_hours,
    )

    return {
        "job_id": str(job_id),
        "status": str((job or {}).get("status") or ""),
        "actor": actor_value,
        "recomputed_at": now_iso,
        "use_saved_profile": bool(use_saved_profile),
        "applied_finding_sla_hours": applied_finding_sla_hours,
        "applied_default_comment_sla_hours": applied_default_comment_sla_hours,
        "finding_checked_count": finding_checked_count,
        "comment_checked_count": comment_checked_count,
        "finding_updated_count": finding_updated_count,
        "comment_updated_count": comment_updated_count,
        "total_updated_count": total_updated_count,
        "sla": public_job_review_workflow_sla_payload(
            job_id,
            job,
            overdue_after_hours=REVIEW_WORKFLOW_OVERDUE_DEFAULT_HOURS,
        ),
    }


def _set_critic_fatal_flaw_status(
    job_id: str,
    *,
    finding_id: str,
    next_status: str,
    actor: Optional[str] = None,
    dry_run: bool = False,
    if_match_status: Optional[str] = None,
    request_id: Optional[str] = None,
) -> Dict[str, Any]:
    if next_status not in CRITIC_FINDING_STATUSES:
        raise HTTPException(status_code=400, detail="Unsupported critic finding status")
    expected_status = str(if_match_status or "").strip().lower() or None
    if expected_status and expected_status not in CRITIC_FINDING_STATUSES:
        raise HTTPException(status_code=400, detail="Unsupported if_match_status")
    request_id_token = api_app_module._normalize_request_id(request_id)

    job = api_app_module._normalize_critic_fatal_flaws_for_job(job_id) or api_app_module._get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    idempotency_fingerprint = api_app_module._idempotency_fingerprint(
        {
            "op": "critic_finding_status",
            "job_id": str(job_id),
            "finding_id": str(finding_id),
            "next_status": str(next_status),
            "dry_run": bool(dry_run),
            "if_match_status": expected_status,
        }
    )
    replay = api_app_module._idempotency_replay_response(
        job,
        scope="critic_finding_status",
        request_id=request_id_token,
        fingerprint=idempotency_fingerprint,
    )
    if replay is not None:
        return replay
    state = job.get("state")
    if not isinstance(state, dict):
        raise HTTPException(status_code=404, detail="Critic findings not found")
    critic_notes = state.get("critic_notes")
    if not isinstance(critic_notes, dict):
        raise HTTPException(status_code=404, detail="Critic findings not found")

    flaws = state_critic_findings(state, default_source="rules")
    if not flaws:
        raise HTTPException(status_code=404, detail="Critic findings not found")

    changed = False
    updated_finding: Optional[Dict[str, Any]] = None
    next_flaws: list[Dict[str, Any]] = []
    now = api_app_module._utcnow_iso()
    actor_value = str(actor or "").strip() or "api_user"
    for item in flaws:
        current = dict(item)
        current_finding_id = finding_primary_id(current)
        if current_finding_id != finding_id:
            next_flaws.append(current)
            continue
        current_status = str(current.get("status") or "open").strip().lower() or "open"
        if expected_status and current_status != expected_status:
            raise HTTPException(
                status_code=409,
                detail={
                    "reason": "finding_status_conflict",
                    "message": "Finding status changed since last read; refresh and retry.",
                    "finding_id": current_finding_id,
                    "if_match_status": expected_status,
                    "current_status": current_status,
                },
            )
        current, finding_changed = _apply_critic_finding_status_transition(
            current,
            next_status=next_status,
            now=now,
            actor_value=actor_value,
            state=state,
        )
        if finding_changed:
            changed = True
        updated_finding = current
        next_flaws.append(current)

    if updated_finding is None:
        raise HTTPException(status_code=404, detail="Critic finding not found")

    if changed and not dry_run:
        next_state = dict(state)
        write_state_critic_findings(next_state, next_flaws, previous_items=next_flaws, default_source="rules")
        api_app_module._update_job(job_id, state=next_state)
        api_app_module._record_job_event(
            job_id,
            "critic_finding_status_changed",
            finding_id=str(updated_finding.get("id") or finding_id),
            status=next_status,
            section=updated_finding.get("section"),
            severity=updated_finding.get("severity"),
            actor=actor_value,
            request_id=request_id_token,
        )

    response = dict(updated_finding)
    response["dry_run"] = bool(dry_run)
    response["persisted"] = not bool(dry_run)
    response["changed"] = bool(changed)
    if expected_status:
        response["if_match_status"] = expected_status
    if request_id_token:
        response["request_id"] = request_id_token
    api_app_module._store_idempotency_response(
        job_id,
        scope="critic_finding_status",
        request_id=request_id_token,
        fingerprint=idempotency_fingerprint,
        response=response,
        persisted=not bool(dry_run),
    )
    return response


def _apply_critic_finding_status_transition(
    item: Dict[str, Any],
    *,
    next_status: str,
    now: str,
    actor_value: str,
    state: Optional[Dict[str, Any]] = None,
) -> tuple[Dict[str, Any], bool]:
    current = dict(item)
    current_finding_id = finding_primary_id(current)
    if current_finding_id:
        current["id"] = current_finding_id
        current["finding_id"] = current_finding_id
    current = api_app_module._ensure_finding_due_at(current, now_iso=now)

    current_status = str(current.get("status") or "open")
    if current_status == next_status:
        normalized = canonicalize_findings(
            [current], state=state, previous_items=[current], default_source="rules", dedupe=False
        )
        if normalized:
            current = dict(normalized[0])
        return current, False

    current["status"] = next_status
    current["updated_at"] = now
    current["updated_by"] = actor_value
    if next_status == "acknowledged":
        current["acknowledged_at"] = current.get("acknowledged_at") or now
        current["acknowledged_by"] = actor_value
        current.pop("resolved_at", None)
        current.pop("resolved_by", None)
        current = api_app_module._ensure_finding_due_at(current, now_iso=now)
    elif next_status == "resolved":
        current["resolved_at"] = now
        current["resolved_by"] = actor_value
        if not current.get("acknowledged_at"):
            current["acknowledged_at"] = now
        if not current.get("acknowledged_by"):
            current["acknowledged_by"] = actor_value
    elif next_status == "open":
        current.pop("acknowledged_at", None)
        current.pop("acknowledged_by", None)
        current.pop("resolved_at", None)
        current.pop("resolved_by", None)
        current = api_app_module._ensure_finding_due_at(current, now_iso=now, reset=True)
    normalized = canonicalize_findings(
        [current], state=state, previous_items=[current], default_source="rules", dedupe=False
    )
    if normalized:
        current = dict(normalized[0])
    return current, True


def _set_critic_fatal_flaws_status_bulk(
    job_id: str,
    *,
    next_status: str,
    actor: Optional[str] = None,
    dry_run: bool = False,
    request_id: Optional[str] = None,
    if_match_status: Optional[str] = None,
    apply_to_all: bool = False,
    finding_status: Optional[str] = None,
    severity: Optional[str] = None,
    section: Optional[str] = None,
    finding_ids: Optional[list[str]] = None,
) -> Dict[str, Any]:
    if next_status not in CRITIC_FINDING_STATUSES:
        raise HTTPException(status_code=400, detail="Unsupported critic finding status")

    finding_status_filter = str(finding_status or "").strip().lower() or None
    if finding_status_filter and finding_status_filter not in CRITIC_FINDING_STATUSES:
        raise HTTPException(status_code=400, detail="Unsupported finding_status filter")
    expected_status = str(if_match_status or "").strip().lower() or None
    if expected_status and expected_status not in CRITIC_FINDING_STATUSES:
        raise HTTPException(status_code=400, detail="Unsupported if_match_status")
    if expected_status and finding_status_filter and expected_status != finding_status_filter:
        raise HTTPException(
            status_code=400, detail="if_match_status must match finding_status filter when both provided"
        )
    severity_filter = str(severity or "").strip().lower() or None
    if severity_filter and severity_filter not in {"high", "medium", "low"}:
        raise HTTPException(status_code=400, detail="Unsupported severity filter")
    section_filter = str(section or "").strip().lower() or None
    if section_filter and section_filter not in {"toc", "logframe", "general"}:
        raise HTTPException(status_code=400, detail="Unsupported section filter")

    requested_finding_ids_raw = finding_ids if isinstance(finding_ids, list) else []
    requested_finding_ids: list[str] = []
    for item in requested_finding_ids_raw:
        token = str(item or "").strip()
        if not token:
            continue
        if token not in requested_finding_ids:
            requested_finding_ids.append(token)
    requested_finding_ids_set = set(requested_finding_ids)

    has_selector = bool(requested_finding_ids or finding_status_filter or severity_filter or section_filter)
    if not has_selector and not apply_to_all:
        raise HTTPException(status_code=400, detail="Provide at least one selector or set apply_to_all=true")
    request_id_token = api_app_module._normalize_request_id(request_id)

    job = api_app_module._normalize_critic_fatal_flaws_for_job(job_id) or api_app_module._get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    idempotency_fingerprint = api_app_module._idempotency_fingerprint(
        {
            "op": "critic_findings_bulk_status",
            "job_id": str(job_id),
            "next_status": str(next_status),
            "dry_run": bool(dry_run),
            "request_selectors": {
                "apply_to_all": bool(apply_to_all),
                "if_match_status": expected_status,
                "finding_status": finding_status_filter,
                "severity": severity_filter,
                "section": section_filter,
                "finding_ids": requested_finding_ids,
            },
        }
    )
    replay = api_app_module._idempotency_replay_response(
        job,
        scope="critic_findings_bulk_status",
        request_id=request_id_token,
        fingerprint=idempotency_fingerprint,
    )
    if replay is not None:
        return replay
    state = job.get("state")
    if not isinstance(state, dict):
        raise HTTPException(status_code=404, detail="Critic findings not found")
    critic_notes = state.get("critic_notes")
    if not isinstance(critic_notes, dict):
        raise HTTPException(status_code=404, detail="Critic findings not found")

    flaws = state_critic_findings(state, default_source="rules")
    if not flaws:
        raise HTTPException(status_code=404, detail="Critic findings not found")

    available_ids = {finding_primary_id(item) for item in flaws if finding_primary_id(item)}
    not_found_finding_ids = [item for item in requested_finding_ids if item not in available_ids]

    now = api_app_module._utcnow_iso()
    actor_value = str(actor or "").strip() or "api_user"
    batch_id = str(uuid.uuid4())

    changed = False
    changed_items: list[Dict[str, Any]] = []
    matched_items: list[Dict[str, Any]] = []
    conflict_items: list[Dict[str, Any]] = []
    next_flaws: list[Dict[str, Any]] = []

    for item in flaws:
        current = dict(item)
        current_finding_id = finding_primary_id(current)
        current_status = str(current.get("status") or "open").strip().lower()
        current_severity = str(current.get("severity") or "").strip().lower()
        current_section = str(current.get("section") or "").strip().lower()
        if current_finding_id:
            current["id"] = current_finding_id
            current["finding_id"] = current_finding_id

        match = bool(apply_to_all)
        if not apply_to_all:
            match = True
            if requested_finding_ids_set and current_finding_id not in requested_finding_ids_set:
                match = False
            if finding_status_filter and current_status != finding_status_filter:
                match = False
            if severity_filter and current_severity != severity_filter:
                match = False
            if section_filter and current_section != section_filter:
                match = False
        if not match:
            next_flaws.append(current)
            continue
        if expected_status and current_status != expected_status:
            conflict_items.append(
                {
                    "finding_id": current_finding_id,
                    "current_status": current_status,
                    "expected_status": expected_status,
                }
            )
            next_flaws.append(current)
            continue

        updated, finding_changed = _apply_critic_finding_status_transition(
            current,
            next_status=next_status,
            now=now,
            actor_value=actor_value,
            state=state,
        )
        matched_items.append(updated)
        next_flaws.append(updated)
        if finding_changed:
            changed = True
            changed_items.append(updated)

    if conflict_items:
        raise HTTPException(
            status_code=409,
            detail={
                "reason": "finding_status_conflict",
                "message": "One or more findings changed status since last read; refresh and retry.",
                "if_match_status": expected_status,
                "conflict_count": len(conflict_items),
                "conflicts": conflict_items,
            },
        )

    if changed and not dry_run:
        next_state = dict(state)
        write_state_critic_findings(next_state, next_flaws, previous_items=next_flaws, default_source="rules")
        api_app_module._update_job(job_id, state=next_state)
        for updated in changed_items:
            api_app_module._record_job_event(
                job_id,
                "critic_finding_status_changed",
                finding_id=str(updated.get("id") or ""),
                status=next_status,
                section=updated.get("section"),
                severity=updated.get("severity"),
                actor=actor_value,
                batch_id=batch_id,
                request_id=request_id_token,
            )

    matched_count = len(matched_items)
    changed_count = len(changed_items)
    response = {
        "job_id": str(job_id),
        "status": str((job or {}).get("status") or ""),
        "requested_status": next_status,
        "actor": actor_value,
        "dry_run": bool(dry_run),
        "persisted": not bool(dry_run),
        "matched_count": matched_count,
        "changed_count": changed_count,
        "unchanged_count": max(0, matched_count - changed_count),
        "not_found_finding_ids": not_found_finding_ids,
        "filters": {
            "apply_to_all": bool(apply_to_all),
            "if_match_status": expected_status,
            "finding_status": finding_status_filter,
            "severity": severity_filter,
            "section": section_filter,
            "finding_ids": requested_finding_ids or None,
        },
        "updated_findings": matched_items,
    }
    if request_id_token:
        response["request_id"] = request_id_token
    api_app_module._store_idempotency_response(
        job_id,
        scope="critic_findings_bulk_status",
        request_id=request_id_token,
        fingerprint=idempotency_fingerprint,
        response=response,
        persisted=not bool(dry_run),
    )
    return response


def _append_review_comment(
    job_id: str,
    *,
    section: str,
    message: str,
    author: Optional[str] = None,
    version_id: Optional[str] = None,
    linked_finding_id: Optional[str] = None,
    linked_finding_severity: Optional[str] = None,
    request_id: Optional[str] = None,
) -> Dict[str, Any]:
    job = api_app_module._get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    request_id_token = api_app_module._normalize_request_id(request_id)
    idempotency_fingerprint = api_app_module._idempotency_fingerprint(
        {
            "op": "review_comment_add",
            "job_id": str(job_id),
            "section": section,
            "message": message,
            "author": author,
            "version_id": version_id,
            "linked_finding_id": linked_finding_id,
        }
    )
    replay = api_app_module._idempotency_replay_response(
        job,
        scope="review_comment_add",
        request_id=request_id_token,
        fingerprint=idempotency_fingerprint,
    )
    if replay is not None:
        return replay

    existing = job.get("review_comments")
    comments = [c for c in existing if isinstance(c, dict)] if isinstance(existing, list) else []
    comment: Dict[str, Any] = {
        "comment_id": str(uuid.uuid4()),
        "ts": api_app_module._utcnow_iso(),
        "section": section,
        "status": "open",
        "message": message,
    }
    comment["sla_hours"] = api_app_module._comment_sla_hours(linked_finding_severity=linked_finding_severity)
    comment["due_at"] = api_app_module._iso_plus_hours(comment["ts"], int(comment["sla_hours"]))
    if author:
        comment["author"] = author
    if version_id:
        comment["version_id"] = version_id
    if linked_finding_id:
        comment["linked_finding_id"] = linked_finding_id
    if request_id_token:
        comment["request_id"] = request_id_token
    comments.append(comment)
    api_app_module._update_job(job_id, review_comments=comments[-500:])
    api_app_module._record_job_event(
        job_id,
        "review_comment_added",
        comment_id=comment["comment_id"],
        section=section,
        version_id=version_id,
        author=author,
        linked_finding_id=linked_finding_id,
        request_id=request_id_token,
    )
    api_app_module._store_idempotency_response(
        job_id,
        scope="review_comment_add",
        request_id=request_id_token,
        fingerprint=idempotency_fingerprint,
        response=comment,
        persisted=True,
    )
    return comment


def _set_review_comment_status(
    job_id: str,
    *,
    comment_id: str,
    next_status: str,
    actor: Optional[str] = None,
    request_id: Optional[str] = None,
) -> Dict[str, Any]:
    job = api_app_module._get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    request_id_token = api_app_module._normalize_request_id(request_id)
    idempotency_fingerprint = api_app_module._idempotency_fingerprint(
        {
            "op": "review_comment_status",
            "job_id": str(job_id),
            "comment_id": str(comment_id),
            "next_status": str(next_status),
        }
    )
    replay = api_app_module._idempotency_replay_response(
        job,
        scope="review_comment_status",
        request_id=request_id_token,
        fingerprint=idempotency_fingerprint,
    )
    if replay is not None:
        return replay

    existing = job.get("review_comments")
    comments = [c for c in existing if isinstance(c, dict)] if isinstance(existing, list) else []
    updated_comment: Optional[Dict[str, Any]] = None
    changed = False
    status_transitioned = False
    now_iso = api_app_module._utcnow_iso()
    actor_value = str(actor or "").strip() or "api_user"

    next_comments: list[Dict[str, Any]] = []
    for item in comments:
        cid = str(item.get("comment_id") or "")
        if cid != comment_id:
            next_comments.append(item)
            continue

        current = dict(item)
        current_status = str(current.get("status") or "open")
        current_with_due = api_app_module._ensure_comment_due_at(current, job=job, now_iso=now_iso)
        if current_with_due != current:
            changed = True
        current = current_with_due
        if current_status != next_status:
            current["status"] = next_status
            current["updated_ts"] = now_iso
            current["updated_by"] = actor_value
            if next_status == "resolved":
                current["resolved_at"] = current["updated_ts"]
            elif "resolved_at" in current:
                current.pop("resolved_at", None)
            if next_status == "open":
                current = api_app_module._ensure_comment_due_at(current, job=job, now_iso=now_iso, reset=True)
            changed = True
            status_transitioned = True
        updated_comment = current
        next_comments.append(current)

    if updated_comment is None:
        raise HTTPException(status_code=404, detail="Comment not found")

    if changed:
        api_app_module._update_job(job_id, review_comments=next_comments[-500:])
    if status_transitioned:
        api_app_module._record_job_event(
            job_id,
            "review_comment_status_changed",
            comment_id=comment_id,
            status=next_status,
            section=updated_comment.get("section"),
            actor=actor_value,
            request_id=request_id_token,
        )
    response = dict(updated_comment)
    if request_id_token:
        response["request_id"] = request_id_token
    response["persisted"] = True
    response["changed"] = bool(status_transitioned)
    api_app_module._store_idempotency_response(
        job_id,
        scope="review_comment_status",
        request_id=request_id_token,
        fingerprint=idempotency_fingerprint,
        response=response,
        persisted=True,
    )
    return response
