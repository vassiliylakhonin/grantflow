from __future__ import annotations

import difflib
import json
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, Optional, cast

from grantflow.api.csv_utils import csv_text_from_mapping
from grantflow.swarm.citations import citation_traceability_status
from grantflow.swarm.findings import finding_primary_id, normalize_findings

PORTFOLIO_QUALITY_SIGNAL_WEIGHTS: dict[str, int] = {
    "high_severity_findings_total": 5,
    "medium_severity_findings_total": 3,
    "open_findings_total": 4,
    "needs_revision_job_count": 4,
    "rag_low_confidence_citation_count": 3,
    "traceability_gap_citation_count": 2,
    "low_confidence_citation_count": 1,
}
PORTFOLIO_QUALITY_HIGH_PRIORITY_SIGNALS = {
    "high_severity_findings_total",
    "open_findings_total",
    "needs_revision_job_count",
    "rag_low_confidence_citation_count",
    "traceability_gap_citation_count",
}
PORTFOLIO_WARNING_LEVELS = {"high", "medium", "low", "none"}
PORTFOLIO_WARNING_LEVEL_ORDER = ("high", "medium", "low", "none")
GROUNDING_RISK_LEVEL_ORDER = ("high", "medium", "low", "unknown")
GROUNDING_RISK_LEVELS = set(GROUNDING_RISK_LEVEL_ORDER)
FINDING_STATUS_FILTER_VALUES = {"open", "acknowledged", "resolved"}
FINDING_SEVERITY_FILTER_VALUES = {"high", "medium", "low"}
REVIEW_WORKFLOW_EVENT_TYPES = {
    "critic_finding_status_changed",
    "review_comment_added",
    "review_comment_status_changed",
}
REVIEW_WORKFLOW_STATE_FILTER_VALUES = {"pending", "overdue"}
REVIEW_WORKFLOW_OVERDUE_DEFAULT_HOURS = 48
GROUNDING_FALLBACK_HIGH_THRESHOLD = 0.8
GROUNDING_FALLBACK_MEDIUM_THRESHOLD = 0.5


def _job_warning_level(job: Dict[str, Any]) -> str:
    preflight = job.get("generate_preflight")
    if not isinstance(preflight, dict):
        state = job.get("state")
        state_dict = state if isinstance(state, dict) else {}
        preflight = state_dict.get("generate_preflight")
    preflight_dict = preflight if isinstance(preflight, dict) else {}
    raw = str(preflight_dict.get("warning_level") or preflight_dict.get("risk_level") or "").strip().lower()
    if raw in PORTFOLIO_WARNING_LEVELS:
        return raw
    return "none"


def _normalize_warning_level_filter(warning_level: Optional[str]) -> Optional[str]:
    if warning_level is None:
        return None
    token = str(warning_level or "").strip().lower()
    if not token:
        return None
    return token


def _normalize_grounding_risk_filter(grounding_risk_level: Optional[str]) -> Optional[str]:
    if grounding_risk_level is None:
        return None
    token = str(grounding_risk_level or "").strip().lower()
    if not token:
        return None
    if token not in GROUNDING_RISK_LEVELS:
        return token
    return token


def _normalize_finding_status_filter(finding_status: Optional[str]) -> Optional[str]:
    if finding_status is None:
        return None
    token = str(finding_status or "").strip().lower()
    if not token:
        return None
    if token not in FINDING_STATUS_FILTER_VALUES:
        return token
    return token


def _normalize_finding_severity_filter(finding_severity: Optional[str]) -> Optional[str]:
    if finding_severity is None:
        return None
    token = str(finding_severity or "").strip().lower()
    if not token:
        return None
    if token not in FINDING_SEVERITY_FILTER_VALUES:
        return token
    return token


def _normalize_review_workflow_state_filter(workflow_state: Optional[str]) -> Optional[str]:
    if workflow_state is None:
        return None
    token = str(workflow_state or "").strip().lower()
    if not token:
        return None
    if token not in REVIEW_WORKFLOW_STATE_FILTER_VALUES:
        return token
    return token


def _warning_level_breakdown(
    warning_level_counts: Dict[str, int], total_jobs: int
) -> tuple[Dict[str, int], Dict[str, Optional[float]]]:
    normalized_counts: Dict[str, int] = {}
    normalized_rates: Dict[str, Optional[float]] = {}
    for level in PORTFOLIO_WARNING_LEVEL_ORDER:
        count = int(warning_level_counts.get(level) or 0)
        normalized_counts[level] = count
        normalized_rates[level] = round(count / total_jobs, 4) if total_jobs else None
    return normalized_counts, normalized_rates


def _grounding_risk_breakdown(
    grounding_risk_counts: Dict[str, int], total_jobs: int
) -> tuple[Dict[str, int], Dict[str, Optional[float]]]:
    normalized_counts: Dict[str, int] = {}
    normalized_rates: Dict[str, Optional[float]] = {}
    for level in GROUNDING_RISK_LEVEL_ORDER:
        count = int(grounding_risk_counts.get(level) or 0)
        normalized_counts[level] = count
        normalized_rates[level] = round(count / total_jobs, 4) if total_jobs else None
    return normalized_counts, normalized_rates


def _grounding_risk_level(*, fallback_count: int, citation_count: int) -> str:
    if citation_count <= 0:
        return "unknown"
    rate = fallback_count / citation_count
    if rate >= GROUNDING_FALLBACK_HIGH_THRESHOLD:
        return "high"
    if rate >= GROUNDING_FALLBACK_MEDIUM_THRESHOLD:
        return "medium"
    return "low"


def _job_grounding_risk_level(job: Dict[str, Any]) -> str:
    state = job.get("state")
    state_dict = state if isinstance(state, dict) else {}
    citations = state_dict.get("citations")
    citations_list = citations if isinstance(citations, list) else []
    citation_count = 0
    fallback_count = 0
    for item in citations_list:
        if not isinstance(item, dict):
            continue
        citation_count += 1
        if str(item.get("citation_type") or "").strip() == "fallback_namespace":
            fallback_count += 1
    return _grounding_risk_level(fallback_count=fallback_count, citation_count=citation_count)


def _job_critic_findings(job: Dict[str, Any]) -> list[Dict[str, Any]]:
    state = job.get("state")
    state_dict = state if isinstance(state, dict) else {}
    critic_notes = state_dict.get("critic_notes")
    critic_notes_dict = critic_notes if isinstance(critic_notes, dict) else {}
    raw_flaws = critic_notes_dict.get("fatal_flaws")
    if not isinstance(raw_flaws, list):
        return []
    return normalize_findings(raw_flaws, default_source="rules")


def _job_matches_finding_filters(
    job: Dict[str, Any],
    *,
    finding_status_filter: Optional[str],
    finding_severity_filter: Optional[str],
) -> bool:
    if finding_status_filter is None and finding_severity_filter is None:
        return True
    findings = _job_critic_findings(job)
    if not findings:
        return False
    for row in findings:
        if not isinstance(row, dict):
            continue
        status = str(row.get("status") or "open").strip().lower()
        severity = str(row.get("severity") or "medium").strip().lower()
        if finding_status_filter is not None and status != finding_status_filter:
            continue
        if finding_severity_filter is not None and severity != finding_severity_filter:
            continue
        return True
    return False


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
        if key in {"webhook_url", "webhook_secret", "job_events", "review_comments", "client_metadata"}:
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


