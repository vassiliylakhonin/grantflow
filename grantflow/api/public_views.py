from __future__ import annotations

import difflib
import json
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional


def sanitize_for_public_response(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(k): sanitize_for_public_response(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [sanitize_for_public_response(item) for item in value]
    return str(value)


def public_state_snapshot(state: Any) -> Any:
    if not isinstance(state, dict):
        return sanitize_for_public_response(state)

    redacted_state = {}
    for key, value in state.items():
        if key in {"strategy", "donor_strategy"}:
            continue
        redacted_state[str(key)] = sanitize_for_public_response(value)
    return redacted_state


def public_job_payload(job: Dict[str, Any]) -> Dict[str, Any]:
    public_job: Dict[str, Any] = {}
    for key, value in job.items():
        if key in {"webhook_url", "webhook_secret", "job_events", "review_comments"}:
            continue
        if key == "state":
            public_job[key] = public_state_snapshot(value)
            continue
        public_job[str(key)] = sanitize_for_public_response(value)
    public_job["webhook_configured"] = bool(job.get("webhook_url"))
    return public_job


def public_job_comments_payload(
    job_id: str,
    job: Dict[str, Any],
    *,
    section: Optional[str] = None,
    comment_status: Optional[str] = None,
    version_id: Optional[str] = None,
) -> Dict[str, Any]:
    raw_comments = job.get("review_comments")
    comments: list[Dict[str, Any]] = []
    if isinstance(raw_comments, list):
        for item in raw_comments:
            if not isinstance(item, dict):
                continue
            comments.append(sanitize_for_public_response(item))

    if section:
        comments = [c for c in comments if str(c.get("section") or "") == section]
    if comment_status:
        comments = [c for c in comments if str(c.get("status") or "") == comment_status]
    if version_id:
        comments = [c for c in comments if str(c.get("version_id") or "") == version_id]

    return {
        "job_id": str(job_id),
        "status": str(job.get("status") or ""),
        "comment_count": len(comments),
        "comments": comments,
    }


def public_job_critic_payload(job_id: str, job: Dict[str, Any]) -> Dict[str, Any]:
    state = job.get("state")
    critic_notes = (state or {}).get("critic_notes") if isinstance(state, dict) else {}
    if not isinstance(critic_notes, dict):
        critic_notes = {}

    raw_flaws = critic_notes.get("fatal_flaws")
    fatal_flaws = [sanitize_for_public_response(item) for item in raw_flaws if isinstance(item, dict)] if isinstance(raw_flaws, list) else []

    raw_comments = job.get("review_comments")
    linked_comment_ids_by_finding: dict[str, list[str]] = {}
    if isinstance(raw_comments, list):
        for item in raw_comments:
            if not isinstance(item, dict):
                continue
            finding_id = str(item.get("linked_finding_id") or "").strip()
            comment_id = str(item.get("comment_id") or "").strip()
            if not finding_id or not comment_id:
                continue
            linked_comment_ids_by_finding.setdefault(finding_id, []).append(comment_id)
    if linked_comment_ids_by_finding:
        for flaw in fatal_flaws:
            if not isinstance(flaw, dict):
                continue
            finding_id = str(flaw.get("finding_id") or "").strip()
            if not finding_id:
                continue
            linked = linked_comment_ids_by_finding.get(finding_id) or []
            if linked:
                flaw["linked_comment_ids"] = linked

    raw_messages = critic_notes.get("fatal_flaw_messages")
    fatal_flaw_messages = [str(item) for item in raw_messages if isinstance(item, (str, int, float))] if isinstance(raw_messages, list) else []

    raw_checks = critic_notes.get("rule_checks")
    rule_checks = [sanitize_for_public_response(item) for item in raw_checks if isinstance(item, dict)] if isinstance(raw_checks, list) else []

    return {
        "job_id": str(job_id),
        "status": str(job.get("status") or ""),
        "quality_score": sanitize_for_public_response((state or {}).get("quality_score") if isinstance(state, dict) else None),
        "critic_score": sanitize_for_public_response((state or {}).get("critic_score") if isinstance(state, dict) else None),
        "engine": sanitize_for_public_response(critic_notes.get("engine")),
        "rule_score": sanitize_for_public_response(critic_notes.get("rule_score")),
        "llm_score": sanitize_for_public_response(critic_notes.get("llm_score")),
        "needs_revision": sanitize_for_public_response((state or {}).get("needs_revision") if isinstance(state, dict) else None),
        "revision_instructions": sanitize_for_public_response(critic_notes.get("revision_instructions")),
        "fatal_flaw_count": len(fatal_flaws),
        "fatal_flaws": fatal_flaws,
        "fatal_flaw_messages": fatal_flaw_messages,
        "rule_check_count": len(rule_checks),
        "rule_checks": rule_checks,
    }


def public_job_citations_payload(job_id: str, job: Dict[str, Any]) -> Dict[str, Any]:
    state = job.get("state")
    citations = []
    if isinstance(state, dict):
        raw = state.get("citations")
        if isinstance(raw, list):
            citations = [sanitize_for_public_response(item) for item in raw if isinstance(item, dict)]
    return {
        "job_id": str(job_id),
        "status": str(job.get("status") or ""),
        "citation_count": len(citations),
        "citations": citations,
    }


def _public_versions_from_state(state: Any) -> list[Dict[str, Any]]:
    if not isinstance(state, dict):
        return []
    raw = state.get("draft_versions")
    if not isinstance(raw, list):
        return []

    versions: list[Dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        version = {
            "version_id": str(item.get("version_id") or ""),
            "sequence": sanitize_for_public_response(item.get("sequence")),
            "section": sanitize_for_public_response(item.get("section")),
            "node": sanitize_for_public_response(item.get("node")),
            "iteration": sanitize_for_public_response(item.get("iteration")),
            "content": sanitize_for_public_response(item.get("content") or {}),
        }
        versions.append(version)
    return versions


def public_job_versions_payload(job_id: str, job: Dict[str, Any], section: Optional[str] = None) -> Dict[str, Any]:
    versions = _public_versions_from_state(job.get("state"))
    if section:
        versions = [v for v in versions if v.get("section") == section]
    return {
        "job_id": str(job_id),
        "status": str(job.get("status") or ""),
        "version_count": len(versions),
        "versions": versions,
    }


def public_job_diff_payload(
    job_id: str,
    job: Dict[str, Any],
    *,
    section: Optional[str] = None,
    from_version_id: Optional[str] = None,
    to_version_id: Optional[str] = None,
) -> Dict[str, Any]:
    versions = _public_versions_from_state(job.get("state"))
    if section:
        versions = [v for v in versions if v.get("section") == section]

    by_id = {str(v.get("version_id") or ""): v for v in versions if v.get("version_id")}
    selected_from = by_id.get(from_version_id or "") if from_version_id else None
    selected_to = by_id.get(to_version_id or "") if to_version_id else None

    if (from_version_id and not selected_from) or (to_version_id and not selected_to):
        return {
            "job_id": str(job_id),
            "status": str(job.get("status") or ""),
            "section": section,
            "has_diff": False,
            "error": "Requested version_id not found",
            "diff_text": "",
            "diff_lines": [],
        }

    if not selected_to and not selected_from:
        if len(versions) >= 2:
            selected_from, selected_to = versions[-2], versions[-1]
        else:
            return {
                "job_id": str(job_id),
                "status": str(job.get("status") or ""),
                "section": section,
                "has_diff": False,
                "error": "Need at least two versions to compute diff",
                "diff_text": "",
                "diff_lines": [],
            }
    elif selected_to is None and selected_from is not None:
        if len(versions) >= 1:
            selected_to = versions[-1]
        else:
            return {
                "job_id": str(job_id),
                "status": str(job.get("status") or ""),
                "section": section,
                "has_diff": False,
                "error": "Need at least one target version to compute diff",
                "diff_text": "",
                "diff_lines": [],
            }
    elif selected_from is None and selected_to is not None:
        # default to previous version before selected_to within filtered set
        idx = next((i for i, v in enumerate(versions) if v.get("version_id") == selected_to.get("version_id")), -1)
        if idx > 0:
            selected_from = versions[idx - 1]
        else:
            return {
                "job_id": str(job_id),
                "status": str(job.get("status") or ""),
                "section": section,
                "has_diff": False,
                "error": "No previous version found for requested to_version_id",
                "diff_text": "",
                "diff_lines": [],
            }

    from_content = (selected_from or {}).get("content") if selected_from else {}
    to_content = (selected_to or {}).get("content") if selected_to else {}
    from_text = json.dumps(from_content or {}, ensure_ascii=False, sort_keys=True, indent=2).splitlines()
    to_text = json.dumps(to_content or {}, ensure_ascii=False, sort_keys=True, indent=2).splitlines()
    diff_lines = list(
        difflib.unified_diff(
            from_text,
            to_text,
            fromfile=str((selected_from or {}).get("version_id") or "from"),
            tofile=str((selected_to or {}).get("version_id") or "to"),
            lineterm="",
        )
    )
    return {
        "job_id": str(job_id),
        "status": str(job.get("status") or ""),
        "section": section or (selected_to or {}).get("section"),
        "from_version_id": (selected_from or {}).get("version_id"),
        "to_version_id": (selected_to or {}).get("version_id"),
        "has_diff": True,
        "diff_text": "\n".join(diff_lines),
        "diff_lines": diff_lines,
    }


def public_job_events_payload(job_id: str, job: Dict[str, Any]) -> Dict[str, Any]:
    raw_events = job.get("job_events")
    events: list[Dict[str, Any]] = []
    if isinstance(raw_events, list):
        for item in raw_events:
            if not isinstance(item, dict):
                continue
            events.append(sanitize_for_public_response(item))
    return {
        "job_id": str(job_id),
        "status": str(job.get("status") or ""),
        "event_count": len(events),
        "events": events,
    }


def _parse_event_ts(value: Any) -> Optional[datetime]:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def public_job_metrics_payload(job_id: str, job: Dict[str, Any]) -> Dict[str, Any]:
    raw_events = job.get("job_events")
    events: list[Dict[str, Any]] = []
    if isinstance(raw_events, list):
        events = [sanitize_for_public_response(item) for item in raw_events if isinstance(item, dict)]

    status_events = [e for e in events if e.get("type") == "status_changed"]
    pause_events = [e for e in status_events if e.get("to_status") == "pending_hitl"]
    resume_events = [e for e in events if e.get("type") == "resume_requested"]
    terminal_statuses = {"done", "error", "canceled"}

    created_event = next((e for e in status_events if e.get("to_status") == "accepted"), None)
    started_event = next((e for e in status_events if e.get("to_status") == "running"), None)
    first_pending_event = next((e for e in status_events if e.get("to_status") == "pending_hitl"), None)
    terminal_event = next((e for e in reversed(status_events) if e.get("to_status") in terminal_statuses), None)

    created_at = _parse_event_ts((created_event or {}).get("ts"))
    first_pending_at = _parse_event_ts((first_pending_event or {}).get("ts"))
    terminal_at = _parse_event_ts((terminal_event or {}).get("ts"))

    # Sum durations spent in pending_hitl until the next status transition.
    total_pending_s = 0.0
    pending_started_at: Optional[datetime] = None
    for e in status_events:
        ts = _parse_event_ts(e.get("ts"))
        if ts is None:
            continue
        to_status = e.get("to_status")
        if to_status == "pending_hitl":
            pending_started_at = ts
            continue
        if pending_started_at is not None:
            total_pending_s += max(0.0, (ts - pending_started_at).total_seconds())
            pending_started_at = None
    # If still pending at the end, leave the open interval uncounted (deterministic snapshot metric).

    first_draft_marker = first_pending_at or terminal_at
    time_to_first_draft = (
        max(0.0, (first_draft_marker - created_at).total_seconds())
        if created_at is not None and first_draft_marker is not None
        else None
    )
    time_to_terminal = (
        max(0.0, (terminal_at - created_at).total_seconds())
        if created_at is not None and terminal_at is not None
        else None
    )

    return {
        "job_id": str(job_id),
        "status": str(job.get("status") or ""),
        "event_count": len(events),
        "status_change_count": len(status_events),
        "pause_count": len(pause_events),
        "resume_count": len(resume_events),
        "created_at": (created_event or {}).get("ts"),
        "started_at": (started_event or {}).get("ts"),
        "first_pending_hitl_at": (first_pending_event or {}).get("ts"),
        "terminal_at": (terminal_event or {}).get("ts"),
        "terminal_status": (terminal_event or {}).get("to_status"),
        "time_to_first_draft_seconds": round(time_to_first_draft, 3) if time_to_first_draft is not None else None,
        "time_to_terminal_seconds": round(time_to_terminal, 3) if time_to_terminal is not None else None,
        "time_in_pending_hitl_seconds": round(total_pending_s, 3),
    }


def public_portfolio_metrics_payload(
    jobs_by_id: Dict[str, Dict[str, Any]],
    *,
    donor_id: Optional[str] = None,
    status: Optional[str] = None,
    hitl_enabled: Optional[bool] = None,
) -> Dict[str, Any]:
    filtered: list[tuple[str, Dict[str, Any]]] = []
    for job_id, job in jobs_by_id.items():
        if not isinstance(job, dict):
            continue
        job_status = str(job.get("status") or "")
        state = job.get("state") if isinstance(job.get("state"), dict) else {}
        job_donor = str((state or {}).get("donor_id") or (state or {}).get("donor") or "")
        job_hitl = bool(job.get("hitl_enabled"))

        if donor_id and job_donor != donor_id:
            continue
        if status and job_status != status:
            continue
        if hitl_enabled is not None and job_hitl != hitl_enabled:
            continue
        filtered.append((str(job_id), job))

    status_counts: Dict[str, int] = {}
    donor_counts: Dict[str, int] = {}
    total_pause_count = 0
    total_resume_count = 0
    metrics_rows: list[Dict[str, Any]] = []

    for job_id, job in filtered:
        job_status = str(job.get("status") or "")
        status_counts[job_status] = status_counts.get(job_status, 0) + 1
        state = job.get("state") if isinstance(job.get("state"), dict) else {}
        job_donor = str((state or {}).get("donor_id") or (state or {}).get("donor") or "unknown")
        donor_counts[job_donor] = donor_counts.get(job_donor, 0) + 1

        m = public_job_metrics_payload(job_id, job)
        metrics_rows.append(m)
        total_pause_count += int(m.get("pause_count") or 0)
        total_resume_count += int(m.get("resume_count") or 0)

    def _avg(key: str) -> Optional[float]:
        values = [float(m[key]) for m in metrics_rows if isinstance(m.get(key), (int, float))]
        if not values:
            return None
        return round(sum(values) / len(values), 3)

    terminal_statuses = {"done", "error", "canceled"}
    terminal_rows = [m for m in metrics_rows if str(m.get("terminal_status") or "") in terminal_statuses]

    return {
        "job_count": len(filtered),
        "filters": {
            "donor_id": donor_id,
            "status": status,
            "hitl_enabled": hitl_enabled,
        },
        "status_counts": status_counts,
        "donor_counts": donor_counts,
        "terminal_job_count": len(terminal_rows),
        "hitl_job_count": sum(1 for _, job in filtered if bool(job.get("hitl_enabled"))),
        "total_pause_count": total_pause_count,
        "total_resume_count": total_resume_count,
        "avg_time_to_first_draft_seconds": _avg("time_to_first_draft_seconds"),
        "avg_time_to_terminal_seconds": _avg("time_to_terminal_seconds"),
        "avg_time_in_pending_hitl_seconds": _avg("time_in_pending_hitl_seconds"),
    }


def public_checkpoint_payload(checkpoint: Dict[str, Any]) -> Dict[str, Any]:
    public_checkpoint: Dict[str, Any] = {}
    for key, value in checkpoint.items():
        if key == "state_snapshot":
            continue
        public_checkpoint[str(key)] = sanitize_for_public_response(value)
    public_checkpoint["has_state_snapshot"] = "state_snapshot" in checkpoint
    return public_checkpoint