def public_job_review_workflow_payload(
    job_id: str,
    job: Dict[str, Any],
    *,
    event_type: Optional[str] = None,
    finding_id: Optional[str] = None,
    comment_status: Optional[str] = None,
    workflow_state: Optional[str] = None,
    overdue_after_hours: int = REVIEW_WORKFLOW_OVERDUE_DEFAULT_HOURS,
) -> Dict[str, Any]:
    event_type_filter = str(event_type or "").strip() or None
    finding_id_filter = str(finding_id or "").strip() or None
    comment_status_filter = str(comment_status or "").strip().lower() or None
    workflow_state_filter = _normalize_review_workflow_state_filter(workflow_state)
    overdue_after_hours_value = (
        int(overdue_after_hours)
        if isinstance(overdue_after_hours, int) and overdue_after_hours > 0
        else REVIEW_WORKFLOW_OVERDUE_DEFAULT_HOURS
    )

    critic_payload = public_job_critic_payload(job_id, job)
    findings = critic_payload.get("fatal_flaws") if isinstance(critic_payload, dict) else []
    findings_list = [item for item in findings if isinstance(item, dict)] if isinstance(findings, list) else []
    if finding_id_filter:
        findings_list = [item for item in findings_list if finding_primary_id(item) == finding_id_filter]

    comments_payload = public_job_comments_payload(job_id, job)
    comments = comments_payload.get("comments") if isinstance(comments_payload, dict) else []
    comments_list = [item for item in comments if isinstance(item, dict)] if isinstance(comments, list) else []
    if finding_id_filter:
        comments_list = [
            item for item in comments_list if str(item.get("linked_finding_id") or "") == finding_id_filter
        ]

    raw_events = job.get("job_events")
    timeline_all: list[Dict[str, Any]] = []
    if isinstance(raw_events, list):
        for item in raw_events:
            if not isinstance(item, dict):
                continue
            event = sanitize_for_public_response(item)
            if not isinstance(event, dict):
                continue
            event_type = str(event.get("type") or "").strip()
            if event_type not in REVIEW_WORKFLOW_EVENT_TYPES:
                continue
            event_finding_id = str(event.get("finding_id") or "").strip() or None
            comment_id = str(event.get("comment_id") or "").strip() or None
            timeline_all.append(
                {
                    "event_id": event.get("event_id"),
                    "ts": event.get("ts"),
                    "type": event_type,
                    "kind": (
                        "finding_status"
                        if event_type == "critic_finding_status_changed"
                        else ("comment_added" if event_type == "review_comment_added" else "comment_status")
                    ),
                    "finding_id": event_finding_id,
                    "comment_id": comment_id,
                    "status": event.get("status"),
                    "section": event.get("section"),
                    "severity": event.get("severity"),
                    "actor": event.get("actor"),
                    "author": event.get("author"),
                    "message": event.get("message"),
                }
            )
    finding_last_event_ts: Dict[str, datetime] = {}
    comment_last_event_ts: Dict[str, datetime] = {}
    activity_dt_values: list[datetime] = []

    def _latest(existing: Optional[datetime], candidate: Optional[datetime]) -> Optional[datetime]:
        if existing is None:
            return candidate
        if candidate is None:
            return existing
        return candidate if candidate > existing else existing

    for row in timeline_all:
        ts_dt = _parse_event_ts(row.get("ts"))
        if ts_dt is None:
            continue
        activity_dt_values.append(ts_dt)
        event_finding_id = str(row.get("finding_id") or "").strip()
        event_comment_id = str(row.get("comment_id") or "").strip()
        if str(row.get("type") or "") == "critic_finding_status_changed" and event_finding_id:
            finding_last_event_ts[event_finding_id] = (
                _latest(finding_last_event_ts.get(event_finding_id), ts_dt) or ts_dt
            )
        if str(row.get("kind") or "") in {"comment_added", "comment_status"} and event_comment_id:
            comment_last_event_ts[event_comment_id] = (
                _latest(comment_last_event_ts.get(event_comment_id), ts_dt) or ts_dt
            )

    for row in comments_list:
        for key in ("updated_ts", "resolved_at", "ts"):
            ts_dt = _parse_event_ts(row.get(key))
            if ts_dt is not None:
                activity_dt_values.append(ts_dt)
                break

    for row in findings_list:
        for key in ("updated_at", "resolved_at", "acknowledged_at"):
            ts_dt = _parse_event_ts(row.get(key))
            if ts_dt is not None:
                activity_dt_values.append(ts_dt)
                break

    reference_ts = max(activity_dt_values) if activity_dt_values else None

    findings_with_workflow: list[Dict[str, Any]] = []
    for row in findings_list:
        current = dict(row)
        current_finding_id = finding_primary_id(current)
        status = str(current.get("status") or "open").strip().lower() or "open"
        unresolved = status in {"open", "acknowledged"}
        last_transition_dt = finding_last_event_ts.get(current_finding_id or "")
        if last_transition_dt is None:
            for key in ("updated_at", "acknowledged_at", "resolved_at"):
                parsed = _parse_event_ts(current.get(key))
                if parsed is not None:
                    last_transition_dt = parsed
                    break
        due_at_dt = _parse_event_ts(current.get("due_at"))
        threshold_due_dt = (
            last_transition_dt + timedelta(hours=float(overdue_after_hours_value))
            if unresolved and last_transition_dt is not None
            else None
        )
        if due_at_dt is None:
            due_at_dt = threshold_due_dt
        effective_due_dt = due_at_dt
        if due_at_dt is not None and threshold_due_dt is not None:
            effective_due_dt = min(due_at_dt, threshold_due_dt)
        age_hours: Optional[float] = None
        if unresolved and reference_ts is not None and last_transition_dt is not None:
            age_hours = max(0.0, (reference_ts - last_transition_dt).total_seconds() / 3600.0)
        if unresolved and reference_ts is not None and effective_due_dt is not None:
            is_overdue = reference_ts >= effective_due_dt
        else:
            is_overdue = bool(unresolved and age_hours is not None and age_hours >= float(overdue_after_hours_value))
        time_to_due_hours: Optional[float] = None
        if unresolved and reference_ts is not None and effective_due_dt is not None:
            time_to_due_hours = (effective_due_dt - reference_ts).total_seconds() / 3600.0
        if status == "resolved":
            current["workflow_state"] = "resolved"
        elif is_overdue:
            current["workflow_state"] = "overdue"
        else:
            current["workflow_state"] = "pending"
        current["is_overdue"] = is_overdue
        current["age_hours"] = round(age_hours, 3) if age_hours is not None else None
        current["time_to_due_hours"] = round(time_to_due_hours, 3) if time_to_due_hours is not None else None
        current["due_at"] = due_at_dt.isoformat() if due_at_dt is not None else current.get("due_at")
        current["last_transition_at"] = last_transition_dt.isoformat() if last_transition_dt is not None else None
        findings_with_workflow.append(current)

    comments_with_workflow: list[Dict[str, Any]] = []
    for row in comments_list:
        current = dict(row)
        current_comment_id = str(current.get("comment_id") or "").strip()
        status = str(current.get("status") or "open").strip().lower() or "open"
        unresolved = status != "resolved"
        last_transition_dt = comment_last_event_ts.get(current_comment_id)
        if last_transition_dt is None:
            for key in ("updated_ts", "resolved_at", "ts"):
                parsed = _parse_event_ts(current.get(key))
                if parsed is not None:
                    last_transition_dt = parsed
                    break
        due_at_dt = _parse_event_ts(current.get("due_at"))
        threshold_due_dt = (
            last_transition_dt + timedelta(hours=float(overdue_after_hours_value))
            if unresolved and last_transition_dt is not None
            else None
        )
        if due_at_dt is None:
            due_at_dt = threshold_due_dt
        effective_due_dt = due_at_dt
        if due_at_dt is not None and threshold_due_dt is not None:
            effective_due_dt = min(due_at_dt, threshold_due_dt)
        age_hours: Optional[float] = None
        if unresolved and reference_ts is not None and last_transition_dt is not None:
            age_hours = max(0.0, (reference_ts - last_transition_dt).total_seconds() / 3600.0)
        if unresolved and reference_ts is not None and effective_due_dt is not None:
            is_overdue = reference_ts >= effective_due_dt
        else:
            is_overdue = bool(unresolved and age_hours is not None and age_hours >= float(overdue_after_hours_value))
        time_to_due_hours: Optional[float] = None
        if unresolved and reference_ts is not None and effective_due_dt is not None:
            time_to_due_hours = (effective_due_dt - reference_ts).total_seconds() / 3600.0
        if status == "resolved":
            current["workflow_state"] = "resolved"
        elif is_overdue:
            current["workflow_state"] = "overdue"
        else:
            current["workflow_state"] = "pending"
        current["is_overdue"] = is_overdue
        current["age_hours"] = round(age_hours, 3) if age_hours is not None else None
        current["time_to_due_hours"] = round(time_to_due_hours, 3) if time_to_due_hours is not None else None
        current["due_at"] = due_at_dt.isoformat() if due_at_dt is not None else current.get("due_at")
        current["last_transition_at"] = last_transition_dt.isoformat() if last_transition_dt is not None else None
        comments_with_workflow.append(current)

    if comment_status_filter:
        comments_with_workflow = [
            item
            for item in comments_with_workflow
            if str(item.get("status") or "").strip().lower() == comment_status_filter
        ]
    if workflow_state_filter in REVIEW_WORKFLOW_STATE_FILTER_VALUES:
        findings_with_workflow = [
            item for item in findings_with_workflow if str(item.get("workflow_state") or "") == workflow_state_filter
        ]
        comments_with_workflow = [
            item for item in comments_with_workflow if str(item.get("workflow_state") or "") == workflow_state_filter
        ]

    finding_status_counts = {"open": 0, "acknowledged": 0, "resolved": 0}
    finding_severity_counts = {"high": 0, "medium": 0, "low": 0}
    pending_finding_count = 0
    overdue_finding_count = 0
    for row in findings_with_workflow:
        status = str(row.get("status") or "open").strip().lower()
        severity = str(row.get("severity") or "").strip().lower()
        workflow_status = str(row.get("workflow_state") or "").strip().lower()
        if status in finding_status_counts:
            finding_status_counts[status] += 1
        if severity in finding_severity_counts:
            finding_severity_counts[severity] += 1
        if workflow_status == "pending":
            pending_finding_count += 1
        elif workflow_status == "overdue":
            overdue_finding_count += 1

    finding_ids = {finding_primary_id(row) for row in findings_with_workflow if finding_primary_id(row)}
    comment_ids = {
        str(row.get("comment_id") or "").strip()
        for row in comments_with_workflow
        if str(row.get("comment_id") or "").strip()
    }
    linked_comment_count = 0
    orphan_linked_comment_count = 0
    comment_status_counts: Dict[str, int] = {}
    pending_comment_count = 0
    overdue_comment_count = 0
    for row in comments_with_workflow:
        row_status = str(row.get("status") or "open").strip().lower() or "open"
        comment_status_counts[row_status] = int(comment_status_counts.get(row_status, 0)) + 1
        workflow_status = str(row.get("workflow_state") or "").strip().lower()
        if workflow_status == "pending":
            pending_comment_count += 1
        elif workflow_status == "overdue":
            overdue_comment_count += 1
        linked_finding_id = str(row.get("linked_finding_id") or "").strip()
        if not linked_finding_id:
            continue
        linked_comment_count += 1
        if linked_finding_id not in finding_ids:
            orphan_linked_comment_count += 1

    timeline = list(timeline_all)
    if finding_id_filter:
        timeline = [
            row
            for row in timeline
            if str(row.get("finding_id") or "").strip() == finding_id_filter
            or str(row.get("comment_id") or "").strip() in comment_ids
        ]
    if comment_status_filter:
        timeline = [
            row
            for row in timeline
            if str(row.get("kind") or "") not in {"comment_added", "comment_status"}
            or str(row.get("comment_id") or "").strip() in comment_ids
        ]
    if workflow_state_filter in REVIEW_WORKFLOW_STATE_FILTER_VALUES:
        timeline = [
            row
            for row in timeline
            if str(row.get("finding_id") or "").strip() in finding_ids
            or str(row.get("comment_id") or "").strip() in comment_ids
        ]
    if event_type_filter:
        timeline = [row for row in timeline if str(row.get("type") or "") == event_type_filter]
    timeline.sort(key=lambda row: str(row.get("ts") or ""), reverse=True)

    activity_ts_values: list[str] = []
    for row in timeline:
        ts = str(row.get("ts") or "").strip()
        if ts:
            activity_ts_values.append(ts)
    for row in comments_with_workflow:
        ts = str(row.get("ts") or "").strip()
        if ts:
            activity_ts_values.append(ts)
    for row in findings_with_workflow:
        for key in ("updated_at", "resolved_at", "acknowledged_at"):
            ts = str(row.get(key) or "").strip()
            if ts:
                activity_ts_values.append(ts)
    last_activity_at = max(activity_ts_values) if activity_ts_values else None

    summary = {
        "finding_count": len(findings_list),
        "comment_count": len(comments_list),
        "linked_comment_count": linked_comment_count,
        "orphan_linked_comment_count": orphan_linked_comment_count,
        "open_finding_count": int(finding_status_counts.get("open", 0)),
        "acknowledged_finding_count": int(finding_status_counts.get("acknowledged", 0)),
        "resolved_finding_count": int(finding_status_counts.get("resolved", 0)),
        "pending_finding_count": pending_finding_count,
        "overdue_finding_count": overdue_finding_count,
        "open_comment_count": int(comment_status_counts.get("open", 0)),
        "resolved_comment_count": int(comment_status_counts.get("resolved", 0)),
        "pending_comment_count": pending_comment_count,
        "overdue_comment_count": overdue_comment_count,
        "finding_status_counts": finding_status_counts,
        "finding_severity_counts": finding_severity_counts,
        "comment_status_counts": comment_status_counts,
        "timeline_event_count": len(timeline),
        "last_activity_at": last_activity_at,
    }
    return {
        "job_id": str(job_id),
        "status": str(job.get("status") or ""),
        "filters": {
            "event_type": event_type_filter,
            "finding_id": finding_id_filter,
            "comment_status": comment_status_filter,
            "workflow_state": workflow_state_filter,
            "overdue_after_hours": overdue_after_hours_value,
        },
        "summary": summary,
        "findings": findings_with_workflow,
        "comments": comments_with_workflow,
        "timeline": timeline,
    }


def public_job_review_workflow_sla_payload(
    job_id: str,
    job: Dict[str, Any],
    *,
    overdue_after_hours: int = REVIEW_WORKFLOW_OVERDUE_DEFAULT_HOURS,
    top_limit: int = 5,
) -> Dict[str, Any]:
    workflow_payload = public_job_review_workflow_payload(
        job_id,
        job,
        overdue_after_hours=overdue_after_hours,
    )
    findings = workflow_payload.get("findings")
    comments = workflow_payload.get("comments")
    findings_list = [item for item in findings if isinstance(item, dict)] if isinstance(findings, list) else []
    comments_list = [item for item in comments if isinstance(item, dict)] if isinstance(comments, list) else []

    summary = workflow_payload.get("summary")
    summary_dict = summary if isinstance(summary, dict) else {}
    reference_ts = _parse_event_ts(summary_dict.get("last_activity_at"))

    finding_severity_by_id: Dict[str, str] = {}
    for row in findings_list:
        finding_id = finding_primary_id(row)
        severity = str(row.get("severity") or "").strip().lower()
        if finding_id:
            finding_severity_by_id[finding_id] = severity or "unknown"

    overdue_by_severity: Dict[str, int] = {}
    overdue_by_section: Dict[str, int] = {}
    overdue_rows: list[Dict[str, Any]] = []

    def _append_overdue_row(
        *,
        kind: str,
        row_id: str,
        section: Optional[str],
        severity: Optional[str],
        status: Optional[str],
        due_at: Optional[str],
        message: Optional[str],
        linked_finding_id: Optional[str] = None,
    ) -> None:
        due_dt = _parse_event_ts(due_at)
        overdue_hours: Optional[float] = None
        if reference_ts is not None and due_dt is not None:
            overdue_hours = max(0.0, (reference_ts - due_dt).total_seconds() / 3600.0)
        overdue_rows.append(
            {
                "kind": kind,
                "id": row_id,
                "section": section,
                "severity": severity,
                "status": status,
                "due_at": due_at,
                "overdue_hours": round(overdue_hours, 3) if overdue_hours is not None else None,
                "message": message,
                "linked_finding_id": linked_finding_id,
            }
        )
        section_key = str(section or "unknown").strip().lower() or "unknown"
        severity_key = str(severity or "unknown").strip().lower() or "unknown"
        overdue_by_section[section_key] = int(overdue_by_section.get(section_key) or 0) + 1
        overdue_by_severity[severity_key] = int(overdue_by_severity.get(severity_key) or 0) + 1

    unresolved_finding_count = 0
    overdue_finding_count = 0
    for row in findings_list:
        status = str(row.get("status") or "open").strip().lower() or "open"
        unresolved = status in {"open", "acknowledged"}
        if not unresolved:
            continue
        unresolved_finding_count += 1
        if not bool(row.get("is_overdue")):
            continue
        overdue_finding_count += 1
        _append_overdue_row(
            kind="finding",
            row_id=str(finding_primary_id(row) or ""),
            section=str(row.get("section") or "").strip() or None,
            severity=str(row.get("severity") or "").strip().lower() or None,
            status=status,
            due_at=str(row.get("due_at") or "").strip() or None,
            message=str(row.get("message") or "").strip() or None,
        )

    unresolved_comment_count = 0
    overdue_comment_count = 0
    for row in comments_list:
        status = str(row.get("status") or "open").strip().lower() or "open"
        unresolved = status != "resolved"
        if not unresolved:
            continue
        unresolved_comment_count += 1
        if not bool(row.get("is_overdue")):
            continue
        overdue_comment_count += 1
        linked_finding_id = str(row.get("linked_finding_id") or "").strip() or None
        severity = finding_severity_by_id.get(linked_finding_id or "", "unknown")
        _append_overdue_row(
            kind="comment",
            row_id=str(row.get("comment_id") or "").strip(),
            section=str(row.get("section") or "").strip() or None,
            severity=severity,
            status=status,
            due_at=str(row.get("due_at") or "").strip() or None,
            message=str(row.get("message") or "").strip() or None,
            linked_finding_id=linked_finding_id,
        )

    def _sort_key(item: Dict[str, Any]) -> tuple[float, str]:
        overdue_hours = item.get("overdue_hours")
        try:
            overdue_hours_value = float(overdue_hours)
        except (TypeError, ValueError):
            overdue_hours_value = -1.0
        due_at = str(item.get("due_at") or "")
        return overdue_hours_value, due_at

    overdue_rows.sort(key=_sort_key, reverse=True)
    top_n = max(1, int(top_limit))
    top_overdue = overdue_rows[:top_n]
    oldest_overdue = top_overdue[0] if top_overdue else None

    unresolved_total = unresolved_finding_count + unresolved_comment_count
    overdue_total = overdue_finding_count + overdue_comment_count
    breach_rate = (overdue_total / unresolved_total) if unresolved_total else None

    return {
        "job_id": str(job_id),
        "status": str(job.get("status") or ""),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "overdue_after_hours": int(overdue_after_hours),
        "finding_total": len(findings_list),
        "comment_total": len(comments_list),
        "unresolved_finding_count": unresolved_finding_count,
        "unresolved_comment_count": unresolved_comment_count,
        "unresolved_total": unresolved_total,
        "overdue_finding_count": overdue_finding_count,
        "overdue_comment_count": overdue_comment_count,
        "overdue_total": overdue_total,
        "breach_rate": round(breach_rate, 4) if breach_rate is not None else None,
        "overdue_by_severity": overdue_by_severity,
        "overdue_by_section": overdue_by_section,
        "oldest_overdue": oldest_overdue,
        "top_overdue": top_overdue,
        "workflow_summary": summary_dict,
    }


def public_job_critic_payload(job_id: str, job: Dict[str, Any]) -> Dict[str, Any]:
    state = job.get("state")
    critic_notes = (state or {}).get("critic_notes") if isinstance(state, dict) else {}
    if not isinstance(critic_notes, dict):
        critic_notes = {}

    raw_flaws = critic_notes.get("fatal_flaws")
    fatal_flaws = (
        [sanitize_for_public_response(item) for item in normalize_findings(raw_flaws, default_source="rules")]
        if isinstance(raw_flaws, list)
        else []
    )

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
            finding_id = finding_primary_id(flaw)
            if not finding_id:
                continue
            flaw["id"] = finding_id
            flaw["finding_id"] = finding_id
            linked = linked_comment_ids_by_finding.get(finding_id) or []
            if linked:
                flaw["linked_comment_ids"] = linked

    raw_messages = critic_notes.get("fatal_flaw_messages")
    fatal_flaw_messages = (
        [str(item) for item in raw_messages if isinstance(item, (str, int, float))]
        if isinstance(raw_messages, list)
        else []
    )

    raw_checks = critic_notes.get("rule_checks")
    rule_checks = (
        [sanitize_for_public_response(item) for item in raw_checks if isinstance(item, dict)]
        if isinstance(raw_checks, list)
        else []
    )

    return {
        "job_id": str(job_id),
        "status": str(job.get("status") or ""),
        "quality_score": sanitize_for_public_response(
            (state or {}).get("quality_score") if isinstance(state, dict) else None
        ),
        "critic_score": sanitize_for_public_response(
            (state or {}).get("critic_score") if isinstance(state, dict) else None
        ),
        "engine": sanitize_for_public_response(critic_notes.get("engine")),
        "rule_score": sanitize_for_public_response(critic_notes.get("rule_score")),
        "llm_score": sanitize_for_public_response(critic_notes.get("llm_score")),
        "needs_revision": sanitize_for_public_response(
            (state or {}).get("needs_revision") if isinstance(state, dict) else None
        ),
        "revision_instructions": sanitize_for_public_response(critic_notes.get("revision_instructions")),
        "fatal_flaw_count": len(fatal_flaws),
        "fatal_flaws": fatal_flaws,
        "fatal_flaw_messages": fatal_flaw_messages,
        "rule_check_count": len(rule_checks),
        "rule_checks": rule_checks,
        "llm_advisory_diagnostics": sanitize_for_public_response(critic_notes.get("llm_advisory_diagnostics")),
        "llm_advisory_normalization": sanitize_for_public_response(critic_notes.get("llm_advisory_normalization")),
        "llm_advisory_score_calibration": sanitize_for_public_response(
            critic_notes.get("llm_advisory_score_calibration")
        ),
    }


def public_job_export_payload(
    job_id: str,
    job: Dict[str, Any],
    *,
    ingest_inventory_rows: Optional[list[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    state = job.get("state")
    state_payload = public_state_snapshot(state) if isinstance(state, dict) else {}

    critic = public_job_critic_payload(job_id, job)
    critic_findings = critic.get("fatal_flaws") if isinstance(critic, dict) else []
    if not isinstance(critic_findings, list):
        critic_findings = []

    comments_payload = public_job_comments_payload(job_id, job)
    review_comments = comments_payload.get("comments") if isinstance(comments_payload, dict) else []
    if not isinstance(review_comments, list):
        review_comments = []
    readiness_payload = _public_job_quality_readiness_payload(job, ingest_inventory_rows)

    return {
        "job_id": str(job_id),
        "status": str(job.get("status") or ""),
        "payload": {
            "state": state_payload if isinstance(state_payload, dict) else {},
            "critic_findings": [item for item in critic_findings if isinstance(item, dict)],
            "review_comments": [item for item in review_comments if isinstance(item, dict)],
            "readiness": readiness_payload,
        },
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


def public_ingest_recent_payload(
    records: list[Dict[str, Any]],
    *,
    donor_id: Optional[str] = None,
) -> Dict[str, Any]:
    safe_records = [sanitize_for_public_response(item) for item in records if isinstance(item, dict)]
    return {
        "count": len(safe_records),
        "donor_id": donor_id,
        "records": safe_records,
    }


def public_ingest_inventory_payload(
    rows: list[Dict[str, Any]],
    *,
    donor_id: Optional[str] = None,
) -> Dict[str, Any]:
    safe_rows = [sanitize_for_public_response(item) for item in rows if isinstance(item, dict)]
    doc_family_counts: Dict[str, int] = {}
    total_uploads = 0
    for row in safe_rows:
        doc_family = str(row.get("doc_family") or "").strip()
        count = row.get("count")
        try:
            count_int = int(count)
        except (TypeError, ValueError):
            count_int = 0
        if not doc_family or count_int <= 0:
            continue
        doc_family_counts[doc_family] = count_int
        total_uploads += count_int
    return {
        "donor_id": donor_id,
        "total_uploads": total_uploads,
        "family_count": len(doc_family_counts),
        "doc_family_counts": doc_family_counts,
        "doc_families": safe_rows,
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
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
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


def _public_job_quality_readiness_payload(
    job: Dict[str, Any],
    ingest_inventory_rows: Optional[list[Dict[str, Any]]] = None,
) -> Optional[Dict[str, Any]]:
    client_metadata = job.get("client_metadata")
    if not isinstance(client_metadata, dict):
        return None

    rag_readiness = client_metadata.get("rag_readiness")
    if not isinstance(rag_readiness, dict):
        return None

    raw_expected = rag_readiness.get("expected_doc_families")
    if not isinstance(raw_expected, list):
        return None

    expected_doc_families: list[str] = []
    seen: set[str] = set()
    for item in raw_expected:
        doc_family = str(item or "").strip()
        if not doc_family or doc_family in seen:
            continue
        expected_doc_families.append(doc_family)
        seen.add(doc_family)
    if not expected_doc_families:
        return None

    state = job.get("state")
    state_dict: Dict[str, Any] = state if isinstance(state, dict) else {}
    donor_id = (
        str(
            rag_readiness.get("donor_id")
            or client_metadata.get("donor_id")
            or state_dict.get("donor_id")
            or state_dict.get("donor")
            or ""
        ).strip()
        or None
    )

    inventory_payload = public_ingest_inventory_payload(ingest_inventory_rows or [], donor_id=donor_id)
    doc_family_counts_raw = inventory_payload.get("doc_family_counts")
    doc_family_counts = doc_family_counts_raw if isinstance(doc_family_counts_raw, dict) else {}

    present_doc_families = [doc for doc in expected_doc_families if int(doc_family_counts.get(doc) or 0) > 0]
    missing_doc_families = [doc for doc in expected_doc_families if int(doc_family_counts.get(doc) or 0) <= 0]

    expected_count = len(expected_doc_families)
    loaded_count = len(present_doc_families)
    coverage_rate = round(loaded_count / expected_count, 4) if expected_count else None
    inventory_total_uploads = int(inventory_payload.get("total_uploads") or 0)
    namespace_empty = inventory_total_uploads <= 0
    low_doc_coverage = bool(coverage_rate is not None and coverage_rate < 0.5)

    raw_architect_retrieval = state_dict.get("architect_retrieval")
    architect_retrieval = raw_architect_retrieval if isinstance(raw_architect_retrieval, dict) else {}
    architect_retrieval_enabled = (
        bool(architect_retrieval.get("enabled")) if isinstance(architect_retrieval.get("enabled"), bool) else None
    )
    architect_retrieval_hits_count_raw = architect_retrieval.get("hits_count")
    try:
        architect_retrieval_hits_count = (
            int(architect_retrieval_hits_count_raw) if architect_retrieval_hits_count_raw is not None else None
        )
    except (TypeError, ValueError):
        architect_retrieval_hits_count = None
    retrieval_namespace = str(architect_retrieval.get("namespace") or "").strip() or None

    warnings: list[Dict[str, Any]] = []
    if namespace_empty:
        warnings.append(
            {
                "code": "NAMESPACE_EMPTY",
                "severity": "high",
                "message": "No donor documents are currently uploaded for this readiness scope.",
            }
        )
    if low_doc_coverage:
        coverage_label = f"{loaded_count}/{expected_count}" if expected_count else "0/0"
        severity = "high" if loaded_count == 0 else "medium"
        warnings.append(
            {
                "code": "LOW_DOC_COVERAGE",
                "severity": severity,
                "message": f"Recommended document-family coverage is low ({coverage_label}).",
            }
        )
    if architect_retrieval_enabled and architect_retrieval_hits_count == 0:
        warnings.append(
            {
                "code": "ARCHITECT_RETRIEVAL_NO_HITS",
                "severity": "medium",
                "message": "Architect retrieval returned no hits; outputs may rely on fallback citations.",
            }
        )
    severity_rank = {"none": 0, "low": 1, "medium": 2, "high": 3}
    warning_level = "none"
    for row in warnings:
        level = str(row.get("severity") or "low").lower()
        if severity_rank.get(level, 1) > severity_rank.get(warning_level, 0):
            warning_level = level

    return {
        "preset_key": sanitize_for_public_response(client_metadata.get("demo_generate_preset_key")),
        "donor_id": donor_id,
        "expected_doc_families": expected_doc_families,
        "present_doc_families": present_doc_families,
        "missing_doc_families": missing_doc_families,
        "expected_count": expected_count,
        "loaded_count": loaded_count,
        "coverage_rate": coverage_rate,
        "inventory_total_uploads": inventory_total_uploads,
        "inventory_family_count": sanitize_for_public_response(inventory_payload.get("family_count")),
        "doc_family_counts": sanitize_for_public_response(doc_family_counts),
        "namespace_empty": namespace_empty,
        "low_doc_coverage": low_doc_coverage,
        "architect_retrieval_enabled": architect_retrieval_enabled,
        "architect_retrieval_hits_count": architect_retrieval_hits_count,
        "retrieval_namespace": retrieval_namespace,
        "warning_count": len(warnings),
        "warning_level": warning_level,
        "warnings": warnings,
    }


def _public_job_preflight_payload(job: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    preflight = job.get("generate_preflight")
    if not isinstance(preflight, dict):
        state = job.get("state")
        state_dict = state if isinstance(state, dict) else {}
        preflight = state_dict.get("generate_preflight")
    if not isinstance(preflight, dict):
        return None
    payload = sanitize_for_public_response(preflight)
    return cast(Dict[str, Any], payload) if isinstance(payload, dict) else None


def public_job_quality_payload(
    job_id: str,
    job: Dict[str, Any],
    *,
    ingest_inventory_rows: Optional[list[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    raw_state = job.get("state")
    state_dict: Dict[str, Any] = raw_state if isinstance(raw_state, dict) else {}
    critic_payload: Dict[str, Any] = public_job_critic_payload(job_id, job)
    metrics_payload: Dict[str, Any] = public_job_metrics_payload(job_id, job)
    citations_payload = public_job_citations_payload(job_id, job)

    citations = citations_payload.get("citations") if isinstance(citations_payload, dict) else []
    if not isinstance(citations, list):
        citations = []
    critic_flaws = critic_payload.get("fatal_flaws") if isinstance(critic_payload, dict) else []
    if not isinstance(critic_flaws, list):
        critic_flaws = []
    rule_checks = critic_payload.get("rule_checks") if isinstance(critic_payload, dict) else []
    if not isinstance(rule_checks, list):
        rule_checks = []

    architect_citations = [c for c in citations if isinstance(c, dict) and str(c.get("stage") or "") == "architect"]
    mel_citations = [c for c in citations if isinstance(c, dict) and str(c.get("stage") or "") == "mel"]

    confidence_values: list[float] = []
    high_conf = 0
    low_conf = 0
    rag_low_conf = 0
    fallback_ns = 0
    traceability_complete = 0
    traceability_partial = 0
    traceability_missing = 0
    architect_threshold_considered = 0
    architect_threshold_hits = 0
    for c in citations:
        if not isinstance(c, dict):
            continue
        if str(c.get("citation_type") or "") == "rag_low_confidence":
            rag_low_conf += 1
        if str(c.get("citation_type") or "") == "fallback_namespace":
            fallback_ns += 1
        traceability_status = citation_traceability_status(c)
        if traceability_status == "complete":
            traceability_complete += 1
        elif traceability_status == "partial":
            traceability_partial += 1
        else:
            traceability_missing += 1
        conf_raw = c.get("citation_confidence")
        try:
            conf = float(conf_raw) if conf_raw is not None else None
        except (TypeError, ValueError):
            conf = None
        if conf is not None:
            confidence_values.append(conf)
            if conf >= 0.7:
                high_conf += 1
            if conf < 0.3:
                low_conf += 1
        if str(c.get("stage") or "") == "architect":
            thr_raw = c.get("confidence_threshold")
            try:
                thr = float(thr_raw) if thr_raw is not None else None
            except (TypeError, ValueError):
                thr = None
            if thr is not None:
                architect_threshold_considered += 1
                if conf is not None and conf >= thr:
                    architect_threshold_hits += 1

    flaw_status_counts = {"open": 0, "acknowledged": 0, "resolved": 0}
    flaw_severity_counts = {"high": 0, "medium": 0, "low": 0}
    for flaw in critic_flaws:
        if not isinstance(flaw, dict):
            continue
        status = str(flaw.get("status") or "open").lower()
        severity = str(flaw.get("severity") or "").lower()
        if status in flaw_status_counts:
            flaw_status_counts[status] += 1
        if severity in flaw_severity_counts:
            flaw_severity_counts[severity] += 1

    failed_checks = sum(1 for c in rule_checks if isinstance(c, dict) and str(c.get("status") or "").lower() == "fail")
    warned_checks = sum(1 for c in rule_checks if isinstance(c, dict) and str(c.get("status") or "").lower() == "warn")
    llm_finding_label_counts: Dict[str, int] = {}
    for flaw in critic_payload.get("fatal_flaws") or []:
        if not isinstance(flaw, dict):
            continue
        if str(flaw.get("source") or "").lower() != "llm":
            continue
        label = str(flaw.get("label") or "").strip() or "GENERIC_LLM_REVIEW_FLAG"
        llm_finding_label_counts[label] = int(llm_finding_label_counts.get(label, 0)) + 1

    raw_toc_validation = state_dict.get("toc_validation")
    toc_validation: Dict[str, Any] = (
        cast(Dict[str, Any], raw_toc_validation) if isinstance(raw_toc_validation, dict) else {}
    )
    raw_toc_generation_meta = state_dict.get("toc_generation_meta")
    toc_generation_meta: Dict[str, Any] = (
        cast(Dict[str, Any], raw_toc_generation_meta) if isinstance(raw_toc_generation_meta, dict) else {}
    )
    raw_architect_retrieval = state_dict.get("architect_retrieval")
    architect_retrieval: Dict[str, Any] = (
        cast(Dict[str, Any], raw_architect_retrieval) if isinstance(raw_architect_retrieval, dict) else {}
    )
    readiness_payload = _public_job_quality_readiness_payload(job, ingest_inventory_rows)
    preflight_payload = _public_job_preflight_payload(job)
    traceability_gap = traceability_partial + traceability_missing

    return {
        "job_id": str(job_id),
        "status": str(job.get("status") or ""),
        "quality_score": sanitize_for_public_response(state_dict.get("quality_score")),
        "critic_score": sanitize_for_public_response(state_dict.get("critic_score")),
        "needs_revision": sanitize_for_public_response(state_dict.get("needs_revision")),
        "strict_preflight": sanitize_for_public_response(
            job.get("strict_preflight") if "strict_preflight" in job else state_dict.get("strict_preflight")
        ),
        "terminal_status": sanitize_for_public_response(metrics_payload.get("terminal_status")),
        "time_to_first_draft_seconds": sanitize_for_public_response(metrics_payload.get("time_to_first_draft_seconds")),
        "time_to_terminal_seconds": sanitize_for_public_response(metrics_payload.get("time_to_terminal_seconds")),
        "critic": {
            "engine": sanitize_for_public_response(critic_payload.get("engine")),
            "rule_score": sanitize_for_public_response(critic_payload.get("rule_score")),
            "llm_score": sanitize_for_public_response(critic_payload.get("llm_score")),
            "fatal_flaw_count": int(critic_payload.get("fatal_flaw_count") or 0),
            "open_finding_count": flaw_status_counts["open"],
            "acknowledged_finding_count": flaw_status_counts["acknowledged"],
            "resolved_finding_count": flaw_status_counts["resolved"],
            "high_severity_fatal_flaw_count": flaw_severity_counts["high"],
            "medium_severity_fatal_flaw_count": flaw_severity_counts["medium"],
            "low_severity_fatal_flaw_count": flaw_severity_counts["low"],
            "rule_check_count": int(critic_payload.get("rule_check_count") or 0),
            "failed_rule_check_count": failed_checks,
            "warned_rule_check_count": warned_checks,
            "llm_finding_label_counts": llm_finding_label_counts,
            "llm_advisory_diagnostics": sanitize_for_public_response(critic_payload.get("llm_advisory_diagnostics")),
        },
        "citations": {
            "citation_count": len(citations),
            "architect_citation_count": len(architect_citations),
            "mel_citation_count": len(mel_citations),
            "high_confidence_citation_count": high_conf,
            "low_confidence_citation_count": low_conf,
            "architect_rag_low_confidence_citation_count": sum(
                1 for c in architect_citations if str(c.get("citation_type") or "") == "rag_low_confidence"
            ),
            "mel_rag_low_confidence_citation_count": sum(
                1 for c in mel_citations if str(c.get("citation_type") or "") == "rag_low_confidence"
            ),
            "rag_low_confidence_citation_count": rag_low_conf,
            "fallback_namespace_citation_count": fallback_ns,
            "fallback_namespace_citation_rate": round(fallback_ns / len(citations), 4) if citations else None,
            "grounding_risk_level": _grounding_risk_level(
                fallback_count=fallback_ns,
                citation_count=len(citations),
            ),
            "traceability_complete_citation_count": traceability_complete,
            "traceability_partial_citation_count": traceability_partial,
            "traceability_missing_citation_count": traceability_missing,
            "traceability_gap_citation_count": traceability_gap,
            "traceability_gap_citation_rate": round(traceability_gap / len(citations), 4) if citations else None,
            "citation_confidence_avg": (
                round(sum(confidence_values) / len(confidence_values), 4) if confidence_values else None
            ),
            "architect_threshold_hit_rate": (
                round(architect_threshold_hits / architect_threshold_considered, 4)
                if architect_threshold_considered
                else None
            ),
        },
        "architect": {
            "engine": sanitize_for_public_response(toc_generation_meta.get("engine")),
            "llm_used": sanitize_for_public_response(toc_generation_meta.get("llm_used")),
            "retrieval_used": sanitize_for_public_response(toc_generation_meta.get("retrieval_used")),
            "retrieval_enabled": sanitize_for_public_response(architect_retrieval.get("enabled")),
            "retrieval_hits_count": sanitize_for_public_response(architect_retrieval.get("hits_count")),
            "retrieval_namespace": sanitize_for_public_response(architect_retrieval.get("namespace")),
            "toc_schema_name": sanitize_for_public_response(toc_validation.get("schema_name")),
            "toc_schema_valid": sanitize_for_public_response(toc_validation.get("valid")),
            "citation_policy": sanitize_for_public_response(toc_generation_meta.get("citation_policy")),
        },
        "preflight": preflight_payload,
        "readiness": readiness_payload,
    }


def public_portfolio_metrics_payload(
    jobs_by_id: Dict[str, Dict[str, Any]],
    *,
    donor_id: Optional[str] = None,
    status: Optional[str] = None,
    hitl_enabled: Optional[bool] = None,
    warning_level: Optional[str] = None,
    grounding_risk_level: Optional[str] = None,
) -> Dict[str, Any]:
    warning_level_filter = _normalize_warning_level_filter(warning_level)
    grounding_risk_filter = _normalize_grounding_risk_filter(grounding_risk_level)
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
        if warning_level_filter is not None and _job_warning_level(job) != warning_level_filter:
            continue
        if grounding_risk_filter is not None and _job_grounding_risk_level(job) != grounding_risk_filter:
            continue
        filtered.append((str(job_id), job))

    status_counts: Dict[str, int] = {}
    donor_counts: Dict[str, int] = {}
    warning_level_counts: Dict[str, int] = {}
    grounding_risk_counts: Dict[str, int] = {}
    total_pause_count = 0
    total_resume_count = 0
    metrics_rows: list[Dict[str, Any]] = []

    for job_id, job in filtered:
        job_status = str(job.get("status") or "")
        status_counts[job_status] = status_counts.get(job_status, 0) + 1
        state = job.get("state") if isinstance(job.get("state"), dict) else {}
        job_donor = str((state or {}).get("donor_id") or (state or {}).get("donor") or "unknown")
        donor_counts[job_donor] = donor_counts.get(job_donor, 0) + 1
        job_warning_level = _job_warning_level(job)
        warning_level_counts[job_warning_level] = warning_level_counts.get(job_warning_level, 0) + 1
        job_grounding_risk_level = _job_grounding_risk_level(job)
        grounding_risk_counts[job_grounding_risk_level] = grounding_risk_counts.get(job_grounding_risk_level, 0) + 1

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

    job_count = len(filtered)
    warning_level_job_counts, warning_level_job_rates = _warning_level_breakdown(warning_level_counts, job_count)
    grounding_risk_job_counts, grounding_risk_job_rates = _grounding_risk_breakdown(grounding_risk_counts, job_count)

    return {
        "job_count": job_count,
        "filters": {
            "donor_id": donor_id,
            "status": status,
            "hitl_enabled": hitl_enabled,
            "warning_level": warning_level_filter,
            "grounding_risk_level": grounding_risk_filter,
        },
        "status_counts": status_counts,
        "donor_counts": donor_counts,
        "warning_level_counts": warning_level_counts,
        "warning_level_job_counts": warning_level_job_counts,
        "warning_level_job_rates": warning_level_job_rates,
        "grounding_risk_counts": grounding_risk_counts,
        "grounding_risk_job_counts": grounding_risk_job_counts,
        "grounding_risk_job_rates": grounding_risk_job_rates,
        "grounding_risk_high_job_count": int(grounding_risk_job_counts.get("high") or 0),
        "grounding_risk_medium_job_count": int(grounding_risk_job_counts.get("medium") or 0),
        "grounding_risk_low_job_count": int(grounding_risk_job_counts.get("low") or 0),
        "grounding_risk_unknown_job_count": int(grounding_risk_job_counts.get("unknown") or 0),
        "terminal_job_count": len(terminal_rows),
        "hitl_job_count": sum(1 for _, job in filtered if bool(job.get("hitl_enabled"))),
        "total_pause_count": total_pause_count,
        "total_resume_count": total_resume_count,
        "avg_time_to_first_draft_seconds": _avg("time_to_first_draft_seconds"),
        "avg_time_to_terminal_seconds": _avg("time_to_terminal_seconds"),
        "avg_time_in_pending_hitl_seconds": _avg("time_in_pending_hitl_seconds"),
    }


def public_portfolio_quality_payload(
    jobs_by_id: Dict[str, Dict[str, Any]],
    *,
    donor_id: Optional[str] = None,
    status: Optional[str] = None,
    hitl_enabled: Optional[bool] = None,
    warning_level: Optional[str] = None,
    grounding_risk_level: Optional[str] = None,
    finding_status: Optional[str] = None,
    finding_severity: Optional[str] = None,
) -> Dict[str, Any]:
    warning_level_filter = _normalize_warning_level_filter(warning_level)
    grounding_risk_filter = _normalize_grounding_risk_filter(grounding_risk_level)
    finding_status_filter = _normalize_finding_status_filter(finding_status)
    finding_severity_filter = _normalize_finding_severity_filter(finding_severity)
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
        if warning_level_filter is not None and _job_warning_level(job) != warning_level_filter:
            continue
        if grounding_risk_filter is not None and _job_grounding_risk_level(job) != grounding_risk_filter:
            continue
        if not _job_matches_finding_filters(
            job,
            finding_status_filter=finding_status_filter,
            finding_severity_filter=finding_severity_filter,
        ):
            continue
        filtered.append((str(job_id), job))

    status_counts: Dict[str, int] = {}
    donor_counts: Dict[str, int] = {}
    warning_level_counts: Dict[str, int] = {}
    grounding_risk_counts: Dict[str, int] = {}
    finding_status_counts: Dict[str, int] = {}
    finding_severity_counts: Dict[str, int] = {}
    donor_needs_revision_counts: Dict[str, int] = {}
    donor_open_findings_counts: Dict[str, int] = {}
    donor_weighted_risk_breakdown: Dict[str, Dict[str, Any]] = {}
    quality_rows: list[Dict[str, Any]] = []

    for job_id, job in filtered:
        job_status = str(job.get("status") or "")
        status_counts[job_status] = status_counts.get(job_status, 0) + 1
        state = job.get("state") if isinstance(job.get("state"), dict) else {}
        job_donor = str((state or {}).get("donor_id") or (state or {}).get("donor") or "unknown")
        donor_counts[job_donor] = donor_counts.get(job_donor, 0) + 1
        job_warning_level = _job_warning_level(job)
        warning_level_counts[job_warning_level] = warning_level_counts.get(job_warning_level, 0) + 1
        job_grounding_risk_level = _job_grounding_risk_level(job)
        grounding_risk_counts[job_grounding_risk_level] = grounding_risk_counts.get(job_grounding_risk_level, 0) + 1

        q = public_job_quality_payload(job_id, job)
        q["_donor_id"] = job_donor
        quality_rows.append(q)

        critic_summary: Dict[str, Any] = (
            cast(Dict[str, Any], q.get("critic")) if isinstance(q.get("critic"), dict) else {}
        )
        if bool(q.get("needs_revision")):
            donor_needs_revision_counts[job_donor] = donor_needs_revision_counts.get(job_donor, 0) + 1
        open_findings = int(critic_summary.get("open_finding_count") or 0)
        if open_findings > 0:
            donor_open_findings_counts[job_donor] = donor_open_findings_counts.get(job_donor, 0) + open_findings
        finding_status_counts["open"] = int(finding_status_counts.get("open", 0)) + open_findings
        finding_status_counts["acknowledged"] = int(finding_status_counts.get("acknowledged", 0)) + int(
            critic_summary.get("acknowledged_finding_count") or 0
        )
        finding_status_counts["resolved"] = int(finding_status_counts.get("resolved", 0)) + int(
            critic_summary.get("resolved_finding_count") or 0
        )
        finding_severity_counts["high"] = int(finding_severity_counts.get("high", 0)) + int(
            critic_summary.get("high_severity_fatal_flaw_count") or 0
        )
        finding_severity_counts["medium"] = int(finding_severity_counts.get("medium", 0)) + int(
            critic_summary.get("medium_severity_fatal_flaw_count") or 0
        )
        finding_severity_counts["low"] = int(finding_severity_counts.get("low", 0)) + int(
            critic_summary.get("low_severity_fatal_flaw_count") or 0
        )

    def _avg(rows: list[Dict[str, Any]], key: str) -> Optional[float]:
        values = [float(row[key]) for row in rows if isinstance(row.get(key), (int, float))]
        if not values:
            return None
        return round(sum(values) / len(values), 4)

    terminal_statuses = {"done", "error", "canceled"}
    terminal_rows = [row for row in quality_rows if str(row.get("terminal_status") or "") in terminal_statuses]

    critic_open_findings_total = 0
    critic_high_severity_total = 0
    critic_fatal_flaws_total = 0
    critic_medium_severity_total = 0
    needs_revision_job_count = 0
    citation_count_total = 0
    low_confidence_citation_count = 0
    rag_low_confidence_citation_count = 0
    architect_rag_low_confidence_citation_count = 0
    mel_rag_low_confidence_citation_count = 0
    fallback_namespace_citation_count = 0
    traceability_complete_citation_count = 0
    traceability_partial_citation_count = 0
    traceability_missing_citation_count = 0
    traceability_gap_citation_count = 0
    llm_finding_label_counts_total: Dict[str, int] = {}
    llm_advisory_diagnostics_job_count = 0
    llm_advisory_applied_job_count = 0
    llm_advisory_candidate_finding_count = 0
    llm_advisory_rejected_reason_counts: Dict[str, int] = {}

    for row in quality_rows:
        row_critic: Dict[str, Any] = (
            cast(Dict[str, Any], row.get("critic")) if isinstance(row.get("critic"), dict) else {}
        )
        row_citations: Dict[str, Any] = (
            cast(Dict[str, Any], row.get("citations")) if isinstance(row.get("citations"), dict) else {}
        )
        if bool(row.get("needs_revision")):
            needs_revision_job_count += 1
        critic_open_findings_total += int(row_critic.get("open_finding_count") or 0)
        critic_high_severity_total += int(row_critic.get("high_severity_fatal_flaw_count") or 0)
        critic_medium_severity_total += int(row_critic.get("medium_severity_fatal_flaw_count") or 0)
        critic_fatal_flaws_total += int(row_critic.get("fatal_flaw_count") or 0)
        for label, count in (
            (row_critic.get("llm_finding_label_counts") or {}).items()
            if isinstance(row_critic.get("llm_finding_label_counts"), dict)
            else []
        ):
            label_key = str(label).strip() or "GENERIC_LLM_REVIEW_FLAG"
            llm_finding_label_counts_total[label_key] = int(llm_finding_label_counts_total.get(label_key, 0)) + int(
                count or 0
            )
        row_llm_advisory = (
            cast(Dict[str, Any], row_critic.get("llm_advisory_diagnostics"))
            if isinstance(row_critic.get("llm_advisory_diagnostics"), dict)
            else {}
        )
        if row_llm_advisory:
            llm_advisory_diagnostics_job_count += 1
            llm_advisory_candidate_finding_count += int(row_llm_advisory.get("advisory_candidate_count") or 0)
            if bool(row_llm_advisory.get("advisory_applies")):
                llm_advisory_applied_job_count += 1
            else:
                rejected_reason = str(row_llm_advisory.get("advisory_rejected_reason") or "").strip()
                if rejected_reason:
                    llm_advisory_rejected_reason_counts[rejected_reason] = (
                        int(llm_advisory_rejected_reason_counts.get(rejected_reason, 0)) + 1
                    )
        citation_count_total += int(row_citations.get("citation_count") or 0)
        low_confidence_citation_count += int(row_citations.get("low_confidence_citation_count") or 0)
        rag_low_confidence_citation_count += int(row_citations.get("rag_low_confidence_citation_count") or 0)
        architect_rag_low_confidence_citation_count += int(
            row_citations.get("architect_rag_low_confidence_citation_count") or 0
        )
        mel_rag_low_confidence_citation_count += int(row_citations.get("mel_rag_low_confidence_citation_count") or 0)
        fallback_namespace_citation_count += int(row_citations.get("fallback_namespace_citation_count") or 0)
        traceability_complete_citation_count += int(row_citations.get("traceability_complete_citation_count") or 0)
        traceability_partial_citation_count += int(row_citations.get("traceability_partial_citation_count") or 0)
        traceability_missing_citation_count += int(row_citations.get("traceability_missing_citation_count") or 0)
        traceability_gap_citation_count += int(row_citations.get("traceability_gap_citation_count") or 0)

        donor_for_row = str(row.get("_donor_id") or "unknown")
        donor_row = donor_weighted_risk_breakdown.setdefault(
            donor_for_row,
            {
                "weighted_score": 0,
                "high_priority_signal_count": 0,
                "open_findings_total": 0,
                "high_severity_findings_total": 0,
                "needs_revision_job_count": 0,
                "citation_count_total": 0,
                "low_confidence_citation_count": 0,
                "rag_low_confidence_citation_count": 0,
                "architect_rag_low_confidence_citation_count": 0,
                "mel_rag_low_confidence_citation_count": 0,
                "fallback_namespace_citation_count": 0,
                "traceability_complete_citation_count": 0,
                "traceability_partial_citation_count": 0,
                "traceability_missing_citation_count": 0,
                "traceability_gap_citation_count": 0,
                "llm_finding_label_counts": {},
                "llm_advisory_applied_label_counts": {},
                "llm_advisory_rejected_label_counts": {},
                "llm_advisory_diagnostics_job_count": 0,
                "llm_advisory_applied_job_count": 0,
                "llm_advisory_candidate_finding_count": 0,
                "llm_advisory_rejected_reason_counts": {},
            },
        )
        donor_row["open_findings_total"] += int(row_critic.get("open_finding_count") or 0)
        donor_row["high_severity_findings_total"] += int(row_critic.get("high_severity_fatal_flaw_count") or 0)
        donor_row["citation_count_total"] += int(row_citations.get("citation_count") or 0)
        donor_row["low_confidence_citation_count"] += int(row_citations.get("low_confidence_citation_count") or 0)
        donor_row["rag_low_confidence_citation_count"] += int(
            row_citations.get("rag_low_confidence_citation_count") or 0
        )
        donor_row["architect_rag_low_confidence_citation_count"] += int(
            row_citations.get("architect_rag_low_confidence_citation_count") or 0
        )
        donor_row["mel_rag_low_confidence_citation_count"] += int(
            row_citations.get("mel_rag_low_confidence_citation_count") or 0
        )
        donor_row["fallback_namespace_citation_count"] += int(
            row_citations.get("fallback_namespace_citation_count") or 0
        )
        donor_row["traceability_complete_citation_count"] += int(
            row_citations.get("traceability_complete_citation_count") or 0
        )
        donor_row["traceability_partial_citation_count"] += int(
            row_citations.get("traceability_partial_citation_count") or 0
        )
        donor_row["traceability_missing_citation_count"] += int(
            row_citations.get("traceability_missing_citation_count") or 0
        )
        donor_row["traceability_gap_citation_count"] += int(row_citations.get("traceability_gap_citation_count") or 0)
        donor_label_counts = donor_row.get("llm_finding_label_counts")
        if not isinstance(donor_label_counts, dict):
            donor_label_counts = {}
            donor_row["llm_finding_label_counts"] = donor_label_counts
        for label, count in (
            (row_critic.get("llm_finding_label_counts") or {}).items()
            if isinstance(row_critic.get("llm_finding_label_counts"), dict)
            else []
        ):
            label_key = str(label).strip() or "GENERIC_LLM_REVIEW_FLAG"
            donor_label_counts[label_key] = int(donor_label_counts.get(label_key, 0)) + int(count or 0)
        donor_advisory_reasons = donor_row.get("llm_advisory_rejected_reason_counts")
        if not isinstance(donor_advisory_reasons, dict):
            donor_advisory_reasons = {}
            donor_row["llm_advisory_rejected_reason_counts"] = donor_advisory_reasons
        row_llm_advisory = (
            cast(Dict[str, Any], row_critic.get("llm_advisory_diagnostics"))
            if isinstance(row_critic.get("llm_advisory_diagnostics"), dict)
            else {}
        )
        if row_llm_advisory:
            donor_row["llm_advisory_diagnostics_job_count"] += 1
            donor_row["llm_advisory_candidate_finding_count"] += int(
                row_llm_advisory.get("advisory_candidate_count") or 0
            )
            donor_applied_label_counts = donor_row.get("llm_advisory_applied_label_counts")
            if not isinstance(donor_applied_label_counts, dict):
                donor_applied_label_counts = {}
                donor_row["llm_advisory_applied_label_counts"] = donor_applied_label_counts
            donor_rejected_label_counts = donor_row.get("llm_advisory_rejected_label_counts")
            if not isinstance(donor_rejected_label_counts, dict):
                donor_rejected_label_counts = {}
                donor_row["llm_advisory_rejected_label_counts"] = donor_rejected_label_counts
            candidate_label_counts = (
                cast(Dict[str, Any], row_llm_advisory.get("candidate_label_counts"))
                if isinstance(row_llm_advisory.get("candidate_label_counts"), dict)
                else {}
            )
            if bool(row_llm_advisory.get("advisory_applies")):
                donor_row["llm_advisory_applied_job_count"] += 1
                for label, count in candidate_label_counts.items():
                    label_key = str(label).strip() or "GENERIC_LLM_REVIEW_FLAG"
                    donor_applied_label_counts[label_key] = int(donor_applied_label_counts.get(label_key, 0)) + int(
                        count or 0
                    )
            else:
                for label, count in candidate_label_counts.items():
                    label_key = str(label).strip() or "GENERIC_LLM_REVIEW_FLAG"
                    donor_rejected_label_counts[label_key] = int(donor_rejected_label_counts.get(label_key, 0)) + int(
                        count or 0
                    )
        rejected_reason = str(row_llm_advisory.get("advisory_rejected_reason") or "").strip()
        if rejected_reason:
            donor_advisory_reasons[rejected_reason] = int(donor_advisory_reasons.get(rejected_reason, 0)) + 1
        if bool(row.get("needs_revision")):
            donor_row["needs_revision_job_count"] += 1

    signal_counts = {
        "high_severity_findings_total": critic_high_severity_total,
        "medium_severity_findings_total": critic_medium_severity_total,
        "open_findings_total": critic_open_findings_total,
        "needs_revision_job_count": needs_revision_job_count,
        "rag_low_confidence_citation_count": rag_low_confidence_citation_count,
        "traceability_gap_citation_count": traceability_gap_citation_count,
        "low_confidence_citation_count": low_confidence_citation_count,
    }
    priority_signal_breakdown: Dict[str, Dict[str, int]] = {}
    severity_weighted_risk_score = 0
    high_priority_signal_count = 0
    for signal, count in signal_counts.items():
        weight = int(PORTFOLIO_QUALITY_SIGNAL_WEIGHTS.get(signal, 1))
        weighted_score = int(count) * weight
        priority_signal_breakdown[signal] = {
            "count": int(count),
            "weight": weight,
            "weighted_score": weighted_score,
        }
        severity_weighted_risk_score += weighted_score
        if signal in PORTFOLIO_QUALITY_HIGH_PRIORITY_SIGNALS:
            high_priority_signal_count += int(count)

    donor_grounding_risk_counts: Dict[str, int] = {level: 0 for level in GROUNDING_RISK_LEVEL_ORDER}
    donor_grounding_risk_breakdown: Dict[str, Dict[str, Any]] = {}

    for donor_id, donor_row in donor_weighted_risk_breakdown.items():
        donor_row["weighted_score"] = (
            donor_row["high_severity_findings_total"] * PORTFOLIO_QUALITY_SIGNAL_WEIGHTS["high_severity_findings_total"]
            + donor_row["open_findings_total"] * PORTFOLIO_QUALITY_SIGNAL_WEIGHTS["open_findings_total"]
            + donor_row["needs_revision_job_count"] * PORTFOLIO_QUALITY_SIGNAL_WEIGHTS["needs_revision_job_count"]
            + donor_row["rag_low_confidence_citation_count"]
            * PORTFOLIO_QUALITY_SIGNAL_WEIGHTS["rag_low_confidence_citation_count"]
            + donor_row["traceability_gap_citation_count"]
            * PORTFOLIO_QUALITY_SIGNAL_WEIGHTS["traceability_gap_citation_count"]
            + donor_row["low_confidence_citation_count"]
            * PORTFOLIO_QUALITY_SIGNAL_WEIGHTS["low_confidence_citation_count"]
        )
        donor_row["high_priority_signal_count"] = (
            donor_row["high_severity_findings_total"]
            + donor_row["open_findings_total"]
            + donor_row["needs_revision_job_count"]
            + donor_row["rag_low_confidence_citation_count"]
            + donor_row["traceability_gap_citation_count"]
        )
        donor_diag_jobs = int(donor_row.get("llm_advisory_diagnostics_job_count") or 0)
        donor_applied_jobs = int(donor_row.get("llm_advisory_applied_job_count") or 0)
        donor_row["llm_advisory_applied_rate"] = (
            round(donor_applied_jobs / donor_diag_jobs, 4) if donor_diag_jobs else None
        )
        donor_citations_total = int(donor_row.get("citation_count_total") or 0)
        donor_fallback_total = int(donor_row.get("fallback_namespace_citation_count") or 0)
        donor_fallback_rate = round(donor_fallback_total / donor_citations_total, 4) if donor_citations_total else None
        donor_grounding_level = _grounding_risk_level(
            fallback_count=donor_fallback_total,
            citation_count=donor_citations_total,
        )
        donor_row["fallback_namespace_citation_rate"] = donor_fallback_rate
        donor_row["grounding_risk_level"] = donor_grounding_level
        donor_grounding_risk_counts[donor_grounding_level] = (
            int(donor_grounding_risk_counts.get(donor_grounding_level, 0)) + 1
        )
        donor_grounding_risk_breakdown[donor_id] = {
            "citation_count_total": donor_citations_total,
            "fallback_namespace_citation_count": donor_fallback_total,
            "fallback_namespace_citation_rate": donor_fallback_rate,
            "grounding_risk_level": donor_grounding_level,
        }

    job_count = len(filtered)
    warning_level_job_counts, warning_level_job_rates = _warning_level_breakdown(warning_level_counts, job_count)
    grounding_risk_job_counts, grounding_risk_job_rates = _grounding_risk_breakdown(grounding_risk_counts, job_count)
    quality_score_job_count = sum(1 for row in quality_rows if isinstance(row.get("quality_score"), (int, float)))
    critic_score_job_count = sum(1 for row in quality_rows if isinstance(row.get("critic_score"), (int, float)))

    citation_summary_rows: list[Dict[str, Any]] = [
        cast(Dict[str, Any], row.get("citations")) for row in quality_rows if isinstance(row.get("citations"), dict)
    ]
    fallback_namespace_citation_rate = (
        round(fallback_namespace_citation_count / citation_count_total, 4) if citation_count_total else None
    )
    grounding_risk_level = _grounding_risk_level(
        fallback_count=fallback_namespace_citation_count,
        citation_count=citation_count_total,
    )

    return {
        "job_count": job_count,
        "filters": {
            "donor_id": donor_id,
            "status": status,
            "hitl_enabled": hitl_enabled,
            "warning_level": warning_level_filter,
            "grounding_risk_level": grounding_risk_filter,
            "finding_status": finding_status_filter,
            "finding_severity": finding_severity_filter,
        },
        "status_counts": status_counts,
        "donor_counts": donor_counts,
        "warning_level_counts": warning_level_counts,
        "finding_status_counts": finding_status_counts,
        "finding_severity_counts": finding_severity_counts,
        "warning_level_job_counts": warning_level_job_counts,
        "warning_level_job_rates": warning_level_job_rates,
        "grounding_risk_counts": grounding_risk_counts,
        "grounding_risk_job_counts": grounding_risk_job_counts,
        "grounding_risk_job_rates": grounding_risk_job_rates,
        "grounding_risk_high_job_count": int(grounding_risk_job_counts.get("high") or 0),
        "grounding_risk_medium_job_count": int(grounding_risk_job_counts.get("medium") or 0),
        "grounding_risk_low_job_count": int(grounding_risk_job_counts.get("low") or 0),
        "grounding_risk_unknown_job_count": int(grounding_risk_job_counts.get("unknown") or 0),
        "warning_level_high_job_count": int(warning_level_job_counts.get("high") or 0),
        "warning_level_medium_job_count": int(warning_level_job_counts.get("medium") or 0),
        "warning_level_low_job_count": int(warning_level_job_counts.get("low") or 0),
        "warning_level_none_job_count": int(warning_level_job_counts.get("none") or 0),
        "warning_level_high_rate": (warning_level_job_rates.get("high")),
        "warning_level_medium_rate": (warning_level_job_rates.get("medium")),
        "warning_level_low_rate": (warning_level_job_rates.get("low")),
        "warning_level_none_rate": (warning_level_job_rates.get("none")),
        "donor_grounding_risk_counts": donor_grounding_risk_counts,
        "high_grounding_risk_donor_count": int(donor_grounding_risk_counts.get("high") or 0),
        "medium_grounding_risk_donor_count": int(donor_grounding_risk_counts.get("medium") or 0),
        "low_grounding_risk_donor_count": int(donor_grounding_risk_counts.get("low") or 0),
        "unknown_grounding_risk_donor_count": int(donor_grounding_risk_counts.get("unknown") or 0),
        "terminal_job_count": len(terminal_rows),
        "quality_score_job_count": quality_score_job_count,
        "critic_score_job_count": critic_score_job_count,
        "avg_quality_score": _avg(quality_rows, "quality_score"),
        "avg_critic_score": _avg(quality_rows, "critic_score"),
        "severity_weighted_risk_score": severity_weighted_risk_score,
        "high_priority_signal_count": high_priority_signal_count,
        "critic": {
            "open_findings_total": critic_open_findings_total,
            "open_findings_per_job_avg": round(critic_open_findings_total / job_count, 4) if job_count else None,
            "high_severity_findings_total": critic_high_severity_total,
            "fatal_flaws_total": critic_fatal_flaws_total,
            "needs_revision_job_count": needs_revision_job_count,
            "needs_revision_rate": round(needs_revision_job_count / job_count, 4) if job_count else None,
            "llm_finding_label_counts": llm_finding_label_counts_total,
            "llm_advisory_diagnostics_job_count": llm_advisory_diagnostics_job_count,
            "llm_advisory_applied_job_count": llm_advisory_applied_job_count,
            "llm_advisory_applied_rate": (
                round(llm_advisory_applied_job_count / llm_advisory_diagnostics_job_count, 4)
                if llm_advisory_diagnostics_job_count
                else None
            ),
            "llm_advisory_candidate_finding_count": llm_advisory_candidate_finding_count,
            "llm_advisory_rejected_reason_counts": llm_advisory_rejected_reason_counts,
        },
        "citations": {
            "citation_count_total": citation_count_total,
            "citation_confidence_avg": _avg(citation_summary_rows, "citation_confidence_avg"),
            "low_confidence_citation_count": low_confidence_citation_count,
            "low_confidence_citation_rate": (
                round(low_confidence_citation_count / citation_count_total, 4) if citation_count_total else None
            ),
            "rag_low_confidence_citation_count": rag_low_confidence_citation_count,
            "rag_low_confidence_citation_rate": (
                round(rag_low_confidence_citation_count / citation_count_total, 4) if citation_count_total else None
            ),
            "architect_rag_low_confidence_citation_count": architect_rag_low_confidence_citation_count,
            "architect_rag_low_confidence_citation_rate": (
                round(architect_rag_low_confidence_citation_count / citation_count_total, 4)
                if citation_count_total
                else None
            ),
            "mel_rag_low_confidence_citation_count": mel_rag_low_confidence_citation_count,
            "mel_rag_low_confidence_citation_rate": (
                round(mel_rag_low_confidence_citation_count / citation_count_total, 4) if citation_count_total else None
            ),
            "fallback_namespace_citation_count": fallback_namespace_citation_count,
            "fallback_namespace_citation_rate": fallback_namespace_citation_rate,
            "grounding_risk_level": grounding_risk_level,
            "traceability_complete_citation_count": traceability_complete_citation_count,
            "traceability_complete_citation_rate": (
                round(traceability_complete_citation_count / citation_count_total, 4) if citation_count_total else None
            ),
            "traceability_partial_citation_count": traceability_partial_citation_count,
            "traceability_partial_citation_rate": (
                round(traceability_partial_citation_count / citation_count_total, 4) if citation_count_total else None
            ),
            "traceability_missing_citation_count": traceability_missing_citation_count,
            "traceability_missing_citation_rate": (
                round(traceability_missing_citation_count / citation_count_total, 4) if citation_count_total else None
            ),
            "traceability_gap_citation_count": traceability_gap_citation_count,
            "traceability_gap_citation_rate": (
                round(traceability_gap_citation_count / citation_count_total, 4) if citation_count_total else None
            ),
            "architect_threshold_hit_rate_avg": _avg(citation_summary_rows, "architect_threshold_hit_rate"),
        },
        "priority_signal_breakdown": priority_signal_breakdown,
        "donor_weighted_risk_breakdown": donor_weighted_risk_breakdown,
        "donor_grounding_risk_breakdown": donor_grounding_risk_breakdown,
        "donor_needs_revision_counts": donor_needs_revision_counts,
        "donor_open_findings_counts": donor_open_findings_counts,
    }


def public_portfolio_quality_csv_text(payload: Dict[str, Any]) -> str:
    return csv_text_from_mapping(payload)


def public_portfolio_metrics_csv_text(payload: Dict[str, Any]) -> str:
    return csv_text_from_mapping(payload)


def public_ingest_inventory_csv_text(payload: Dict[str, Any]) -> str:
    return csv_text_from_mapping(payload)


def public_job_review_workflow_csv_text(payload: Dict[str, Any]) -> str:
    return csv_text_from_mapping(payload)


def public_checkpoint_payload(checkpoint: Dict[str, Any]) -> Dict[str, Any]:
    public_checkpoint: Dict[str, Any] = {}
    for key, value in checkpoint.items():
        if key == "state_snapshot":
            continue
        public_checkpoint[str(key)] = sanitize_for_public_response(value)
    public_checkpoint["has_state_snapshot"] = "state_snapshot" in checkpoint
    return public_checkpoint
