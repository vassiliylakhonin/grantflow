from __future__ import annotations

import difflib
import json
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, Optional, cast

from grantflow.api.csv_utils import csv_text_from_mapping
from grantflow.core.config import config
from grantflow.exporters.donor_contracts import evaluate_export_contract_gate, normalize_export_contract_policy_mode
from grantflow.swarm.citations import (
    citation_has_doc_id,
    citation_has_retrieval_confidence,
    citation_has_retrieval_metadata,
    citation_has_retrieval_rank,
    citation_traceability_status,
    is_fallback_namespace_citation_type,
    is_non_retrieval_citation_type,
    is_retrieval_grounded_citation_type,
    is_strategy_reference_citation_type,
)
from grantflow.swarm.findings import finding_messages, finding_primary_id, state_critic_findings
from grantflow.swarm.state_contract import normalized_state_copy, state_donor_id

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
TOC_TEXT_RISK_LEVEL_ORDER = ("high", "medium", "low", "unknown")
TOC_TEXT_RISK_LEVELS = set(TOC_TEXT_RISK_LEVEL_ORDER)
FINDING_STATUS_FILTER_VALUES = {"open", "acknowledged", "resolved"}
FINDING_SEVERITY_FILTER_VALUES = {"high", "medium", "low"}
REVIEW_WORKFLOW_EVENT_TYPES = {
    "critic_finding_status_changed",
    "review_comment_added",
    "review_comment_status_changed",
    "hitl_checkpoint_decision",
}
REVIEW_WORKFLOW_STATE_FILTER_VALUES = {"pending", "overdue"}
REVIEW_WORKFLOW_OVERDUE_DEFAULT_HOURS = 48
GROUNDING_FALLBACK_HIGH_THRESHOLD = 0.8
GROUNDING_FALLBACK_MEDIUM_THRESHOLD = 0.5
GROUNDING_NON_RETRIEVAL_HIGH_THRESHOLD = 0.8
GROUNDING_NON_RETRIEVAL_MEDIUM_THRESHOLD = 0.5
GROUNDED_GATE_SECTION_ORDER = ("toc", "logframe", "general")
MEL_PLACEHOLDER_VALUES = {
    "",
    "tbd",
    "to be determined",
    "placeholder",
    "n/a",
    "na",
    "unknown",
    "-",
    "--",
    "none",
    "null",
}
MEL_COVERAGE_FIELDS = (
    "baseline",
    "target",
    "frequency",
    "formula",
    "definition",
    "data_source",
    "disaggregation",
    "result_level",
)
MEL_SMART_COVERAGE_FIELDS = (
    "baseline",
    "target",
    "frequency",
    "formula",
    "definition",
    "data_source",
    "result_level",
)


def _job_state_dict(job: Dict[str, Any]) -> Dict[str, Any]:
    state = job.get("state") if isinstance(job.get("state"), dict) else {}
    return dict(normalized_state_copy(state))


def _coerce_int(value: Any, default: int = 0) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _state_export_contract_gate(state_dict: Dict[str, Any]) -> Dict[str, Any]:
    raw_gate = state_dict.get("export_contract_gate")
    if isinstance(raw_gate, dict):
        return raw_gate

    donor_id = state_donor_id(state_dict, default="grantflow")
    raw_toc = state_dict.get("toc_draft")
    toc_payload = raw_toc if isinstance(raw_toc, dict) else {}
    if not toc_payload:
        raw_toc_fallback = state_dict.get("toc")
        if isinstance(raw_toc_fallback, dict):
            toc_payload = raw_toc_fallback
    mode_raw = getattr(config.graph, "export_contract_policy_mode", None)
    if not str(mode_raw or "").strip():
        mode_raw = getattr(config.graph, "export_grounding_policy_mode", "warn")
    mode = normalize_export_contract_policy_mode(mode_raw)
    return evaluate_export_contract_gate(
        donor_id=donor_id,
        toc_payload=toc_payload,
        policy_mode=mode,
    )


def _job_donor_id(job: Dict[str, Any], *, default: str = "") -> str:
    donor_id = state_donor_id(_job_state_dict(job), default="")
    if donor_id:
        return donor_id
    metadata_raw = job.get("client_metadata")
    metadata: Dict[str, Any] = metadata_raw if isinstance(metadata_raw, dict) else {}
    token = str(metadata.get("donor_id") or metadata.get("donor") or "").strip().lower()
    return token or default


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


def _normalize_toc_text_risk_filter(toc_text_risk_level: Optional[str]) -> Optional[str]:
    if toc_text_risk_level is None:
        return None
    token = str(toc_text_risk_level or "").strip().lower()
    if not token:
        return None
    if token not in TOC_TEXT_RISK_LEVELS:
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


def _grounding_risk_level(
    *,
    fallback_count: int,
    citation_count: int,
    strategy_reference_count: int = 0,
    retrieval_grounded_count: int = 0,
    retrieval_expected: bool = True,
) -> str:
    if citation_count <= 0:
        return "unknown"
    if retrieval_expected:
        non_retrieval_rate = (fallback_count + strategy_reference_count) / citation_count
        if non_retrieval_rate >= GROUNDING_NON_RETRIEVAL_HIGH_THRESHOLD:
            return "high"
        if non_retrieval_rate >= GROUNDING_NON_RETRIEVAL_MEDIUM_THRESHOLD:
            return "medium"
        if retrieval_grounded_count <= 0:
            return "medium"
        return "low"
    fallback_rate = fallback_count / citation_count
    if fallback_rate >= GROUNDING_FALLBACK_HIGH_THRESHOLD:
        return "high"
    if fallback_rate >= GROUNDING_FALLBACK_MEDIUM_THRESHOLD:
        return "medium"
    return "low"


def _state_retrieval_expected(state_dict: Dict[str, Any]) -> bool:
    architect_retrieval = state_dict.get("architect_retrieval")
    if isinstance(architect_retrieval, dict) and isinstance(architect_retrieval.get("enabled"), bool):
        return bool(architect_retrieval.get("enabled"))
    raw = state_dict.get("architect_rag_enabled")
    if isinstance(raw, bool):
        return raw
    return True


def _citation_grounding_counts(citations: list[Dict[str, Any]]) -> Dict[str, int]:
    fallback_count = 0
    strategy_reference_count = 0
    retrieval_grounded_count = 0
    non_retrieval_count = 0
    for item in citations:
        if not isinstance(item, dict):
            continue
        citation_type = item.get("citation_type")
        if is_fallback_namespace_citation_type(citation_type):
            fallback_count += 1
        if is_strategy_reference_citation_type(citation_type):
            strategy_reference_count += 1
        if is_retrieval_grounded_citation_type(citation_type):
            retrieval_grounded_count += 1
        if is_non_retrieval_citation_type(citation_type):
            non_retrieval_count += 1
    return {
        "fallback_namespace_citation_count": fallback_count,
        "strategy_reference_citation_count": strategy_reference_count,
        "retrieval_grounded_citation_count": retrieval_grounded_count,
        "non_retrieval_citation_count": non_retrieval_count,
    }


def _citation_retrieval_metadata_counts(citations: list[Dict[str, Any]]) -> Dict[str, int]:
    doc_id_present_count = 0
    retrieval_rank_present_count = 0
    retrieval_confidence_present_count = 0
    retrieval_metadata_complete_count = 0
    for item in citations:
        if not isinstance(item, dict):
            continue
        has_doc_id = citation_has_doc_id(item)
        has_retrieval_rank = citation_has_retrieval_rank(item)
        has_retrieval_confidence = citation_has_retrieval_confidence(item)
        if has_doc_id:
            doc_id_present_count += 1
        if has_retrieval_rank:
            retrieval_rank_present_count += 1
        if has_retrieval_confidence:
            retrieval_confidence_present_count += 1
        if citation_has_retrieval_metadata(item):
            retrieval_metadata_complete_count += 1
    return {
        "doc_id_present_citation_count": doc_id_present_count,
        "retrieval_rank_present_citation_count": retrieval_rank_present_count,
        "retrieval_confidence_present_citation_count": retrieval_confidence_present_count,
        "retrieval_metadata_complete_citation_count": retrieval_metadata_complete_count,
    }


def _citation_type_counts(citations: list[Dict[str, Any]]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for item in citations:
        if not isinstance(item, dict):
            continue
        token = str(item.get("citation_type") or "").strip().lower() or "unknown"
        counts[token] = int(counts.get(token, 0)) + 1
    return dict(sorted(counts.items()))


def _is_claim_support_citation_type(citation_type: Any) -> bool:
    token = str(citation_type or "").strip().lower()
    return token in {"rag_result", "rag_support", "rag_claim_support"}


def _job_grounding_risk_level(job: Dict[str, Any]) -> str:
    state = job.get("state")
    state_dict = state if isinstance(state, dict) else {}
    citations = state_dict.get("citations")
    citations_list = [item for item in citations if isinstance(item, dict)] if isinstance(citations, list) else []
    citation_count = len(citations_list)
    grounding_counts = _citation_grounding_counts(citations_list)
    return _grounding_risk_level(
        fallback_count=int(grounding_counts.get("fallback_namespace_citation_count") or 0),
        strategy_reference_count=int(grounding_counts.get("strategy_reference_citation_count") or 0),
        retrieval_grounded_count=int(grounding_counts.get("retrieval_grounded_citation_count") or 0),
        citation_count=citation_count,
        retrieval_expected=_state_retrieval_expected(state_dict),
    )


def _job_critic_findings(job: Dict[str, Any]) -> list[Dict[str, Any]]:
    state = job.get("state")
    state_dict = state if isinstance(state, dict) else {}
    return [dict(item) for item in state_critic_findings(state_dict, default_source="rules")]


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
        if key in {
            "webhook_url",
            "webhook_secret",
            "job_events",
            "review_comments",
            "client_metadata",
            "idempotency_records",
        }:
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
    finding_code: Optional[str] = None,
    finding_section: Optional[str] = None,
    comment_status: Optional[str] = None,
    workflow_state: Optional[str] = None,
    overdue_after_hours: int = REVIEW_WORKFLOW_OVERDUE_DEFAULT_HOURS,
) -> Dict[str, Any]:
    event_type_filter = str(event_type or "").strip() or None
    finding_id_filter = str(finding_id or "").strip() or None
    finding_code_filter = str(finding_code or "").strip().upper() or None
    finding_section_filter = str(finding_section or "").strip().lower() or None
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
    if finding_code_filter:
        findings_list = [
            item for item in findings_list if str(item.get("code") or "").strip().upper() == finding_code_filter
        ]
    if finding_section_filter:
        findings_list = [
            item
            for item in findings_list
            if str(item.get("section") or "").strip().lower() == finding_section_filter
            or (
                isinstance(item.get("related_sections"), list)
                and finding_section_filter
                in {
                    str(section or "").strip().lower()
                    for section in cast(list[Any], item.get("related_sections"))
                    if str(section or "").strip()
                }
            )
        ]
    filtered_finding_ids = {finding_primary_id(item) for item in findings_list if finding_primary_id(item)}

    comments_payload = public_job_comments_payload(job_id, job)
    comments = comments_payload.get("comments") if isinstance(comments_payload, dict) else []
    comments_list = [item for item in comments if isinstance(item, dict)] if isinstance(comments, list) else []
    if finding_id_filter:
        comments_list = [
            item for item in comments_list if str(item.get("linked_finding_id") or "") == finding_id_filter
        ]
    if finding_code_filter:
        comments_list = [
            item for item in comments_list if str(item.get("linked_finding_id") or "").strip() in filtered_finding_ids
        ]
    if finding_section_filter:
        comments_list = [
            item
            for item in comments_list
            if str(item.get("section") or "").strip().lower() == finding_section_filter
            or str(item.get("linked_finding_id") or "").strip() in filtered_finding_ids
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
                        else (
                            "comment_added"
                            if event_type == "review_comment_added"
                            else ("hitl_decision" if event_type == "hitl_checkpoint_decision" else "comment_status")
                        )
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
        finding_age_hours: Optional[float] = None
        if unresolved and reference_ts is not None and last_transition_dt is not None:
            finding_age_hours = max(0.0, (reference_ts - last_transition_dt).total_seconds() / 3600.0)
        if unresolved and reference_ts is not None and effective_due_dt is not None:
            is_overdue = reference_ts >= effective_due_dt
        else:
            is_overdue = bool(
                unresolved and finding_age_hours is not None and finding_age_hours >= float(overdue_after_hours_value)
            )
        finding_time_to_due_hours: Optional[float] = None
        if unresolved and reference_ts is not None and effective_due_dt is not None:
            finding_time_to_due_hours = (effective_due_dt - reference_ts).total_seconds() / 3600.0
        if status == "resolved":
            current["workflow_state"] = "resolved"
        elif is_overdue:
            current["workflow_state"] = "overdue"
        else:
            current["workflow_state"] = "pending"
        current["is_overdue"] = is_overdue
        current["age_hours"] = round(finding_age_hours, 3) if finding_age_hours is not None else None
        current["time_to_due_hours"] = (
            round(finding_time_to_due_hours, 3) if finding_time_to_due_hours is not None else None
        )
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
        comment_age_hours: Optional[float] = None
        if unresolved and reference_ts is not None and last_transition_dt is not None:
            comment_age_hours = max(0.0, (reference_ts - last_transition_dt).total_seconds() / 3600.0)
        if unresolved and reference_ts is not None and effective_due_dt is not None:
            is_overdue = reference_ts >= effective_due_dt
        else:
            is_overdue = bool(
                unresolved and comment_age_hours is not None and comment_age_hours >= float(overdue_after_hours_value)
            )
        comment_time_to_due_hours: Optional[float] = None
        if unresolved and reference_ts is not None and effective_due_dt is not None:
            comment_time_to_due_hours = (effective_due_dt - reference_ts).total_seconds() / 3600.0
        if status == "resolved":
            current["workflow_state"] = "resolved"
        elif is_overdue:
            current["workflow_state"] = "overdue"
        else:
            current["workflow_state"] = "pending"
        current["is_overdue"] = is_overdue
        current["age_hours"] = round(comment_age_hours, 3) if comment_age_hours is not None else None
        current["time_to_due_hours"] = (
            round(comment_time_to_due_hours, 3) if comment_time_to_due_hours is not None else None
        )
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
    if finding_code_filter:
        timeline = [
            row
            for row in timeline
            if str(row.get("finding_id") or "").strip() in finding_ids
            or str(row.get("comment_id") or "").strip() in comment_ids
        ]
    if finding_section_filter:
        timeline = [
            row
            for row in timeline
            if str(row.get("section") or "").strip().lower() == finding_section_filter
            or str(row.get("finding_id") or "").strip() in finding_ids
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
            "finding_code": finding_code_filter,
            "finding_section": finding_section_filter,
            "comment_status": comment_status_filter,
            "workflow_state": workflow_state_filter,
            "overdue_after_hours": overdue_after_hours_value,
        },
        "summary": summary,
        "findings": findings_with_workflow,
        "comments": comments_with_workflow,
        "timeline": timeline,
    }


def public_job_review_workflow_trends_payload(
    job_id: str,
    job: Dict[str, Any],
    *,
    event_type: Optional[str] = None,
    finding_id: Optional[str] = None,
    finding_code: Optional[str] = None,
    finding_section: Optional[str] = None,
    comment_status: Optional[str] = None,
    workflow_state: Optional[str] = None,
    overdue_after_hours: int = REVIEW_WORKFLOW_OVERDUE_DEFAULT_HOURS,
) -> Dict[str, Any]:
    workflow_payload = public_job_review_workflow_payload(
        job_id,
        job,
        event_type=event_type,
        finding_id=finding_id,
        finding_code=finding_code,
        finding_section=finding_section,
        comment_status=comment_status,
        workflow_state=workflow_state,
        overdue_after_hours=overdue_after_hours,
    )
    timeline = workflow_payload.get("timeline")
    timeline_rows = [row for row in timeline if isinstance(row, dict)] if isinstance(timeline, list) else []
    filters = workflow_payload.get("filters")
    filters_dict = filters if isinstance(filters, dict) else {}

    total_bucket_counts: Dict[str, int] = {}
    event_type_bucket_counts: Dict[str, Dict[str, int]] = {}
    kind_bucket_counts: Dict[str, Dict[str, int]] = {}
    section_bucket_counts: Dict[str, Dict[str, int]] = {}
    status_bucket_counts: Dict[str, Dict[str, int]] = {}

    for row in timeline_rows:
        ts_dt = _parse_event_ts(row.get("ts"))
        bucket = ts_dt.date().isoformat() if ts_dt is not None else "unknown"
        total_bucket_counts[bucket] = int(total_bucket_counts.get(bucket) or 0) + 1

        event_type_key = str(row.get("type") or "").strip().lower() or "unknown"
        event_type_counts = event_type_bucket_counts.setdefault(event_type_key, {})
        event_type_counts[bucket] = int(event_type_counts.get(bucket) or 0) + 1

        kind_key = str(row.get("kind") or "").strip().lower() or "unknown"
        kind_counts = kind_bucket_counts.setdefault(kind_key, {})
        kind_counts[bucket] = int(kind_counts.get(bucket) or 0) + 1

        section_key = str(row.get("section") or "").strip().lower() or "unknown"
        section_counts = section_bucket_counts.setdefault(section_key, {})
        section_counts[bucket] = int(section_counts.get(bucket) or 0) + 1

        status_key = str(row.get("status") or "").strip().lower() or "unknown"
        status_counts = status_bucket_counts.setdefault(status_key, {})
        status_counts[bucket] = int(status_counts.get(bucket) or 0) + 1

    def _series_rows(counts: Dict[str, int]) -> list[Dict[str, Any]]:
        return [{"bucket": bucket, "count": int(counts.get(bucket) or 0)} for bucket in sorted(counts.keys())]

    total_series = _series_rows(total_bucket_counts)
    event_type_series = {
        key: _series_rows(event_type_bucket_counts.get(key, {})) for key in sorted(event_type_bucket_counts.keys())
    }
    kind_series = {key: _series_rows(kind_bucket_counts.get(key, {})) for key in sorted(kind_bucket_counts.keys())}
    section_series = {
        key: _series_rows(section_bucket_counts.get(key, {})) for key in sorted(section_bucket_counts.keys())
    }
    status_series = {
        key: _series_rows(status_bucket_counts.get(key, {})) for key in sorted(status_bucket_counts.keys())
    }

    dated_buckets = []
    for point in total_series:
        bucket = str(point.get("bucket") or "").strip()
        try:
            datetime.strptime(bucket, "%Y-%m-%d")
            dated_buckets.append(bucket)
        except ValueError:
            continue
    time_window_start = dated_buckets[0] if dated_buckets else None
    time_window_end = dated_buckets[-1] if dated_buckets else None

    top_event_type = None
    top_event_type_count = -1
    for key, rows in event_type_series.items():
        total = sum(int(row.get("count") or 0) for row in rows if isinstance(row, dict))
        if total > top_event_type_count:
            top_event_type = key
            top_event_type_count = total

    summary = workflow_payload.get("summary")
    summary_dict = summary if isinstance(summary, dict) else {}
    timeline_event_count = _coerce_int(summary_dict.get("timeline_event_count"), default=len(timeline_rows))

    return {
        "job_id": str(job_id),
        "status": str(job.get("status") or ""),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "filters": filters_dict,
        "bucket_granularity": "day",
        "bucket_count": len(total_series),
        "time_window_start": time_window_start,
        "time_window_end": time_window_end,
        "timeline_event_count": timeline_event_count,
        "top_event_type": top_event_type,
        "top_event_type_count": top_event_type_count if top_event_type is not None else None,
        "total_series": total_series,
        "event_type_series": event_type_series,
        "kind_series": kind_series,
        "section_series": section_series,
        "status_series": status_series,
    }


def _review_workflow_sla_snapshot(
    job_id: str,
    job: Dict[str, Any],
    *,
    finding_id: Optional[str] = None,
    finding_code: Optional[str] = None,
    finding_section: Optional[str] = None,
    comment_status: Optional[str] = None,
    workflow_state: Optional[str] = None,
    overdue_after_hours: int = REVIEW_WORKFLOW_OVERDUE_DEFAULT_HOURS,
) -> Dict[str, Any]:
    workflow_payload = public_job_review_workflow_payload(
        job_id,
        job,
        finding_id=finding_id,
        finding_code=finding_code,
        finding_section=finding_section,
        comment_status=comment_status,
        workflow_state=workflow_state,
        overdue_after_hours=overdue_after_hours,
    )
    findings = workflow_payload.get("findings")
    comments = workflow_payload.get("comments")
    findings_list = [item for item in findings if isinstance(item, dict)] if isinstance(findings, list) else []
    comments_list = [item for item in comments if isinstance(item, dict)] if isinstance(comments, list) else []

    summary = workflow_payload.get("summary")
    summary_dict = summary if isinstance(summary, dict) else {}
    reference_ts = _parse_event_ts(summary_dict.get("last_activity_at"))
    workflow_filters = workflow_payload.get("filters")
    workflow_filters_dict = workflow_filters if isinstance(workflow_filters, dict) else {}
    overdue_after_hours_value = _coerce_int(
        workflow_filters_dict.get("overdue_after_hours"),
        default=_coerce_int(overdue_after_hours, default=REVIEW_WORKFLOW_OVERDUE_DEFAULT_HOURS),
    )
    if overdue_after_hours_value <= 0:
        overdue_after_hours_value = REVIEW_WORKFLOW_OVERDUE_DEFAULT_HOURS
    sla_filters = {
        "finding_id": str(workflow_filters_dict.get("finding_id") or "").strip() or None,
        "finding_code": str(workflow_filters_dict.get("finding_code") or "").strip() or None,
        "finding_section": str(workflow_filters_dict.get("finding_section") or "").strip() or None,
        "comment_status": str(workflow_filters_dict.get("comment_status") or "").strip() or None,
        "workflow_state": str(workflow_filters_dict.get("workflow_state") or "").strip() or None,
        "overdue_after_hours": overdue_after_hours_value,
    }

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
        overdue_hours_value = -1.0
        if isinstance(overdue_hours, (int, float, str)):
            try:
                overdue_hours_value = float(overdue_hours)
            except (TypeError, ValueError):
                overdue_hours_value = -1.0
        due_at = str(item.get("due_at") or "")
        return overdue_hours_value, due_at

    overdue_rows.sort(key=_sort_key, reverse=True)

    unresolved_total = unresolved_finding_count + unresolved_comment_count
    overdue_total = overdue_finding_count + overdue_comment_count
    breach_rate = (overdue_total / unresolved_total) if unresolved_total else None

    return {
        "job_id": str(job_id),
        "status": str(job.get("status") or ""),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "filters": sla_filters,
        "overdue_after_hours": overdue_after_hours_value,
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
        "workflow_summary": summary_dict,
        "overdue_rows": overdue_rows,
    }


def public_job_review_workflow_sla_payload(
    job_id: str,
    job: Dict[str, Any],
    *,
    finding_id: Optional[str] = None,
    finding_code: Optional[str] = None,
    finding_section: Optional[str] = None,
    comment_status: Optional[str] = None,
    workflow_state: Optional[str] = None,
    overdue_after_hours: int = REVIEW_WORKFLOW_OVERDUE_DEFAULT_HOURS,
    top_limit: int = 5,
) -> Dict[str, Any]:
    snapshot = _review_workflow_sla_snapshot(
        job_id,
        job,
        finding_id=finding_id,
        finding_code=finding_code,
        finding_section=finding_section,
        comment_status=comment_status,
        workflow_state=workflow_state,
        overdue_after_hours=overdue_after_hours,
    )
    overdue_rows = snapshot.pop("overdue_rows", [])
    overdue_rows_list = (
        [item for item in overdue_rows if isinstance(item, dict)] if isinstance(overdue_rows, list) else []
    )
    top_n = max(1, int(top_limit))
    top_overdue = overdue_rows_list[:top_n]
    oldest_overdue = top_overdue[0] if top_overdue else None
    return {
        **snapshot,
        "oldest_overdue": oldest_overdue,
        "top_overdue": top_overdue,
    }


def public_job_review_workflow_sla_trends_payload(
    job_id: str,
    job: Dict[str, Any],
    *,
    finding_id: Optional[str] = None,
    finding_code: Optional[str] = None,
    finding_section: Optional[str] = None,
    comment_status: Optional[str] = None,
    workflow_state: Optional[str] = None,
    overdue_after_hours: int = REVIEW_WORKFLOW_OVERDUE_DEFAULT_HOURS,
) -> Dict[str, Any]:
    snapshot = _review_workflow_sla_snapshot(
        job_id,
        job,
        finding_id=finding_id,
        finding_code=finding_code,
        finding_section=finding_section,
        comment_status=comment_status,
        workflow_state=workflow_state,
        overdue_after_hours=overdue_after_hours,
    )
    overdue_rows = snapshot.pop("overdue_rows", [])
    overdue_rows_list = (
        [item for item in overdue_rows if isinstance(item, dict)] if isinstance(overdue_rows, list) else []
    )

    total_bucket_counts: Dict[str, int] = {}
    severity_bucket_counts: Dict[str, Dict[str, int]] = {}
    section_bucket_counts: Dict[str, Dict[str, int]] = {}

    for row in overdue_rows_list:
        due_dt = _parse_event_ts(row.get("due_at"))
        bucket = due_dt.date().isoformat() if due_dt is not None else "unknown"
        total_bucket_counts[bucket] = int(total_bucket_counts.get(bucket) or 0) + 1

        severity = str(row.get("severity") or "").strip().lower() or "unknown"
        severity_counts = severity_bucket_counts.setdefault(severity, {})
        severity_counts[bucket] = int(severity_counts.get(bucket) or 0) + 1

        section = str(row.get("section") or "").strip().lower() or "unknown"
        section_counts = section_bucket_counts.setdefault(section, {})
        section_counts[bucket] = int(section_counts.get(bucket) or 0) + 1

    def _series_rows(counts: Dict[str, int]) -> list[Dict[str, Any]]:
        return [{"bucket": bucket, "count": int(counts.get(bucket) or 0)} for bucket in sorted(counts.keys())]

    total_series = _series_rows(total_bucket_counts)
    severity_series: Dict[str, list[Dict[str, Any]]] = {}
    for level in ("high", "medium", "low", "unknown"):
        severity_series[level] = _series_rows(severity_bucket_counts.get(level, {}))
    for level in sorted(severity_bucket_counts.keys()):
        if level in severity_series:
            continue
        severity_series[level] = _series_rows(severity_bucket_counts.get(level, {}))

    section_series: Dict[str, list[Dict[str, Any]]] = {}
    for section in sorted(section_bucket_counts.keys()):
        section_series[section] = _series_rows(section_bucket_counts.get(section, {}))

    dated_buckets = []
    for point in total_series:
        bucket = str(point.get("bucket") or "").strip()
        try:
            datetime.strptime(bucket, "%Y-%m-%d")
            dated_buckets.append(bucket)
        except ValueError:
            continue
    time_window_start = dated_buckets[0] if dated_buckets else None
    time_window_end = dated_buckets[-1] if dated_buckets else None

    return {
        **snapshot,
        "bucket_granularity": "day",
        "bucket_count": len(total_series),
        "time_window_start": time_window_start,
        "time_window_end": time_window_end,
        "total_series": total_series,
        "severity_series": severity_series,
        "section_series": section_series,
    }


def public_job_review_workflow_sla_hotspots_payload(
    job_id: str,
    job: Dict[str, Any],
    *,
    finding_id: Optional[str] = None,
    finding_code: Optional[str] = None,
    finding_section: Optional[str] = None,
    comment_status: Optional[str] = None,
    workflow_state: Optional[str] = None,
    overdue_after_hours: int = REVIEW_WORKFLOW_OVERDUE_DEFAULT_HOURS,
    top_limit: int = 10,
    hotspot_kind: Optional[str] = None,
    hotspot_severity: Optional[str] = None,
    min_overdue_hours: Optional[float] = None,
) -> Dict[str, Any]:
    snapshot = _review_workflow_sla_snapshot(
        job_id,
        job,
        finding_id=finding_id,
        finding_code=finding_code,
        finding_section=finding_section,
        comment_status=comment_status,
        workflow_state=workflow_state,
        overdue_after_hours=overdue_after_hours,
    )
    overdue_rows = snapshot.pop("overdue_rows", [])
    overdue_rows_list = (
        [item for item in overdue_rows if isinstance(item, dict)] if isinstance(overdue_rows, list) else []
    )
    hotspot_kind_filter = str(hotspot_kind or "").strip().lower() or None
    if hotspot_kind_filter not in {None, "finding", "comment"}:
        hotspot_kind_filter = None
    hotspot_severity_filter = str(hotspot_severity or "").strip().lower() or None
    if hotspot_severity_filter not in {None, "high", "medium", "low", "unknown"}:
        hotspot_severity_filter = None
    min_overdue_filter = None
    if isinstance(min_overdue_hours, (int, float)):
        min_overdue_filter = max(0.0, float(min_overdue_hours))

    filtered_rows: list[Dict[str, Any]] = []
    hotspot_kind_counts: Dict[str, int] = {}
    hotspot_severity_counts: Dict[str, int] = {}
    hotspot_section_counts: Dict[str, int] = {}
    overdue_values: list[float] = []

    for row in overdue_rows_list:
        row_kind = str(row.get("kind") or "").strip().lower()
        row_severity = str(row.get("severity") or "").strip().lower() or "unknown"
        row_section = str(row.get("section") or "").strip().lower() or "unknown"
        overdue_value_raw = row.get("overdue_hours")
        try:
            overdue_value = float(overdue_value_raw) if overdue_value_raw is not None else None
        except (TypeError, ValueError):
            overdue_value = None

        if hotspot_kind_filter and row_kind != hotspot_kind_filter:
            continue
        if hotspot_severity_filter and row_severity != hotspot_severity_filter:
            continue
        if min_overdue_filter is not None and (overdue_value is None or overdue_value < min_overdue_filter):
            continue

        current = dict(row)
        current["kind"] = row_kind
        current["severity"] = row_severity
        current["section"] = row_section
        if overdue_value is not None:
            current["overdue_hours"] = round(overdue_value, 3)
            overdue_values.append(overdue_value)
        else:
            current["overdue_hours"] = None
        filtered_rows.append(current)
        hotspot_kind_counts[row_kind or "unknown"] = int(hotspot_kind_counts.get(row_kind or "unknown") or 0) + 1
        hotspot_severity_counts[row_severity] = int(hotspot_severity_counts.get(row_severity) or 0) + 1
        hotspot_section_counts[row_section] = int(hotspot_section_counts.get(row_section) or 0) + 1

    filtered_rows.sort(
        key=lambda item: (
            float(item.get("overdue_hours") or -1.0),
            str(item.get("due_at") or ""),
            str(item.get("id") or ""),
        ),
        reverse=True,
    )

    top_n = max(1, int(top_limit))
    top_overdue = filtered_rows[:top_n]
    oldest_overdue = top_overdue[0] if top_overdue else None
    filters = snapshot.get("filters")
    filters_dict = dict(filters) if isinstance(filters, dict) else {}
    filters_dict.update(
        {
            "top_limit": top_n,
            "hotspot_kind": hotspot_kind_filter,
            "hotspot_severity": hotspot_severity_filter,
            "min_overdue_hours": min_overdue_filter,
        }
    )
    return {
        **snapshot,
        "filters": filters_dict,
        "top_limit": top_n,
        "hotspot_count": len(top_overdue),
        "total_overdue_items": len(filtered_rows),
        "max_overdue_hours": round(max(overdue_values), 3) if overdue_values else None,
        "avg_overdue_hours": (round(sum(overdue_values) / len(overdue_values), 3) if overdue_values else None),
        "hotspot_kind_counts": dict(sorted(hotspot_kind_counts.items())),
        "hotspot_severity_counts": dict(sorted(hotspot_severity_counts.items())),
        "hotspot_section_counts": dict(sorted(hotspot_section_counts.items())),
        "oldest_overdue": oldest_overdue,
        "top_overdue": top_overdue,
    }


def public_job_review_workflow_sla_hotspots_trends_payload(
    job_id: str,
    job: Dict[str, Any],
    *,
    finding_id: Optional[str] = None,
    finding_code: Optional[str] = None,
    finding_section: Optional[str] = None,
    comment_status: Optional[str] = None,
    workflow_state: Optional[str] = None,
    overdue_after_hours: int = REVIEW_WORKFLOW_OVERDUE_DEFAULT_HOURS,
    top_limit: int = 10,
    hotspot_kind: Optional[str] = None,
    hotspot_severity: Optional[str] = None,
    min_overdue_hours: Optional[float] = None,
) -> Dict[str, Any]:
    hotspots_payload = public_job_review_workflow_sla_hotspots_payload(
        job_id,
        job,
        finding_id=finding_id,
        finding_code=finding_code,
        finding_section=finding_section,
        comment_status=comment_status,
        workflow_state=workflow_state,
        overdue_after_hours=overdue_after_hours,
        top_limit=top_limit,
        hotspot_kind=hotspot_kind,
        hotspot_severity=hotspot_severity,
        min_overdue_hours=min_overdue_hours,
    )
    rows = hotspots_payload.get("top_overdue")
    filtered_top_rows = [item for item in rows if isinstance(item, dict)] if isinstance(rows, list) else []
    source_total = hotspots_payload.get("total_overdue_items")
    total_hotspots = _coerce_int(source_total, default=len(filtered_top_rows))
    snapshot = _review_workflow_sla_snapshot(
        job_id,
        job,
        finding_id=finding_id,
        finding_code=finding_code,
        finding_section=finding_section,
        comment_status=comment_status,
        workflow_state=workflow_state,
        overdue_after_hours=overdue_after_hours,
    )
    all_rows = snapshot.pop("overdue_rows", [])
    all_rows_list = [item for item in all_rows if isinstance(item, dict)] if isinstance(all_rows, list) else []

    hotspot_kind_filter = str(hotspot_kind or "").strip().lower() or None
    if hotspot_kind_filter not in {None, "finding", "comment"}:
        hotspot_kind_filter = None
    hotspot_severity_filter = str(hotspot_severity or "").strip().lower() or None
    if hotspot_severity_filter not in {None, "high", "medium", "low", "unknown"}:
        hotspot_severity_filter = None
    min_overdue_filter = None
    if isinstance(min_overdue_hours, (int, float)):
        min_overdue_filter = max(0.0, float(min_overdue_hours))

    filtered_rows: list[Dict[str, Any]] = []
    for row in all_rows_list:
        row_kind = str(row.get("kind") or "").strip().lower()
        row_severity = str(row.get("severity") or "").strip().lower() or "unknown"
        overdue_value_raw = row.get("overdue_hours")
        try:
            overdue_value = float(overdue_value_raw) if overdue_value_raw is not None else None
        except (TypeError, ValueError):
            overdue_value = None
        if hotspot_kind_filter and row_kind != hotspot_kind_filter:
            continue
        if hotspot_severity_filter and row_severity != hotspot_severity_filter:
            continue
        if min_overdue_filter is not None and (overdue_value is None or overdue_value < min_overdue_filter):
            continue
        filtered_rows.append(dict(row))

    def _series_rows(counts: Dict[str, int]) -> list[Dict[str, Any]]:
        return [{"bucket": bucket, "count": int(counts.get(bucket) or 0)} for bucket in sorted(counts.keys())]

    total_bucket_counts: Dict[str, int] = {}
    severity_bucket_counts: Dict[str, Dict[str, int]] = {}
    section_bucket_counts: Dict[str, Dict[str, int]] = {}
    kind_bucket_counts: Dict[str, Dict[str, int]] = {}
    kind_totals: Dict[str, int] = {}
    severity_totals: Dict[str, int] = {}
    section_totals: Dict[str, int] = {}

    for row in filtered_rows:
        due_dt = _parse_event_ts(row.get("due_at"))
        bucket = due_dt.date().isoformat() if due_dt is not None else "unknown"
        row_kind = str(row.get("kind") or "").strip().lower() or "unknown"
        row_severity = str(row.get("severity") or "").strip().lower() or "unknown"
        row_section = str(row.get("section") or "").strip().lower() or "unknown"
        total_bucket_counts[bucket] = int(total_bucket_counts.get(bucket) or 0) + 1

        severity_bucket = severity_bucket_counts.setdefault(row_severity, {})
        severity_bucket[bucket] = int(severity_bucket.get(bucket) or 0) + 1
        section_bucket = section_bucket_counts.setdefault(row_section, {})
        section_bucket[bucket] = int(section_bucket.get(bucket) or 0) + 1
        kind_bucket = kind_bucket_counts.setdefault(row_kind, {})
        kind_bucket[bucket] = int(kind_bucket.get(bucket) or 0) + 1

        kind_totals[row_kind] = int(kind_totals.get(row_kind) or 0) + 1
        severity_totals[row_severity] = int(severity_totals.get(row_severity) or 0) + 1
        section_totals[row_section] = int(section_totals.get(row_section) or 0) + 1

    total_series = _series_rows(total_bucket_counts)
    severity_series: Dict[str, list[Dict[str, Any]]] = {}
    for level in ("high", "medium", "low", "unknown"):
        severity_series[level] = _series_rows(severity_bucket_counts.get(level, {}))
    for level in sorted(severity_bucket_counts.keys()):
        if level in severity_series:
            continue
        severity_series[level] = _series_rows(severity_bucket_counts.get(level, {}))

    section_series: Dict[str, list[Dict[str, Any]]] = {}
    for section in sorted(section_bucket_counts.keys()):
        section_series[section] = _series_rows(section_bucket_counts.get(section, {}))

    kind_series: Dict[str, list[Dict[str, Any]]] = {}
    for kind in ("finding", "comment", "unknown"):
        kind_series[kind] = _series_rows(kind_bucket_counts.get(kind, {}))
    for kind in sorted(kind_bucket_counts.keys()):
        if kind in kind_series:
            continue
        kind_series[kind] = _series_rows(kind_bucket_counts.get(kind, {}))

    dated_buckets = []
    for point in total_series:
        bucket = str(point.get("bucket") or "").strip()
        try:
            datetime.strptime(bucket, "%Y-%m-%d")
            dated_buckets.append(bucket)
        except ValueError:
            continue
    time_window_start = dated_buckets[0] if dated_buckets else None
    time_window_end = dated_buckets[-1] if dated_buckets else None

    def _max_key_value(counts: Dict[str, int]) -> tuple[Optional[str], Optional[int]]:
        key: Optional[str] = None
        value = -1
        for item_key, item_total in counts.items():
            current = int(item_total or 0)
            if current > value:
                value = current
                key = item_key
        if key is None:
            return None, None
        return key, value

    top_kind, top_kind_count = _max_key_value(kind_totals)
    top_severity, top_severity_count = _max_key_value(severity_totals)
    top_section, top_section_count = _max_key_value(section_totals)
    filters = hotspots_payload.get("filters")
    filters_dict = dict(filters) if isinstance(filters, dict) else {}
    return {
        "job_id": str(job_id),
        "status": str(job.get("status") or ""),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "filters": filters_dict,
        "bucket_granularity": "day",
        "bucket_count": len(total_series),
        "time_window_start": time_window_start,
        "time_window_end": time_window_end,
        "overdue_after_hours": _coerce_int(filters_dict.get("overdue_after_hours"), default=overdue_after_hours),
        "top_limit": _coerce_int(filters_dict.get("top_limit"), default=max(1, int(top_limit))),
        "hotspot_count_total": total_hotspots,
        "avg_hotspots_per_bucket": (round(total_hotspots / len(total_series), 3) if total_series else None),
        "top_kind": top_kind,
        "top_kind_count": top_kind_count,
        "top_severity": top_severity,
        "top_severity_count": top_severity_count,
        "top_section": top_section,
        "top_section_count": top_section_count,
        "oldest_overdue": hotspots_payload.get("oldest_overdue"),
        "top_overdue": (
            hotspots_payload.get("top_overdue") if isinstance(hotspots_payload.get("top_overdue"), list) else []
        ),
        "total_series": total_series,
        "severity_series": severity_series,
        "section_series": section_series,
        "kind_series": kind_series,
    }


def public_job_critic_payload(job_id: str, job: Dict[str, Any]) -> Dict[str, Any]:
    state = job.get("state")
    critic_notes = (state or {}).get("critic_notes") if isinstance(state, dict) else {}
    if not isinstance(critic_notes, dict):
        critic_notes = {}

    normalized_flaws = state_critic_findings(state if isinstance(state, dict) else {}, default_source="rules")
    fatal_flaws = [sanitize_for_public_response(item) for item in normalized_flaws]

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
    if isinstance(raw_messages, list):
        fatal_flaw_messages = [str(item) for item in raw_messages if isinstance(item, (str, int, float))]
    else:
        fatal_flaw_messages = []
    if not fatal_flaw_messages:
        fatal_flaw_messages = finding_messages(normalized_flaws)

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
    state_dict = _job_state_dict(job)
    export_contract_gate = _state_export_contract_gate(state_dict)

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
            "export_contract": sanitize_for_public_response(export_contract_gate),
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
    tenant_id: Optional[str] = None,
) -> Dict[str, Any]:
    safe_records = [sanitize_for_public_response(item) for item in records if isinstance(item, dict)]
    return {
        "count": len(safe_records),
        "donor_id": donor_id,
        "tenant_id": tenant_id,
        "records": safe_records,
    }


def public_ingest_inventory_payload(
    rows: list[Dict[str, Any]],
    *,
    donor_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
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
        "tenant_id": tenant_id,
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

    state_dict = _job_state_dict(job)
    citations = state_dict.get("citations")
    citations_list = [item for item in citations if isinstance(item, dict)] if isinstance(citations, list) else []
    citation_count = len(citations_list)
    grounding_counts = _citation_grounding_counts(citations_list)
    fallback_count = int(grounding_counts.get("fallback_namespace_citation_count") or 0)
    strategy_reference_count = int(grounding_counts.get("strategy_reference_citation_count") or 0)
    retrieval_grounded_count = int(grounding_counts.get("retrieval_grounded_citation_count") or 0)
    non_retrieval_count = int(grounding_counts.get("non_retrieval_citation_count") or 0)
    retrieval_expected = _state_retrieval_expected(state_dict)
    grounding_risk_level = _grounding_risk_level(
        fallback_count=fallback_count,
        strategy_reference_count=strategy_reference_count,
        retrieval_grounded_count=retrieval_grounded_count,
        citation_count=citation_count,
        retrieval_expected=retrieval_expected,
    )
    non_retrieval_rate = round(non_retrieval_count / citation_count, 4) if citation_count else None
    retrieval_grounded_rate = round(retrieval_grounded_count / citation_count, 4) if citation_count else None

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
        "retrieval_expected": retrieval_expected,
        "grounding_risk_level": grounding_risk_level,
        "citation_count": citation_count,
        "fallback_namespace_citation_count": fallback_count,
        "strategy_reference_citation_count": strategy_reference_count,
        "retrieval_grounded_citation_count": retrieval_grounded_count,
        "non_retrieval_citation_count": non_retrieval_count,
        "retrieval_grounded_citation_rate": retrieval_grounded_rate,
        "non_retrieval_citation_rate": non_retrieval_rate,
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

    state_dict = _job_state_dict(job)
    readiness_donor = str(rag_readiness.get("donor_id") or client_metadata.get("donor_id") or "").strip().lower()
    donor_id = readiness_donor or _job_donor_id(job) or None

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


def _job_toc_text_risk_level(job: Dict[str, Any]) -> str:
    state_dict = _job_state_dict(job)
    critic_notes = state_dict.get("critic_notes")
    critic_notes_dict = critic_notes if isinstance(critic_notes, dict) else {}
    raw_rule_checks = critic_notes_dict.get("rule_checks")
    rule_checks = [row for row in raw_rule_checks if isinstance(row, dict)] if isinstance(raw_rule_checks, list) else []
    critic_flaws = state_critic_findings(state_dict)
    toc_text_quality = _toc_text_quality_summary(rule_checks, critic_flaws)
    risk_level = str(toc_text_quality.get("risk_level") or "unknown").strip().lower()
    if risk_level in TOC_TEXT_RISK_LEVELS:
        return risk_level
    return "unknown"


def _rule_check_status_by_code(rule_checks: list[Dict[str, Any]], code: str) -> str:
    rank = {"unknown": 0, "pass": 1, "warn": 2, "fail": 3}
    best = "unknown"
    target = str(code or "").strip().upper()
    for row in rule_checks:
        if not isinstance(row, dict):
            continue
        row_code = str(row.get("code") or "").strip().upper()
        if row_code != target:
            continue
        status = str(row.get("status") or "").strip().lower()
        if status not in {"pass", "warn", "fail"}:
            continue
        if rank[status] > rank[best]:
            best = status
    return best


def _toc_text_quality_summary(rule_checks: list[Dict[str, Any]], critic_flaws: list[Dict[str, Any]]) -> Dict[str, Any]:
    placeholder_codes = {"TOC_PLACEHOLDER_CONTENT", "TOC_PLACEHOLDER_CONTENT_CRITICAL"}
    repetition_codes = {"TOC_BOILERPLATE_REPETITION", "TOC_BOILERPLATE_REPETITION_CRITICAL"}
    placeholder_finding_count = 0
    repetition_finding_count = 0
    for flaw in critic_flaws:
        if not isinstance(flaw, dict):
            continue
        code = str(flaw.get("code") or "").strip().upper()
        if code in placeholder_codes:
            placeholder_finding_count += 1
        if code in repetition_codes:
            repetition_finding_count += 1

    placeholder_check_status = _rule_check_status_by_code(rule_checks, "TOC_TEXT_COMPLETENESS")
    repetition_check_status = _rule_check_status_by_code(rule_checks, "TOC_NARRATIVE_DIVERSITY")
    issues_total = placeholder_finding_count + repetition_finding_count

    if "fail" in {placeholder_check_status, repetition_check_status}:
        risk_level = "high"
    elif "warn" in {placeholder_check_status, repetition_check_status} or issues_total > 0:
        risk_level = "medium"
    elif placeholder_check_status == "pass" or repetition_check_status == "pass":
        risk_level = "low"
    else:
        risk_level = "unknown"

    return {
        "risk_level": risk_level,
        "issues_total": issues_total,
        "placeholder_finding_count": placeholder_finding_count,
        "repetition_finding_count": repetition_finding_count,
        "placeholder_check_status": placeholder_check_status,
        "repetition_check_status": repetition_check_status,
    }


def _is_mel_placeholder_value(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return str(value).strip().lower() in MEL_PLACEHOLDER_VALUES
    if isinstance(value, list):
        if not value:
            return True
        return all(_is_mel_placeholder_value(item) for item in value)
    return False


def _mel_field_present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        token = str(value).strip().lower()
        return bool(token) and token not in MEL_PLACEHOLDER_VALUES
    if isinstance(value, list):
        if not value:
            return False
        return any(_mel_field_present(item) for item in value)
    if isinstance(value, dict):
        return bool(value)
    if isinstance(value, (int, float, bool)):
        return True
    return bool(str(value).strip())


def _mel_result_level(value: Any) -> str:
    token = str(value or "").strip().lower()
    if token in {"impact", "outcome", "output"}:
        return token
    return "unknown"


def _mel_indicator_coverage_summary(logframe_draft: Dict[str, Any]) -> Dict[str, Any]:
    raw_indicators = logframe_draft.get("indicators")
    indicators = [row for row in raw_indicators if isinstance(row, dict)] if isinstance(raw_indicators, list) else []
    indicator_count = len(indicators)
    coverage_counts: Dict[str, int] = {field: 0 for field in MEL_COVERAGE_FIELDS}
    result_level_counts: Dict[str, int] = {"impact": 0, "outcome": 0, "output": 0, "unknown": 0}
    baseline_placeholder_count = 0
    target_placeholder_count = 0

    for indicator in indicators:
        for field in MEL_COVERAGE_FIELDS:
            if _mel_field_present(indicator.get(field)):
                coverage_counts[field] = int(coverage_counts.get(field, 0)) + 1
        if _is_mel_placeholder_value(indicator.get("baseline")):
            baseline_placeholder_count += 1
        if _is_mel_placeholder_value(indicator.get("target")):
            target_placeholder_count += 1
        level = _mel_result_level(indicator.get("result_level"))
        result_level_counts[level] = int(result_level_counts.get(level, 0)) + 1

    def _rate(count: int) -> Optional[float]:
        return round(count / indicator_count, 4) if indicator_count else None

    missing_field_counts = {
        field: max(0, indicator_count - int(coverage_counts.get(field, 0))) for field in MEL_COVERAGE_FIELDS
    }
    smart_fields_present_total = sum(int(coverage_counts.get(field, 0)) for field in MEL_SMART_COVERAGE_FIELDS)
    smart_fields_total = indicator_count * len(MEL_SMART_COVERAGE_FIELDS)

    return {
        "indicator_count": indicator_count,
        "baseline_coverage_rate": _rate(int(coverage_counts.get("baseline", 0))),
        "target_coverage_rate": _rate(int(coverage_counts.get("target", 0))),
        "frequency_coverage_rate": _rate(int(coverage_counts.get("frequency", 0))),
        "formula_coverage_rate": _rate(int(coverage_counts.get("formula", 0))),
        "definition_coverage_rate": _rate(int(coverage_counts.get("definition", 0))),
        "data_source_coverage_rate": _rate(int(coverage_counts.get("data_source", 0))),
        "disaggregation_coverage_rate": _rate(int(coverage_counts.get("disaggregation", 0))),
        "result_level_coverage_rate": _rate(int(coverage_counts.get("result_level", 0))),
        "smart_field_coverage_rate": (round(smart_fields_present_total / smart_fields_total, 4) if smart_fields_total else None),
        "baseline_placeholder_count": baseline_placeholder_count,
        "target_placeholder_count": target_placeholder_count,
        "missing_field_counts": missing_field_counts,
        "result_level_counts": result_level_counts,
    }


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
    architect_claim_citations = [
        c
        for c in architect_citations
        if isinstance(c, dict)
        and str(c.get("used_for") or "") == "toc_claim"
        and str(c.get("statement_path") or "").strip()
    ]
    citation_type_counts = _citation_type_counts(citations)
    architect_citation_type_counts = _citation_type_counts(architect_citations)
    mel_citation_type_counts = _citation_type_counts(mel_citations)
    citation_grounding_counts = _citation_grounding_counts(citations)
    architect_grounding_counts = _citation_grounding_counts(architect_citations)
    mel_grounding_counts = _citation_grounding_counts(mel_citations)
    citation_retrieval_metadata_counts = _citation_retrieval_metadata_counts(citations)
    architect_retrieval_metadata_counts = _citation_retrieval_metadata_counts(architect_citations)
    mel_retrieval_metadata_counts = _citation_retrieval_metadata_counts(mel_citations)
    retrieval_expected = _state_retrieval_expected(state_dict)
    architect_claim_support_citation_count = int(architect_citation_type_counts.get("rag_claim_support") or 0)
    architect_fallback_namespace_citation_count = int(architect_citation_type_counts.get("fallback_namespace") or 0)
    architect_strategy_reference_citation_count = int(
        architect_citation_type_counts.get("strategy_reference") or 0
    ) + int(architect_citation_type_counts.get("strategy_namespace") or 0)
    mel_claim_support_citation_count = sum(
        1 for c in mel_citations if _is_claim_support_citation_type(c.get("citation_type"))
    )
    mel_fallback_namespace_citation_count = int(mel_citation_type_counts.get("fallback_namespace") or 0)
    mel_strategy_reference_citation_count = int(mel_citation_type_counts.get("strategy_reference") or 0) + int(
        mel_citation_type_counts.get("strategy_namespace") or 0
    )

    confidence_values: list[float] = []
    high_conf = 0
    low_conf = 0
    rag_low_conf = 0
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
    fallback_ns = int(citation_grounding_counts.get("fallback_namespace_citation_count") or 0)
    strategy_reference_count = int(citation_grounding_counts.get("strategy_reference_citation_count") or 0)
    retrieval_grounded_count = int(citation_grounding_counts.get("retrieval_grounded_citation_count") or 0)
    non_retrieval_count = int(citation_grounding_counts.get("non_retrieval_citation_count") or 0)

    flaw_status_counts = {"open": 0, "acknowledged": 0, "resolved": 0}
    flaw_severity_counts = {"high": 0, "medium": 0, "low": 0}
    version_bindable_finding_count = 0
    version_bound_finding_count = 0
    for flaw in critic_flaws:
        if not isinstance(flaw, dict):
            continue
        status = str(flaw.get("status") or "open").lower()
        severity = str(flaw.get("severity") or "").lower()
        section = str(flaw.get("section") or "").strip().lower()
        if section in {"toc", "logframe"}:
            version_bindable_finding_count += 1
            if str(flaw.get("version_id") or "").strip():
                version_bound_finding_count += 1
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
    claim_coverage_meta = (
        cast(Dict[str, Any], toc_generation_meta.get("claim_coverage"))
        if isinstance(toc_generation_meta.get("claim_coverage"), dict)
        else {}
    )
    raw_mel_generation_meta = state_dict.get("mel_generation_meta")
    mel_generation_meta: Dict[str, Any] = (
        cast(Dict[str, Any], raw_mel_generation_meta) if isinstance(raw_mel_generation_meta, dict) else {}
    )
    raw_architect_retrieval = state_dict.get("architect_retrieval")
    architect_retrieval: Dict[str, Any] = (
        cast(Dict[str, Any], raw_architect_retrieval) if isinstance(raw_architect_retrieval, dict) else {}
    )
    raw_logframe = state_dict.get("logframe_draft")
    logframe_draft: Dict[str, Any] = cast(Dict[str, Any], raw_logframe) if isinstance(raw_logframe, dict) else {}
    raw_mel_rag_trace = logframe_draft.get("rag_trace")
    mel_rag_trace: Dict[str, Any] = (
        cast(Dict[str, Any], raw_mel_rag_trace) if isinstance(raw_mel_rag_trace, dict) else {}
    )
    raw_mel_grounding_policy = state_dict.get("mel_grounding_policy")
    mel_grounding_policy: Dict[str, Any] = (
        cast(Dict[str, Any], raw_mel_grounding_policy) if isinstance(raw_mel_grounding_policy, dict) else {}
    )
    raw_grounded_gate = state_dict.get("grounded_quality_gate")
    grounded_gate: Dict[str, Any] = (
        cast(Dict[str, Any], raw_grounded_gate) if isinstance(raw_grounded_gate, dict) else {}
    )
    mel_indicator_coverage = _mel_indicator_coverage_summary(logframe_draft)
    readiness_payload = _public_job_quality_readiness_payload(job, ingest_inventory_rows)
    preflight_payload = _public_job_preflight_payload(job)
    export_contract_gate = _state_export_contract_gate(state_dict)
    toc_text_quality = _toc_text_quality_summary(
        [row for row in rule_checks if isinstance(row, dict)],
        [row for row in critic_flaws if isinstance(row, dict)],
    )
    traceability_gap = traceability_partial + traceability_missing
    architect_claim_paths = {
        str(c.get("statement_path") or "").strip()
        for c in architect_claim_citations
        if str(c.get("statement_path") or "").strip()
    }
    architect_key_claim_paths = {
        str(c.get("statement_path") or "").strip()
        for c in architect_claim_citations
        if str(c.get("statement_path") or "").strip() and int(c.get("statement_priority") or 0) >= 4
    }
    architect_confident_claim_paths = {
        str(c.get("statement_path") or "").strip()
        for c in architect_claim_citations
        if str(c.get("statement_path") or "").strip() and str(c.get("citation_type") or "") == "rag_claim_support"
    }
    architect_claim_traceability_complete = sum(
        1 for c in architect_claim_citations if citation_traceability_status(c) == "complete"
    )
    architect_claim_traceability_partial = sum(
        1 for c in architect_claim_citations if citation_traceability_status(c) == "partial"
    )
    architect_claim_traceability_missing = sum(
        1 for c in architect_claim_citations if citation_traceability_status(c) == "missing"
    )
    architect_claim_traceability_gap = architect_claim_traceability_partial + architect_claim_traceability_missing
    architect_claim_fallback_count = sum(
        1 for c in architect_claim_citations if str(c.get("citation_type") or "") == "fallback_namespace"
    )
    architect_claim_low_confidence_count = sum(
        1 for c in architect_claim_citations if str(c.get("citation_type") or "") == "rag_low_confidence"
    )
    architect_claim_threshold_considered = 0
    architect_claim_threshold_hits = 0
    for c in architect_claim_citations:
        threshold = c.get("confidence_threshold")
        confidence = c.get("citation_confidence")
        try:
            threshold_value = float(threshold) if threshold is not None else None
            confidence_value = float(confidence) if confidence is not None else None
        except (TypeError, ValueError):
            threshold_value = None
            confidence_value = None
        if threshold_value is None or confidence_value is None:
            continue
        architect_claim_threshold_considered += 1
        if confidence_value >= threshold_value:
            architect_claim_threshold_hits += 1

    def _claim_meta_int(key: str, fallback: int) -> int:
        raw = claim_coverage_meta.get(key)
        if raw is None:
            value = fallback
        else:
            try:
                value = int(raw)
            except (TypeError, ValueError):
                value = fallback
        return max(0, value)

    def _claim_meta_rate(key: str, fallback: Optional[float]) -> Optional[float]:
        raw = claim_coverage_meta.get(key)
        value: Optional[float]
        if raw is None:
            value = fallback
        else:
            try:
                value = float(raw)
            except (TypeError, ValueError):
                value = fallback
        if value is None:
            return None
        return round(max(0.0, min(1.0, value)), 4)

    claims_total = _claim_meta_int("claims_total", len(architect_claim_paths))
    key_claims_total = _claim_meta_int("key_claims_total", len(architect_key_claim_paths))
    claim_paths_covered = _claim_meta_int("claim_paths_covered", len(architect_claim_paths))
    key_claim_paths_covered = _claim_meta_int("key_claim_paths_covered", len(architect_key_claim_paths))
    confident_claim_paths_covered = _claim_meta_int(
        "confident_claim_paths_covered", len(architect_confident_claim_paths)
    )
    fallback_claim_count = _claim_meta_int("fallback_claim_count", architect_claim_fallback_count)
    low_confidence_claim_count = _claim_meta_int("low_confidence_claim_count", architect_claim_low_confidence_count)
    claim_coverage_ratio = _claim_meta_rate(
        "claim_coverage_ratio",
        round(claim_paths_covered / claims_total, 4) if claims_total else None,
    )
    key_claim_coverage_ratio = _claim_meta_rate(
        "key_claim_coverage_ratio",
        round(key_claim_paths_covered / key_claims_total, 4) if key_claims_total else None,
    )
    fallback_claim_ratio = _claim_meta_rate(
        "fallback_claim_ratio",
        round(fallback_claim_count / len(architect_claim_citations), 4) if architect_claim_citations else None,
    )
    architect_claim_traceability_complete_rate = (
        round(architect_claim_traceability_complete / len(architect_claim_citations), 4)
        if architect_claim_citations
        else None
    )
    architect_claim_traceability_gap_rate = (
        round(architect_claim_traceability_gap / len(architect_claim_citations), 4)
        if architect_claim_citations
        else None
    )

    payload: Dict[str, Any] = {
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
            "version_bindable_finding_count": version_bindable_finding_count,
            "version_bound_finding_count": version_bound_finding_count,
            "version_binding_rate": (
                round(version_bound_finding_count / version_bindable_finding_count, 4)
                if version_bindable_finding_count
                else None
            ),
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
            "citation_type_counts": citation_type_counts,
            "architect_citation_type_counts": architect_citation_type_counts,
            "mel_citation_type_counts": mel_citation_type_counts,
            "high_confidence_citation_count": high_conf,
            "low_confidence_citation_count": low_conf,
            "architect_claim_support_citation_count": architect_claim_support_citation_count,
            "architect_claim_support_rate": (
                round(architect_claim_support_citation_count / len(architect_citations), 4)
                if architect_citations
                else None
            ),
            "architect_fallback_namespace_citation_count": architect_fallback_namespace_citation_count,
            "architect_fallback_namespace_citation_rate": (
                round(architect_fallback_namespace_citation_count / len(architect_citations), 4)
                if architect_citations
                else None
            ),
            "architect_strategy_reference_citation_count": architect_strategy_reference_citation_count,
            "architect_strategy_reference_citation_rate": (
                round(architect_strategy_reference_citation_count / len(architect_citations), 4)
                if architect_citations
                else None
            ),
            "architect_non_retrieval_citation_count": int(
                architect_grounding_counts.get("non_retrieval_citation_count") or 0
            ),
            "architect_non_retrieval_citation_rate": (
                round(
                    int(architect_grounding_counts.get("non_retrieval_citation_count") or 0) / len(architect_citations),
                    4,
                )
                if architect_citations
                else None
            ),
            "architect_retrieval_grounded_citation_count": int(
                architect_grounding_counts.get("retrieval_grounded_citation_count") or 0
            ),
            "architect_retrieval_grounded_citation_rate": (
                round(
                    int(architect_grounding_counts.get("retrieval_grounded_citation_count") or 0)
                    / len(architect_citations),
                    4,
                )
                if architect_citations
                else None
            ),
            "architect_doc_id_present_citation_count": int(
                architect_retrieval_metadata_counts.get("doc_id_present_citation_count") or 0
            ),
            "architect_doc_id_present_citation_rate": (
                round(
                    int(architect_retrieval_metadata_counts.get("doc_id_present_citation_count") or 0)
                    / len(architect_citations),
                    4,
                )
                if architect_citations
                else None
            ),
            "architect_retrieval_rank_present_citation_count": int(
                architect_retrieval_metadata_counts.get("retrieval_rank_present_citation_count") or 0
            ),
            "architect_retrieval_rank_present_citation_rate": (
                round(
                    int(architect_retrieval_metadata_counts.get("retrieval_rank_present_citation_count") or 0)
                    / len(architect_citations),
                    4,
                )
                if architect_citations
                else None
            ),
            "architect_retrieval_confidence_present_citation_count": int(
                architect_retrieval_metadata_counts.get("retrieval_confidence_present_citation_count") or 0
            ),
            "architect_retrieval_confidence_present_citation_rate": (
                round(
                    int(architect_retrieval_metadata_counts.get("retrieval_confidence_present_citation_count") or 0)
                    / len(architect_citations),
                    4,
                )
                if architect_citations
                else None
            ),
            "architect_retrieval_metadata_complete_citation_count": int(
                architect_retrieval_metadata_counts.get("retrieval_metadata_complete_citation_count") or 0
            ),
            "architect_retrieval_metadata_complete_citation_rate": (
                round(
                    int(architect_retrieval_metadata_counts.get("retrieval_metadata_complete_citation_count") or 0)
                    / len(architect_citations),
                    4,
                )
                if architect_citations
                else None
            ),
            "mel_claim_support_citation_count": mel_claim_support_citation_count,
            "mel_claim_support_rate": (
                round(mel_claim_support_citation_count / len(mel_citations), 4) if mel_citations else None
            ),
            "mel_fallback_namespace_citation_count": mel_fallback_namespace_citation_count,
            "mel_fallback_namespace_citation_rate": (
                round(mel_fallback_namespace_citation_count / len(mel_citations), 4) if mel_citations else None
            ),
            "mel_strategy_reference_citation_count": mel_strategy_reference_citation_count,
            "mel_strategy_reference_citation_rate": (
                round(mel_strategy_reference_citation_count / len(mel_citations), 4) if mel_citations else None
            ),
            "mel_non_retrieval_citation_count": int(mel_grounding_counts.get("non_retrieval_citation_count") or 0),
            "mel_non_retrieval_citation_rate": (
                round(int(mel_grounding_counts.get("non_retrieval_citation_count") or 0) / len(mel_citations), 4)
                if mel_citations
                else None
            ),
            "mel_retrieval_grounded_citation_count": int(
                mel_grounding_counts.get("retrieval_grounded_citation_count") or 0
            ),
            "mel_retrieval_grounded_citation_rate": (
                round(int(mel_grounding_counts.get("retrieval_grounded_citation_count") or 0) / len(mel_citations), 4)
                if mel_citations
                else None
            ),
            "mel_doc_id_present_citation_count": int(
                mel_retrieval_metadata_counts.get("doc_id_present_citation_count") or 0
            ),
            "mel_doc_id_present_citation_rate": (
                round(
                    int(mel_retrieval_metadata_counts.get("doc_id_present_citation_count") or 0) / len(mel_citations), 4
                )
                if mel_citations
                else None
            ),
            "mel_retrieval_rank_present_citation_count": int(
                mel_retrieval_metadata_counts.get("retrieval_rank_present_citation_count") or 0
            ),
            "mel_retrieval_rank_present_citation_rate": (
                round(
                    int(mel_retrieval_metadata_counts.get("retrieval_rank_present_citation_count") or 0)
                    / len(mel_citations),
                    4,
                )
                if mel_citations
                else None
            ),
            "mel_retrieval_confidence_present_citation_count": int(
                mel_retrieval_metadata_counts.get("retrieval_confidence_present_citation_count") or 0
            ),
            "mel_retrieval_confidence_present_citation_rate": (
                round(
                    int(mel_retrieval_metadata_counts.get("retrieval_confidence_present_citation_count") or 0)
                    / len(mel_citations),
                    4,
                )
                if mel_citations
                else None
            ),
            "mel_retrieval_metadata_complete_citation_count": int(
                mel_retrieval_metadata_counts.get("retrieval_metadata_complete_citation_count") or 0
            ),
            "mel_retrieval_metadata_complete_citation_rate": (
                round(
                    int(mel_retrieval_metadata_counts.get("retrieval_metadata_complete_citation_count") or 0)
                    / len(mel_citations),
                    4,
                )
                if mel_citations
                else None
            ),
            "architect_rag_low_confidence_citation_count": sum(
                1 for c in architect_citations if str(c.get("citation_type") or "") == "rag_low_confidence"
            ),
            "mel_rag_low_confidence_citation_count": sum(
                1 for c in mel_citations if str(c.get("citation_type") or "") == "rag_low_confidence"
            ),
            "rag_low_confidence_citation_count": rag_low_conf,
            "fallback_namespace_citation_count": fallback_ns,
            "fallback_namespace_citation_rate": round(fallback_ns / len(citations), 4) if citations else None,
            "strategy_reference_citation_count": strategy_reference_count,
            "strategy_reference_citation_rate": (
                round(strategy_reference_count / len(citations), 4) if citations else None
            ),
            "retrieval_grounded_citation_count": retrieval_grounded_count,
            "retrieval_grounded_citation_rate": (
                round(retrieval_grounded_count / len(citations), 4) if citations else None
            ),
            "doc_id_present_citation_count": int(
                citation_retrieval_metadata_counts.get("doc_id_present_citation_count") or 0
            ),
            "doc_id_present_citation_rate": (
                round(
                    int(citation_retrieval_metadata_counts.get("doc_id_present_citation_count") or 0) / len(citations),
                    4,
                )
                if citations
                else None
            ),
            "retrieval_rank_present_citation_count": int(
                citation_retrieval_metadata_counts.get("retrieval_rank_present_citation_count") or 0
            ),
            "retrieval_rank_present_citation_rate": (
                round(
                    int(citation_retrieval_metadata_counts.get("retrieval_rank_present_citation_count") or 0)
                    / len(citations),
                    4,
                )
                if citations
                else None
            ),
            "retrieval_confidence_present_citation_count": int(
                citation_retrieval_metadata_counts.get("retrieval_confidence_present_citation_count") or 0
            ),
            "retrieval_confidence_present_citation_rate": (
                round(
                    int(citation_retrieval_metadata_counts.get("retrieval_confidence_present_citation_count") or 0)
                    / len(citations),
                    4,
                )
                if citations
                else None
            ),
            "retrieval_metadata_complete_citation_count": int(
                citation_retrieval_metadata_counts.get("retrieval_metadata_complete_citation_count") or 0
            ),
            "retrieval_metadata_complete_citation_rate": (
                round(
                    int(citation_retrieval_metadata_counts.get("retrieval_metadata_complete_citation_count") or 0)
                    / len(citations),
                    4,
                )
                if citations
                else None
            ),
            "non_retrieval_citation_count": non_retrieval_count,
            "non_retrieval_citation_rate": (round(non_retrieval_count / len(citations), 4) if citations else None),
            "retrieval_expected": retrieval_expected,
            "grounding_risk_level": _grounding_risk_level(
                fallback_count=fallback_ns,
                strategy_reference_count=strategy_reference_count,
                retrieval_grounded_count=retrieval_grounded_count,
                citation_count=len(citations),
                retrieval_expected=retrieval_expected,
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
        "architect_claims": {
            "claim_citation_count": len(architect_claim_citations),
            "claims_total": claims_total,
            "key_claims_total": key_claims_total,
            "claim_paths_covered": claim_paths_covered,
            "key_claim_paths_covered": key_claim_paths_covered,
            "confident_claim_paths_covered": confident_claim_paths_covered,
            "fallback_claim_count": fallback_claim_count,
            "low_confidence_claim_count": low_confidence_claim_count,
            "claim_coverage_ratio": claim_coverage_ratio,
            "key_claim_coverage_ratio": key_claim_coverage_ratio,
            "fallback_claim_ratio": fallback_claim_ratio,
            "threshold_hit_rate": (
                round(architect_claim_threshold_hits / architect_claim_threshold_considered, 4)
                if architect_claim_threshold_considered
                else None
            ),
            "traceability_complete_citation_count": architect_claim_traceability_complete,
            "traceability_partial_citation_count": architect_claim_traceability_partial,
            "traceability_missing_citation_count": architect_claim_traceability_missing,
            "traceability_gap_citation_count": architect_claim_traceability_gap,
            "traceability_complete_rate": architect_claim_traceability_complete_rate,
            "traceability_gap_rate": architect_claim_traceability_gap_rate,
        },
        "mel": {
            "engine": sanitize_for_public_response(mel_generation_meta.get("engine")),
            "llm_used": sanitize_for_public_response(mel_generation_meta.get("llm_used")),
            "retrieval_used": sanitize_for_public_response(mel_generation_meta.get("retrieval_used")),
            "retrieval_namespace": sanitize_for_public_response(mel_rag_trace.get("namespace")),
            "retrieval_hits_count": sanitize_for_public_response(mel_rag_trace.get("used_results")),
            "avg_retrieval_confidence": sanitize_for_public_response(mel_rag_trace.get("avg_retrieval_confidence")),
            "citation_policy": sanitize_for_public_response(
                {
                    "claim_support_types": ["rag_result", "rag_support", "rag_claim_support"],
                    "high_confidence_threshold": 0.35,
                }
            ),
            **mel_indicator_coverage,
        },
        "mel_grounding_policy": sanitize_for_public_response(mel_grounding_policy),
        "export_contract": sanitize_for_public_response(export_contract_gate),
        "preflight": preflight_payload,
        "readiness": readiness_payload,
        "toc_text_quality": toc_text_quality,
    }
    if grounded_gate:
        payload["grounded_gate"] = sanitize_for_public_response(grounded_gate)
    return payload


def public_job_grounding_gate_payload(job_id: str, job: Dict[str, Any]) -> Dict[str, Any]:
    state_dict = _job_state_dict(job)
    preflight_payload = _public_job_preflight_payload(job)
    raw_runtime_gate = state_dict.get("grounded_quality_gate")
    runtime_gate: Dict[str, Any] = cast(Dict[str, Any], raw_runtime_gate) if isinstance(raw_runtime_gate, dict) else {}
    raw_mel_policy = state_dict.get("mel_grounding_policy")
    mel_policy: Dict[str, Any] = cast(Dict[str, Any], raw_mel_policy) if isinstance(raw_mel_policy, dict) else {}

    payload: Dict[str, Any] = {
        "job_id": job_id,
        "status": str(job.get("status") or "unknown"),
    }
    if runtime_gate:
        payload["grounded_gate"] = sanitize_for_public_response(runtime_gate)
    preflight_grounding_policy = (
        preflight_payload.get("grounding_policy") if isinstance(preflight_payload, dict) else None
    )
    if isinstance(preflight_grounding_policy, dict):
        payload["preflight_grounding_policy"] = sanitize_for_public_response(preflight_grounding_policy)
    if mel_policy:
        payload["mel_grounding_policy"] = sanitize_for_public_response(mel_policy)
    return payload


def public_portfolio_metrics_payload(
    jobs_by_id: Dict[str, Dict[str, Any]],
    *,
    donor_id: Optional[str] = None,
    status: Optional[str] = None,
    hitl_enabled: Optional[bool] = None,
    warning_level: Optional[str] = None,
    grounding_risk_level: Optional[str] = None,
    toc_text_risk_level: Optional[str] = None,
) -> Dict[str, Any]:
    warning_level_filter = _normalize_warning_level_filter(warning_level)
    grounding_risk_filter = _normalize_grounding_risk_filter(grounding_risk_level)
    toc_text_risk_filter = _normalize_toc_text_risk_filter(toc_text_risk_level)
    filtered: list[tuple[str, Dict[str, Any]]] = []
    for job_id, job in jobs_by_id.items():
        if not isinstance(job, dict):
            continue
        job_status = str(job.get("status") or "")
        job_donor = _job_donor_id(job)
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
        if toc_text_risk_filter is not None and _job_toc_text_risk_level(job) != toc_text_risk_filter:
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
        job_donor = _job_donor_id(job, default="unknown")
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
            "toc_text_risk_level": toc_text_risk_filter,
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


def _grounded_gate_section_counts_template() -> Dict[str, int]:
    return {section: 0 for section in GROUNDED_GATE_SECTION_ORDER}


def _normalized_grounded_gate_sections(gate: Dict[str, Any]) -> set[str]:
    sections: set[str] = set()
    failed_sections = gate.get("failed_sections")
    if isinstance(failed_sections, list):
        for section in failed_sections:
            token = str(section or "").strip().lower()
            if token in GROUNDED_GATE_SECTION_ORDER:
                sections.add(token)

    reason_details = gate.get("reason_details")
    if isinstance(reason_details, list):
        for row in reason_details:
            if not isinstance(row, dict):
                continue
            token = str(row.get("section") or "").strip().lower()
            if token in GROUNDED_GATE_SECTION_ORDER:
                sections.add(token)
    return sections


def _grounded_gate_reason_codes(gate: Dict[str, Any]) -> list[str]:
    codes: list[str] = []
    reason_details = gate.get("reason_details")
    if isinstance(reason_details, list):
        for row in reason_details:
            if not isinstance(row, dict):
                continue
            token = str(row.get("code") or "").strip()
            if token:
                codes.append(token)
    if codes:
        return codes
    reasons = gate.get("reasons")
    if isinstance(reasons, list):
        return [str(reason).strip() for reason in reasons if str(reason).strip()]
    return []


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
    toc_text_risk_level: Optional[str] = None,
) -> Dict[str, Any]:
    warning_level_filter = _normalize_warning_level_filter(warning_level)
    grounding_risk_filter = _normalize_grounding_risk_filter(grounding_risk_level)
    finding_status_filter = _normalize_finding_status_filter(finding_status)
    finding_severity_filter = _normalize_finding_severity_filter(finding_severity)
    toc_text_risk_filter = _normalize_toc_text_risk_filter(toc_text_risk_level)
    filtered: list[tuple[str, Dict[str, Any]]] = []
    for job_id, job in jobs_by_id.items():
        if not isinstance(job, dict):
            continue
        job_status = str(job.get("status") or "")
        job_donor = _job_donor_id(job)
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
        if toc_text_risk_filter is not None and _job_toc_text_risk_level(job) != toc_text_risk_filter:
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
    donor_grounded_gate_breakdown: Dict[str, Dict[str, Any]] = {}
    grounded_gate_section_fail_counts = _grounded_gate_section_counts_template()
    grounded_gate_reason_counts: Dict[str, int] = {}
    grounded_gate_present_job_count = 0
    grounded_gate_blocked_job_count = 0
    grounded_gate_passed_job_count = 0
    quality_rows: list[Dict[str, Any]] = []

    for job_id, job in filtered:
        job_status = str(job.get("status") or "")
        status_counts[job_status] = status_counts.get(job_status, 0) + 1
        job_donor = _job_donor_id(job, default="unknown")
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
    strategy_reference_citation_count = 0
    retrieval_grounded_citation_count = 0
    doc_id_present_citation_count = 0
    retrieval_rank_present_citation_count = 0
    retrieval_confidence_present_citation_count = 0
    retrieval_metadata_complete_citation_count = 0
    non_retrieval_citation_count = 0
    architect_doc_id_present_citation_count = 0
    architect_retrieval_rank_present_citation_count = 0
    architect_retrieval_confidence_present_citation_count = 0
    architect_retrieval_metadata_complete_citation_count = 0
    mel_doc_id_present_citation_count = 0
    mel_retrieval_rank_present_citation_count = 0
    mel_retrieval_confidence_present_citation_count = 0
    mel_retrieval_metadata_complete_citation_count = 0
    traceability_complete_citation_count = 0
    traceability_partial_citation_count = 0
    traceability_missing_citation_count = 0
    traceability_gap_citation_count = 0
    retrieval_expected_true_job_count = 0
    retrieval_expected_false_job_count = 0
    llm_finding_label_counts_total: Dict[str, int] = {}
    llm_advisory_diagnostics_job_count = 0
    llm_advisory_applied_job_count = 0
    llm_advisory_candidate_finding_count = 0
    llm_advisory_rejected_reason_counts: Dict[str, int] = {}
    architect_citation_count_total = 0
    architect_claim_support_citation_count = 0
    citation_type_counts_total: Dict[str, int] = {}
    architect_citation_type_counts_total: Dict[str, int] = {}
    mel_citation_type_counts_total: Dict[str, int] = {}
    toc_text_quality_risk_counts: Dict[str, int] = {"high": 0, "medium": 0, "low": 0, "unknown": 0}
    toc_text_quality_placeholder_check_status_counts: Dict[str, int] = {
        "pass": 0,
        "warn": 0,
        "fail": 0,
        "unknown": 0,
    }
    toc_text_quality_repetition_check_status_counts: Dict[str, int] = {
        "pass": 0,
        "warn": 0,
        "fail": 0,
        "unknown": 0,
    }
    toc_text_quality_issues_total = 0
    toc_text_quality_placeholder_finding_count = 0
    toc_text_quality_repetition_finding_count = 0
    mel_indicator_job_count = 0
    mel_indicator_count_total = 0
    mel_baseline_placeholder_count = 0
    mel_target_placeholder_count = 0
    mel_field_present_weighted_totals: Dict[str, float] = {field: 0.0 for field in MEL_COVERAGE_FIELDS}
    mel_result_level_counts_total: Dict[str, int] = {"impact": 0, "outcome": 0, "output": 0, "unknown": 0}

    for row in quality_rows:
        row_critic: Dict[str, Any] = (
            cast(Dict[str, Any], row.get("critic")) if isinstance(row.get("critic"), dict) else {}
        )
        row_citations: Dict[str, Any] = (
            cast(Dict[str, Any], row.get("citations")) if isinstance(row.get("citations"), dict) else {}
        )
        row_toc_text_quality: Dict[str, Any] = (
            cast(Dict[str, Any], row.get("toc_text_quality")) if isinstance(row.get("toc_text_quality"), dict) else {}
        )
        row_mel: Dict[str, Any] = cast(Dict[str, Any], row.get("mel")) if isinstance(row.get("mel"), dict) else {}
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
        architect_citation_count_total += int(row_citations.get("architect_citation_count") or 0)
        architect_claim_support_citation_count += int(row_citations.get("architect_claim_support_citation_count") or 0)
        low_confidence_citation_count += int(row_citations.get("low_confidence_citation_count") or 0)
        rag_low_confidence_citation_count += int(row_citations.get("rag_low_confidence_citation_count") or 0)
        architect_rag_low_confidence_citation_count += int(
            row_citations.get("architect_rag_low_confidence_citation_count") or 0
        )
        mel_rag_low_confidence_citation_count += int(row_citations.get("mel_rag_low_confidence_citation_count") or 0)
        fallback_namespace_citation_count += int(row_citations.get("fallback_namespace_citation_count") or 0)
        strategy_reference_citation_count += int(row_citations.get("strategy_reference_citation_count") or 0)
        retrieval_grounded_citation_count += int(row_citations.get("retrieval_grounded_citation_count") or 0)
        doc_id_present_citation_count += int(row_citations.get("doc_id_present_citation_count") or 0)
        retrieval_rank_present_citation_count += int(row_citations.get("retrieval_rank_present_citation_count") or 0)
        retrieval_confidence_present_citation_count += int(
            row_citations.get("retrieval_confidence_present_citation_count") or 0
        )
        retrieval_metadata_complete_citation_count += int(
            row_citations.get("retrieval_metadata_complete_citation_count") or 0
        )
        architect_doc_id_present_citation_count += int(
            row_citations.get("architect_doc_id_present_citation_count") or 0
        )
        architect_retrieval_rank_present_citation_count += int(
            row_citations.get("architect_retrieval_rank_present_citation_count") or 0
        )
        architect_retrieval_confidence_present_citation_count += int(
            row_citations.get("architect_retrieval_confidence_present_citation_count") or 0
        )
        architect_retrieval_metadata_complete_citation_count += int(
            row_citations.get("architect_retrieval_metadata_complete_citation_count") or 0
        )
        mel_doc_id_present_citation_count += int(row_citations.get("mel_doc_id_present_citation_count") or 0)
        mel_retrieval_rank_present_citation_count += int(
            row_citations.get("mel_retrieval_rank_present_citation_count") or 0
        )
        mel_retrieval_confidence_present_citation_count += int(
            row_citations.get("mel_retrieval_confidence_present_citation_count") or 0
        )
        mel_retrieval_metadata_complete_citation_count += int(
            row_citations.get("mel_retrieval_metadata_complete_citation_count") or 0
        )
        row_non_retrieval_raw = row_citations.get("non_retrieval_citation_count")
        if row_non_retrieval_raw is None:
            row_non_retrieval_count = _coerce_int(row_citations.get("fallback_namespace_citation_count")) + _coerce_int(
                row_citations.get("strategy_reference_citation_count")
            )
        else:
            row_non_retrieval_count = _coerce_int(row_non_retrieval_raw)
        non_retrieval_citation_count += row_non_retrieval_count
        traceability_complete_citation_count += int(row_citations.get("traceability_complete_citation_count") or 0)
        traceability_partial_citation_count += int(row_citations.get("traceability_partial_citation_count") or 0)
        traceability_missing_citation_count += int(row_citations.get("traceability_missing_citation_count") or 0)
        traceability_gap_citation_count += int(row_citations.get("traceability_gap_citation_count") or 0)
        row_retrieval_expected = row_citations.get("retrieval_expected")
        if row_retrieval_expected is False:
            retrieval_expected_false_job_count += 1
        else:
            retrieval_expected_true_job_count += 1
        row_citation_type_counts = (
            cast(Dict[str, Any], row_citations.get("citation_type_counts"))
            if isinstance(row_citations.get("citation_type_counts"), dict)
            else {}
        )
        for ctype, count in row_citation_type_counts.items():
            key = str(ctype).strip().lower() or "unknown"
            citation_type_counts_total[key] = int(citation_type_counts_total.get(key, 0)) + int(count or 0)
        row_architect_citation_type_counts = (
            cast(Dict[str, Any], row_citations.get("architect_citation_type_counts"))
            if isinstance(row_citations.get("architect_citation_type_counts"), dict)
            else {}
        )
        for ctype, count in row_architect_citation_type_counts.items():
            key = str(ctype).strip().lower() or "unknown"
            architect_citation_type_counts_total[key] = int(architect_citation_type_counts_total.get(key, 0)) + int(
                count or 0
            )
        row_mel_citation_type_counts = (
            cast(Dict[str, Any], row_citations.get("mel_citation_type_counts"))
            if isinstance(row_citations.get("mel_citation_type_counts"), dict)
            else {}
        )
        for ctype, count in row_mel_citation_type_counts.items():
            key = str(ctype).strip().lower() or "unknown"
            mel_citation_type_counts_total[key] = int(mel_citation_type_counts_total.get(key, 0)) + int(count or 0)
        row_toc_risk_level = str(row_toc_text_quality.get("risk_level") or "unknown").strip().lower()
        if row_toc_risk_level not in toc_text_quality_risk_counts:
            row_toc_risk_level = "unknown"
        toc_text_quality_risk_counts[row_toc_risk_level] = (
            int(toc_text_quality_risk_counts.get(row_toc_risk_level, 0)) + 1
        )
        toc_text_quality_issues_total += int(row_toc_text_quality.get("issues_total") or 0)
        toc_text_quality_placeholder_finding_count += int(row_toc_text_quality.get("placeholder_finding_count") or 0)
        toc_text_quality_repetition_finding_count += int(row_toc_text_quality.get("repetition_finding_count") or 0)
        placeholder_check_status = (
            str(row_toc_text_quality.get("placeholder_check_status") or "unknown").strip().lower()
        )
        if placeholder_check_status not in toc_text_quality_placeholder_check_status_counts:
            placeholder_check_status = "unknown"
        toc_text_quality_placeholder_check_status_counts[placeholder_check_status] = (
            int(toc_text_quality_placeholder_check_status_counts.get(placeholder_check_status, 0)) + 1
        )
        repetition_check_status = str(row_toc_text_quality.get("repetition_check_status") or "unknown").strip().lower()
        if repetition_check_status not in toc_text_quality_repetition_check_status_counts:
            repetition_check_status = "unknown"
        toc_text_quality_repetition_check_status_counts[repetition_check_status] = (
            int(toc_text_quality_repetition_check_status_counts.get(repetition_check_status, 0)) + 1
        )

        row_indicator_count = _coerce_int(row_mel.get("indicator_count"), default=0)
        if row_indicator_count > 0:
            mel_indicator_job_count += 1
            mel_indicator_count_total += row_indicator_count

        row_missing_field_counts = (
            cast(Dict[str, Any], row_mel.get("missing_field_counts"))
            if isinstance(row_mel.get("missing_field_counts"), dict)
            else {}
        )
        for field in MEL_COVERAGE_FIELDS:
            if row_indicator_count <= 0:
                continue
            field_present: Optional[float] = None
            missing_raw = row_missing_field_counts.get(field)
            if isinstance(missing_raw, (int, float)):
                row_missing = max(0, min(row_indicator_count, _coerce_int(missing_raw, default=0)))
                field_present = float(max(0, row_indicator_count - row_missing))
            else:
                rate_raw = row_mel.get(f"{field}_coverage_rate")
                if isinstance(rate_raw, (int, float)):
                    bounded_rate = max(0.0, min(1.0, float(rate_raw)))
                    field_present = bounded_rate * float(row_indicator_count)
            if field_present is not None:
                mel_field_present_weighted_totals[field] = (
                    float(mel_field_present_weighted_totals.get(field, 0.0)) + float(field_present)
                )

        mel_baseline_placeholder_count += _coerce_int(row_mel.get("baseline_placeholder_count"), default=0)
        mel_target_placeholder_count += _coerce_int(row_mel.get("target_placeholder_count"), default=0)
        row_result_level_counts = (
            cast(Dict[str, Any], row_mel.get("result_level_counts"))
            if isinstance(row_mel.get("result_level_counts"), dict)
            else {}
        )
        row_result_level_total = 0
        for level in ("impact", "outcome", "output", "unknown"):
            level_count = _coerce_int(row_result_level_counts.get(level), default=0)
            mel_result_level_counts_total[level] = int(mel_result_level_counts_total.get(level, 0)) + level_count
            row_result_level_total += level_count
        if row_indicator_count > 0 and row_result_level_total <= 0:
            mel_result_level_counts_total["unknown"] = int(mel_result_level_counts_total.get("unknown", 0)) + row_indicator_count

        donor_for_row = str(row.get("_donor_id") or "unknown")
        row_grounded_gate: Dict[str, Any] = (
            cast(Dict[str, Any], row.get("grounded_gate")) if isinstance(row.get("grounded_gate"), dict) else {}
        )
        donor_grounded_gate_row = donor_grounded_gate_breakdown.setdefault(
            donor_for_row,
            {
                "job_count": 0,
                "present_job_count": 0,
                "blocked_job_count": 0,
                "passed_job_count": 0,
                "section_fail_counts": _grounded_gate_section_counts_template(),
                "reason_counts": {},
            },
        )
        donor_grounded_gate_row["job_count"] = int(donor_grounded_gate_row.get("job_count") or 0) + 1
        if row_grounded_gate:
            grounded_gate_present_job_count += 1
            donor_grounded_gate_row["present_job_count"] = (
                int(donor_grounded_gate_row.get("present_job_count") or 0) + 1
            )
            if bool(row_grounded_gate.get("blocking")):
                grounded_gate_blocked_job_count += 1
                donor_grounded_gate_row["blocked_job_count"] = (
                    int(donor_grounded_gate_row.get("blocked_job_count") or 0) + 1
                )
            if row_grounded_gate.get("passed") is True:
                grounded_gate_passed_job_count += 1
                donor_grounded_gate_row["passed_job_count"] = (
                    int(donor_grounded_gate_row.get("passed_job_count") or 0) + 1
                )

            row_failed_sections = _normalized_grounded_gate_sections(row_grounded_gate)
            donor_section_fail_counts = (
                cast(Dict[str, Any], donor_grounded_gate_row.get("section_fail_counts"))
                if isinstance(donor_grounded_gate_row.get("section_fail_counts"), dict)
                else {}
            )
            for section in row_failed_sections:
                grounded_gate_section_fail_counts[section] = int(grounded_gate_section_fail_counts.get(section, 0)) + 1
                donor_section_fail_counts[section] = int(donor_section_fail_counts.get(section, 0)) + 1
            donor_grounded_gate_row["section_fail_counts"] = donor_section_fail_counts

            donor_reason_counts = (
                cast(Dict[str, Any], donor_grounded_gate_row.get("reason_counts"))
                if isinstance(donor_grounded_gate_row.get("reason_counts"), dict)
                else {}
            )
            for code in _grounded_gate_reason_codes(row_grounded_gate):
                grounded_gate_reason_counts[code] = int(grounded_gate_reason_counts.get(code, 0)) + 1
                donor_reason_counts[code] = int(donor_reason_counts.get(code, 0)) + 1
            donor_grounded_gate_row["reason_counts"] = donor_reason_counts

        donor_row = donor_weighted_risk_breakdown.setdefault(
            donor_for_row,
            {
                "weighted_score": 0,
                "high_priority_signal_count": 0,
                "open_findings_total": 0,
                "high_severity_findings_total": 0,
                "needs_revision_job_count": 0,
                "citation_count_total": 0,
                "architect_citation_count_total": 0,
                "architect_claim_support_citation_count": 0,
                "low_confidence_citation_count": 0,
                "rag_low_confidence_citation_count": 0,
                "architect_rag_low_confidence_citation_count": 0,
                "mel_rag_low_confidence_citation_count": 0,
                "fallback_namespace_citation_count": 0,
                "strategy_reference_citation_count": 0,
                "retrieval_grounded_citation_count": 0,
                "doc_id_present_citation_count": 0,
                "retrieval_rank_present_citation_count": 0,
                "retrieval_confidence_present_citation_count": 0,
                "retrieval_metadata_complete_citation_count": 0,
                "non_retrieval_citation_count": 0,
                "architect_doc_id_present_citation_count": 0,
                "architect_retrieval_rank_present_citation_count": 0,
                "architect_retrieval_confidence_present_citation_count": 0,
                "architect_retrieval_metadata_complete_citation_count": 0,
                "mel_doc_id_present_citation_count": 0,
                "mel_retrieval_rank_present_citation_count": 0,
                "mel_retrieval_confidence_present_citation_count": 0,
                "mel_retrieval_metadata_complete_citation_count": 0,
                "traceability_complete_citation_count": 0,
                "traceability_partial_citation_count": 0,
                "traceability_missing_citation_count": 0,
                "traceability_gap_citation_count": 0,
                "retrieval_expected_true_job_count": 0,
                "retrieval_expected_false_job_count": 0,
                "llm_finding_label_counts": {},
                "llm_advisory_applied_label_counts": {},
                "llm_advisory_rejected_label_counts": {},
                "llm_advisory_diagnostics_job_count": 0,
                "llm_advisory_applied_job_count": 0,
                "llm_advisory_candidate_finding_count": 0,
                "llm_advisory_rejected_reason_counts": {},
                "citation_type_counts": {},
                "architect_citation_type_counts": {},
                "mel_citation_type_counts": {},
            },
        )
        donor_row["open_findings_total"] += int(row_critic.get("open_finding_count") or 0)
        donor_row["high_severity_findings_total"] += int(row_critic.get("high_severity_fatal_flaw_count") or 0)
        donor_row["citation_count_total"] += int(row_citations.get("citation_count") or 0)
        donor_row["architect_citation_count_total"] += int(row_citations.get("architect_citation_count") or 0)
        donor_row["architect_claim_support_citation_count"] += int(
            row_citations.get("architect_claim_support_citation_count") or 0
        )
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
        donor_row["strategy_reference_citation_count"] += int(
            row_citations.get("strategy_reference_citation_count") or 0
        )
        donor_row["retrieval_grounded_citation_count"] += int(
            row_citations.get("retrieval_grounded_citation_count") or 0
        )
        donor_row["doc_id_present_citation_count"] += int(row_citations.get("doc_id_present_citation_count") or 0)
        donor_row["retrieval_rank_present_citation_count"] += int(
            row_citations.get("retrieval_rank_present_citation_count") or 0
        )
        donor_row["retrieval_confidence_present_citation_count"] += int(
            row_citations.get("retrieval_confidence_present_citation_count") or 0
        )
        donor_row["retrieval_metadata_complete_citation_count"] += int(
            row_citations.get("retrieval_metadata_complete_citation_count") or 0
        )
        donor_row["architect_doc_id_present_citation_count"] += int(
            row_citations.get("architect_doc_id_present_citation_count") or 0
        )
        donor_row["architect_retrieval_rank_present_citation_count"] += int(
            row_citations.get("architect_retrieval_rank_present_citation_count") or 0
        )
        donor_row["architect_retrieval_confidence_present_citation_count"] += int(
            row_citations.get("architect_retrieval_confidence_present_citation_count") or 0
        )
        donor_row["architect_retrieval_metadata_complete_citation_count"] += int(
            row_citations.get("architect_retrieval_metadata_complete_citation_count") or 0
        )
        donor_row["mel_doc_id_present_citation_count"] += int(
            row_citations.get("mel_doc_id_present_citation_count") or 0
        )
        donor_row["mel_retrieval_rank_present_citation_count"] += int(
            row_citations.get("mel_retrieval_rank_present_citation_count") or 0
        )
        donor_row["mel_retrieval_confidence_present_citation_count"] += int(
            row_citations.get("mel_retrieval_confidence_present_citation_count") or 0
        )
        donor_row["mel_retrieval_metadata_complete_citation_count"] += int(
            row_citations.get("mel_retrieval_metadata_complete_citation_count") or 0
        )
        donor_row_non_retrieval_raw = row_citations.get("non_retrieval_citation_count")
        if donor_row_non_retrieval_raw is None:
            donor_row_non_retrieval_count = _coerce_int(
                row_citations.get("fallback_namespace_citation_count")
            ) + _coerce_int(row_citations.get("strategy_reference_citation_count"))
        else:
            donor_row_non_retrieval_count = _coerce_int(donor_row_non_retrieval_raw)
        donor_row["non_retrieval_citation_count"] += donor_row_non_retrieval_count
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
        row_retrieval_expected = row_citations.get("retrieval_expected")
        if row_retrieval_expected is False:
            donor_row["retrieval_expected_false_job_count"] += 1
        else:
            donor_row["retrieval_expected_true_job_count"] += 1
        donor_citation_type_counts = donor_row.get("citation_type_counts")
        if not isinstance(donor_citation_type_counts, dict):
            donor_citation_type_counts = {}
            donor_row["citation_type_counts"] = donor_citation_type_counts
        for ctype, count in row_citation_type_counts.items():
            key = str(ctype).strip().lower() or "unknown"
            donor_citation_type_counts[key] = int(donor_citation_type_counts.get(key, 0)) + int(count or 0)
        donor_architect_citation_type_counts = donor_row.get("architect_citation_type_counts")
        if not isinstance(donor_architect_citation_type_counts, dict):
            donor_architect_citation_type_counts = {}
            donor_row["architect_citation_type_counts"] = donor_architect_citation_type_counts
        for ctype, count in row_architect_citation_type_counts.items():
            key = str(ctype).strip().lower() or "unknown"
            donor_architect_citation_type_counts[key] = int(donor_architect_citation_type_counts.get(key, 0)) + int(
                count or 0
            )
        donor_mel_citation_type_counts = donor_row.get("mel_citation_type_counts")
        if not isinstance(donor_mel_citation_type_counts, dict):
            donor_mel_citation_type_counts = {}
            donor_row["mel_citation_type_counts"] = donor_mel_citation_type_counts
        for ctype, count in row_mel_citation_type_counts.items():
            key = str(ctype).strip().lower() or "unknown"
            donor_mel_citation_type_counts[key] = int(donor_mel_citation_type_counts.get(key, 0)) + int(count or 0)
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
        donor_architect_citations_total = int(donor_row.get("architect_citation_count_total") or 0)
        donor_mel_citations_total = max(0, donor_citations_total - donor_architect_citations_total)
        donor_fallback_total = int(donor_row.get("fallback_namespace_citation_count") or 0)
        donor_strategy_reference_total = int(donor_row.get("strategy_reference_citation_count") or 0)
        donor_retrieval_grounded_total = int(donor_row.get("retrieval_grounded_citation_count") or 0)
        donor_doc_id_present_total = int(donor_row.get("doc_id_present_citation_count") or 0)
        donor_retrieval_rank_present_total = int(donor_row.get("retrieval_rank_present_citation_count") or 0)
        donor_retrieval_confidence_present_total = int(
            donor_row.get("retrieval_confidence_present_citation_count") or 0
        )
        donor_retrieval_metadata_complete_total = int(donor_row.get("retrieval_metadata_complete_citation_count") or 0)
        donor_architect_doc_id_present_total = int(donor_row.get("architect_doc_id_present_citation_count") or 0)
        donor_architect_retrieval_rank_present_total = int(
            donor_row.get("architect_retrieval_rank_present_citation_count") or 0
        )
        donor_architect_retrieval_confidence_present_total = int(
            donor_row.get("architect_retrieval_confidence_present_citation_count") or 0
        )
        donor_architect_retrieval_metadata_complete_total = int(
            donor_row.get("architect_retrieval_metadata_complete_citation_count") or 0
        )
        donor_mel_doc_id_present_total = int(donor_row.get("mel_doc_id_present_citation_count") or 0)
        donor_mel_retrieval_rank_present_total = int(donor_row.get("mel_retrieval_rank_present_citation_count") or 0)
        donor_mel_retrieval_confidence_present_total = int(
            donor_row.get("mel_retrieval_confidence_present_citation_count") or 0
        )
        donor_mel_retrieval_metadata_complete_total = int(
            donor_row.get("mel_retrieval_metadata_complete_citation_count") or 0
        )
        donor_non_retrieval_raw = donor_row.get("non_retrieval_citation_count")
        if donor_non_retrieval_raw is None:
            donor_non_retrieval_total = donor_fallback_total + donor_strategy_reference_total
        else:
            donor_non_retrieval_total = _coerce_int(donor_non_retrieval_raw)
        donor_retrieval_expected_true = int(donor_row.get("retrieval_expected_true_job_count") or 0)
        donor_retrieval_expected_false = int(donor_row.get("retrieval_expected_false_job_count") or 0)
        donor_retrieval_expected = donor_retrieval_expected_true >= donor_retrieval_expected_false
        donor_retrieval_expected_mode = (
            "mixed"
            if donor_retrieval_expected_true > 0 and donor_retrieval_expected_false > 0
            else ("retrieval_expected" if donor_retrieval_expected else "strategy_reference_mode")
        )
        donor_architect_claim_support_total = int(donor_row.get("architect_claim_support_citation_count") or 0)
        donor_fallback_rate = round(donor_fallback_total / donor_citations_total, 4) if donor_citations_total else None
        donor_strategy_reference_rate = (
            round(donor_strategy_reference_total / donor_citations_total, 4) if donor_citations_total else None
        )
        donor_non_retrieval_rate = (
            round(donor_non_retrieval_total / donor_citations_total, 4) if donor_citations_total else None
        )
        donor_retrieval_grounded_rate = (
            round(donor_retrieval_grounded_total / donor_citations_total, 4) if donor_citations_total else None
        )
        donor_doc_id_present_rate = (
            round(donor_doc_id_present_total / donor_citations_total, 4) if donor_citations_total else None
        )
        donor_retrieval_rank_present_rate = (
            round(donor_retrieval_rank_present_total / donor_citations_total, 4) if donor_citations_total else None
        )
        donor_retrieval_confidence_present_rate = (
            round(donor_retrieval_confidence_present_total / donor_citations_total, 4)
            if donor_citations_total
            else None
        )
        donor_retrieval_metadata_complete_rate = (
            round(donor_retrieval_metadata_complete_total / donor_citations_total, 4) if donor_citations_total else None
        )
        donor_architect_doc_id_present_rate = (
            round(donor_architect_doc_id_present_total / donor_architect_citations_total, 4)
            if donor_architect_citations_total
            else None
        )
        donor_architect_retrieval_rank_present_rate = (
            round(donor_architect_retrieval_rank_present_total / donor_architect_citations_total, 4)
            if donor_architect_citations_total
            else None
        )
        donor_architect_retrieval_confidence_present_rate = (
            round(donor_architect_retrieval_confidence_present_total / donor_architect_citations_total, 4)
            if donor_architect_citations_total
            else None
        )
        donor_architect_retrieval_metadata_complete_rate = (
            round(donor_architect_retrieval_metadata_complete_total / donor_architect_citations_total, 4)
            if donor_architect_citations_total
            else None
        )
        donor_mel_doc_id_present_rate = (
            round(donor_mel_doc_id_present_total / donor_mel_citations_total, 4) if donor_mel_citations_total else None
        )
        donor_mel_retrieval_rank_present_rate = (
            round(donor_mel_retrieval_rank_present_total / donor_mel_citations_total, 4)
            if donor_mel_citations_total
            else None
        )
        donor_mel_retrieval_confidence_present_rate = (
            round(donor_mel_retrieval_confidence_present_total / donor_mel_citations_total, 4)
            if donor_mel_citations_total
            else None
        )
        donor_mel_retrieval_metadata_complete_rate = (
            round(donor_mel_retrieval_metadata_complete_total / donor_mel_citations_total, 4)
            if donor_mel_citations_total
            else None
        )
        donor_architect_claim_support_rate = (
            round(donor_architect_claim_support_total / donor_architect_citations_total, 4)
            if donor_architect_citations_total
            else None
        )
        donor_grounding_level = _grounding_risk_level(
            fallback_count=donor_fallback_total,
            strategy_reference_count=donor_strategy_reference_total,
            retrieval_grounded_count=donor_retrieval_grounded_total,
            citation_count=donor_citations_total,
            retrieval_expected=donor_retrieval_expected,
        )
        donor_row["fallback_namespace_citation_rate"] = donor_fallback_rate
        donor_row["strategy_reference_citation_rate"] = donor_strategy_reference_rate
        donor_row["non_retrieval_citation_rate"] = donor_non_retrieval_rate
        donor_row["retrieval_grounded_citation_rate"] = donor_retrieval_grounded_rate
        donor_row["doc_id_present_citation_rate"] = donor_doc_id_present_rate
        donor_row["retrieval_rank_present_citation_rate"] = donor_retrieval_rank_present_rate
        donor_row["retrieval_confidence_present_citation_rate"] = donor_retrieval_confidence_present_rate
        donor_row["retrieval_metadata_complete_citation_rate"] = donor_retrieval_metadata_complete_rate
        donor_row["architect_doc_id_present_citation_rate"] = donor_architect_doc_id_present_rate
        donor_row["architect_retrieval_rank_present_citation_rate"] = donor_architect_retrieval_rank_present_rate
        donor_row["architect_retrieval_confidence_present_citation_rate"] = (
            donor_architect_retrieval_confidence_present_rate
        )
        donor_row["architect_retrieval_metadata_complete_citation_rate"] = (
            donor_architect_retrieval_metadata_complete_rate
        )
        donor_row["mel_doc_id_present_citation_rate"] = donor_mel_doc_id_present_rate
        donor_row["mel_retrieval_rank_present_citation_rate"] = donor_mel_retrieval_rank_present_rate
        donor_row["mel_retrieval_confidence_present_citation_rate"] = donor_mel_retrieval_confidence_present_rate
        donor_row["mel_retrieval_metadata_complete_citation_rate"] = donor_mel_retrieval_metadata_complete_rate
        donor_row["architect_claim_support_rate"] = donor_architect_claim_support_rate
        donor_row["retrieval_expected_mode"] = donor_retrieval_expected_mode
        donor_row["grounding_risk_level"] = donor_grounding_level
        donor_grounding_risk_counts[donor_grounding_level] = (
            int(donor_grounding_risk_counts.get(donor_grounding_level, 0)) + 1
        )
        donor_grounding_risk_breakdown[donor_id] = {
            "citation_count_total": donor_citations_total,
            "architect_citation_count_total": donor_architect_citations_total,
            "architect_claim_support_citation_count": donor_architect_claim_support_total,
            "architect_claim_support_rate": donor_architect_claim_support_rate,
            "fallback_namespace_citation_count": donor_fallback_total,
            "fallback_namespace_citation_rate": donor_fallback_rate,
            "strategy_reference_citation_count": donor_strategy_reference_total,
            "strategy_reference_citation_rate": donor_strategy_reference_rate,
            "retrieval_grounded_citation_count": donor_retrieval_grounded_total,
            "retrieval_grounded_citation_rate": donor_retrieval_grounded_rate,
            "doc_id_present_citation_count": donor_doc_id_present_total,
            "doc_id_present_citation_rate": donor_doc_id_present_rate,
            "retrieval_rank_present_citation_count": donor_retrieval_rank_present_total,
            "retrieval_rank_present_citation_rate": donor_retrieval_rank_present_rate,
            "retrieval_confidence_present_citation_count": donor_retrieval_confidence_present_total,
            "retrieval_confidence_present_citation_rate": donor_retrieval_confidence_present_rate,
            "retrieval_metadata_complete_citation_count": donor_retrieval_metadata_complete_total,
            "retrieval_metadata_complete_citation_rate": donor_retrieval_metadata_complete_rate,
            "architect_doc_id_present_citation_count": donor_architect_doc_id_present_total,
            "architect_doc_id_present_citation_rate": donor_architect_doc_id_present_rate,
            "architect_retrieval_rank_present_citation_count": donor_architect_retrieval_rank_present_total,
            "architect_retrieval_rank_present_citation_rate": donor_architect_retrieval_rank_present_rate,
            "architect_retrieval_confidence_present_citation_count": donor_architect_retrieval_confidence_present_total,
            "architect_retrieval_confidence_present_citation_rate": donor_architect_retrieval_confidence_present_rate,
            "architect_retrieval_metadata_complete_citation_count": donor_architect_retrieval_metadata_complete_total,
            "architect_retrieval_metadata_complete_citation_rate": donor_architect_retrieval_metadata_complete_rate,
            "mel_doc_id_present_citation_count": donor_mel_doc_id_present_total,
            "mel_doc_id_present_citation_rate": donor_mel_doc_id_present_rate,
            "mel_retrieval_rank_present_citation_count": donor_mel_retrieval_rank_present_total,
            "mel_retrieval_rank_present_citation_rate": donor_mel_retrieval_rank_present_rate,
            "mel_retrieval_confidence_present_citation_count": donor_mel_retrieval_confidence_present_total,
            "mel_retrieval_confidence_present_citation_rate": donor_mel_retrieval_confidence_present_rate,
            "mel_retrieval_metadata_complete_citation_count": donor_mel_retrieval_metadata_complete_total,
            "mel_retrieval_metadata_complete_citation_rate": donor_mel_retrieval_metadata_complete_rate,
            "non_retrieval_citation_count": donor_non_retrieval_total,
            "non_retrieval_citation_rate": donor_non_retrieval_rate,
            "retrieval_expected_mode": donor_retrieval_expected_mode,
            "grounding_risk_level": donor_grounding_level,
        }

    job_count = len(filtered)
    warning_level_job_counts, warning_level_job_rates = _warning_level_breakdown(warning_level_counts, job_count)
    grounding_risk_job_counts, grounding_risk_job_rates = _grounding_risk_breakdown(grounding_risk_counts, job_count)
    toc_text_quality_risk_job_rates: Dict[str, Optional[float]] = {
        level: (round(int(count) / job_count, 4) if job_count else None)
        for level, count in toc_text_quality_risk_counts.items()
    }
    mel_missing_field_counts: Dict[str, int] = {
        field: (
            max(
                0,
                int(
                    round(
                        max(0.0, float(mel_indicator_count_total) - float(mel_field_present_weighted_totals.get(field, 0.0)))
                    )
                ),
            )
        )
        if mel_indicator_count_total > 0
        else 0
        for field in MEL_COVERAGE_FIELDS
    }
    mel_coverage_rates: Dict[str, Optional[float]] = {
        field: (
            round(float(mel_field_present_weighted_totals.get(field, 0.0)) / float(mel_indicator_count_total), 4)
            if mel_indicator_count_total
            else None
        )
        for field in MEL_COVERAGE_FIELDS
    }
    mel_smart_present_total = sum(float(mel_field_present_weighted_totals.get(field, 0.0)) for field in MEL_SMART_COVERAGE_FIELDS)
    mel_smart_total = mel_indicator_count_total * len(MEL_SMART_COVERAGE_FIELDS)
    mel_smart_field_coverage_rate = round(mel_smart_present_total / mel_smart_total, 4) if mel_smart_total else None
    quality_score_job_count = sum(1 for row in quality_rows if isinstance(row.get("quality_score"), (int, float)))
    critic_score_job_count = sum(1 for row in quality_rows if isinstance(row.get("critic_score"), (int, float)))

    citation_summary_rows: list[Dict[str, Any]] = [
        cast(Dict[str, Any], row.get("citations")) for row in quality_rows if isinstance(row.get("citations"), dict)
    ]
    fallback_namespace_citation_rate = (
        round(fallback_namespace_citation_count / citation_count_total, 4) if citation_count_total else None
    )
    strategy_reference_citation_rate = (
        round(strategy_reference_citation_count / citation_count_total, 4) if citation_count_total else None
    )
    non_retrieval_citation_rate = (
        round(non_retrieval_citation_count / citation_count_total, 4) if citation_count_total else None
    )
    retrieval_grounded_citation_rate = (
        round(retrieval_grounded_citation_count / citation_count_total, 4) if citation_count_total else None
    )
    doc_id_present_citation_rate = (
        round(doc_id_present_citation_count / citation_count_total, 4) if citation_count_total else None
    )
    retrieval_rank_present_citation_rate = (
        round(retrieval_rank_present_citation_count / citation_count_total, 4) if citation_count_total else None
    )
    retrieval_confidence_present_citation_rate = (
        round(retrieval_confidence_present_citation_count / citation_count_total, 4) if citation_count_total else None
    )
    retrieval_metadata_complete_citation_rate = (
        round(retrieval_metadata_complete_citation_count / citation_count_total, 4) if citation_count_total else None
    )
    architect_doc_id_present_citation_rate = (
        round(architect_doc_id_present_citation_count / architect_citation_count_total, 4)
        if architect_citation_count_total
        else None
    )
    architect_retrieval_rank_present_citation_rate = (
        round(architect_retrieval_rank_present_citation_count / architect_citation_count_total, 4)
        if architect_citation_count_total
        else None
    )
    architect_retrieval_confidence_present_citation_rate = (
        round(architect_retrieval_confidence_present_citation_count / architect_citation_count_total, 4)
        if architect_citation_count_total
        else None
    )
    architect_retrieval_metadata_complete_citation_rate = (
        round(architect_retrieval_metadata_complete_citation_count / architect_citation_count_total, 4)
        if architect_citation_count_total
        else None
    )
    mel_citation_count_total = max(0, citation_count_total - architect_citation_count_total)
    mel_doc_id_present_citation_rate = (
        round(mel_doc_id_present_citation_count / mel_citation_count_total, 4) if mel_citation_count_total else None
    )
    mel_retrieval_rank_present_citation_rate = (
        round(mel_retrieval_rank_present_citation_count / mel_citation_count_total, 4)
        if mel_citation_count_total
        else None
    )
    mel_retrieval_confidence_present_citation_rate = (
        round(mel_retrieval_confidence_present_citation_count / mel_citation_count_total, 4)
        if mel_citation_count_total
        else None
    )
    mel_retrieval_metadata_complete_citation_rate = (
        round(mel_retrieval_metadata_complete_citation_count / mel_citation_count_total, 4)
        if mel_citation_count_total
        else None
    )
    retrieval_expected = retrieval_expected_true_job_count >= retrieval_expected_false_job_count
    retrieval_expected_mode = (
        "mixed"
        if retrieval_expected_true_job_count > 0 and retrieval_expected_false_job_count > 0
        else ("retrieval_expected" if retrieval_expected else "strategy_reference_mode")
    )
    architect_claim_support_rate = (
        round(architect_claim_support_citation_count / architect_citation_count_total, 4)
        if architect_citation_count_total
        else None
    )
    grounding_risk_level = _grounding_risk_level(
        fallback_count=fallback_namespace_citation_count,
        strategy_reference_count=strategy_reference_citation_count,
        retrieval_grounded_count=retrieval_grounded_citation_count,
        citation_count=citation_count_total,
        retrieval_expected=retrieval_expected,
    )
    grounded_gate_block_rate = round(grounded_gate_blocked_job_count / job_count, 4) if job_count else None
    grounded_gate_block_rate_among_present = (
        round(grounded_gate_blocked_job_count / grounded_gate_present_job_count, 4)
        if grounded_gate_present_job_count
        else None
    )
    grounded_gate_pass_rate_among_present = (
        round(grounded_gate_passed_job_count / grounded_gate_present_job_count, 4)
        if grounded_gate_present_job_count
        else None
    )
    for donor_token, donor_gate_row in donor_grounded_gate_breakdown.items():
        donor_job_count = int(donor_gate_row.get("job_count") or 0)
        donor_present_job_count = int(donor_gate_row.get("present_job_count") or 0)
        donor_blocked_job_count = int(donor_gate_row.get("blocked_job_count") or 0)
        donor_passed_job_count = int(donor_gate_row.get("passed_job_count") or 0)
        donor_section_counts = (
            cast(Dict[str, Any], donor_gate_row.get("section_fail_counts"))
            if isinstance(donor_gate_row.get("section_fail_counts"), dict)
            else {}
        )
        donor_gate_row["section_fail_counts"] = {
            section: int(donor_section_counts.get(section) or 0) for section in GROUNDED_GATE_SECTION_ORDER
        }
        donor_reason_counts = (
            cast(Dict[str, Any], donor_gate_row.get("reason_counts"))
            if isinstance(donor_gate_row.get("reason_counts"), dict)
            else {}
        )
        donor_gate_row["reason_counts"] = dict(
            sorted((str(code), int(count or 0)) for code, count in donor_reason_counts.items())
        )
        donor_gate_row["block_rate"] = round(donor_blocked_job_count / donor_job_count, 4) if donor_job_count else None
        donor_gate_row["block_rate_among_present"] = (
            round(donor_blocked_job_count / donor_present_job_count, 4) if donor_present_job_count else None
        )
        donor_gate_row["pass_rate_among_present"] = (
            round(donor_passed_job_count / donor_present_job_count, 4) if donor_present_job_count else None
        )
        donor_grounded_gate_breakdown[donor_token] = donor_gate_row

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
            "toc_text_risk_level": toc_text_risk_filter,
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
        "grounded_gate_present_job_count": grounded_gate_present_job_count,
        "grounded_gate_blocked_job_count": grounded_gate_blocked_job_count,
        "grounded_gate_passed_job_count": grounded_gate_passed_job_count,
        "grounded_gate_block_rate": grounded_gate_block_rate,
        "grounded_gate_block_rate_among_present": grounded_gate_block_rate_among_present,
        "grounded_gate_pass_rate_among_present": grounded_gate_pass_rate_among_present,
        "grounded_gate_section_fail_counts": grounded_gate_section_fail_counts,
        "grounded_gate_reason_counts": dict(sorted(grounded_gate_reason_counts.items())),
        "donor_grounded_gate_breakdown": donor_grounded_gate_breakdown,
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
        "toc_text_quality": {
            "issues_total": toc_text_quality_issues_total,
            "placeholder_finding_count": toc_text_quality_placeholder_finding_count,
            "repetition_finding_count": toc_text_quality_repetition_finding_count,
            "risk_counts": toc_text_quality_risk_counts,
            "risk_job_rates": toc_text_quality_risk_job_rates,
            "high_risk_job_count": int(toc_text_quality_risk_counts.get("high") or 0),
            "medium_risk_job_count": int(toc_text_quality_risk_counts.get("medium") or 0),
            "low_risk_job_count": int(toc_text_quality_risk_counts.get("low") or 0),
            "unknown_risk_job_count": int(toc_text_quality_risk_counts.get("unknown") or 0),
            "high_risk_job_rate": toc_text_quality_risk_job_rates.get("high"),
            "placeholder_check_status_counts": toc_text_quality_placeholder_check_status_counts,
            "repetition_check_status_counts": toc_text_quality_repetition_check_status_counts,
        },
        "mel": {
            "indicator_job_count": mel_indicator_job_count,
            "indicator_count_total": mel_indicator_count_total,
            "avg_indicator_count_per_job": (
                round(mel_indicator_count_total / mel_indicator_job_count, 4) if mel_indicator_job_count else None
            ),
            "baseline_coverage_rate": mel_coverage_rates.get("baseline"),
            "target_coverage_rate": mel_coverage_rates.get("target"),
            "frequency_coverage_rate": mel_coverage_rates.get("frequency"),
            "formula_coverage_rate": mel_coverage_rates.get("formula"),
            "definition_coverage_rate": mel_coverage_rates.get("definition"),
            "data_source_coverage_rate": mel_coverage_rates.get("data_source"),
            "disaggregation_coverage_rate": mel_coverage_rates.get("disaggregation"),
            "result_level_coverage_rate": mel_coverage_rates.get("result_level"),
            "smart_field_coverage_rate": mel_smart_field_coverage_rate,
            "baseline_placeholder_count": mel_baseline_placeholder_count,
            "target_placeholder_count": mel_target_placeholder_count,
            "missing_field_counts": mel_missing_field_counts,
            "result_level_counts": mel_result_level_counts_total,
        },
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
            "architect_citation_count_total": architect_citation_count_total,
            "architect_claim_support_citation_count": architect_claim_support_citation_count,
            "architect_claim_support_rate": architect_claim_support_rate,
            "citation_confidence_avg": _avg(citation_summary_rows, "citation_confidence_avg"),
            "citation_type_counts_total": dict(sorted(citation_type_counts_total.items())),
            "architect_citation_type_counts_total": dict(sorted(architect_citation_type_counts_total.items())),
            "mel_citation_type_counts_total": dict(sorted(mel_citation_type_counts_total.items())),
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
            "strategy_reference_citation_count": strategy_reference_citation_count,
            "strategy_reference_citation_rate": strategy_reference_citation_rate,
            "non_retrieval_citation_count": non_retrieval_citation_count,
            "non_retrieval_citation_rate": non_retrieval_citation_rate,
            "retrieval_grounded_citation_count": retrieval_grounded_citation_count,
            "retrieval_grounded_citation_rate": retrieval_grounded_citation_rate,
            "doc_id_present_citation_count": doc_id_present_citation_count,
            "doc_id_present_citation_rate": doc_id_present_citation_rate,
            "retrieval_rank_present_citation_count": retrieval_rank_present_citation_count,
            "retrieval_rank_present_citation_rate": retrieval_rank_present_citation_rate,
            "retrieval_confidence_present_citation_count": retrieval_confidence_present_citation_count,
            "retrieval_confidence_present_citation_rate": retrieval_confidence_present_citation_rate,
            "retrieval_metadata_complete_citation_count": retrieval_metadata_complete_citation_count,
            "retrieval_metadata_complete_citation_rate": retrieval_metadata_complete_citation_rate,
            "architect_doc_id_present_citation_count": architect_doc_id_present_citation_count,
            "architect_doc_id_present_citation_rate": architect_doc_id_present_citation_rate,
            "architect_retrieval_rank_present_citation_count": architect_retrieval_rank_present_citation_count,
            "architect_retrieval_rank_present_citation_rate": architect_retrieval_rank_present_citation_rate,
            "architect_retrieval_confidence_present_citation_count": architect_retrieval_confidence_present_citation_count,
            "architect_retrieval_confidence_present_citation_rate": architect_retrieval_confidence_present_citation_rate,
            "architect_retrieval_metadata_complete_citation_count": architect_retrieval_metadata_complete_citation_count,
            "architect_retrieval_metadata_complete_citation_rate": architect_retrieval_metadata_complete_citation_rate,
            "mel_doc_id_present_citation_count": mel_doc_id_present_citation_count,
            "mel_doc_id_present_citation_rate": mel_doc_id_present_citation_rate,
            "mel_retrieval_rank_present_citation_count": mel_retrieval_rank_present_citation_count,
            "mel_retrieval_rank_present_citation_rate": mel_retrieval_rank_present_citation_rate,
            "mel_retrieval_confidence_present_citation_count": mel_retrieval_confidence_present_citation_count,
            "mel_retrieval_confidence_present_citation_rate": mel_retrieval_confidence_present_citation_rate,
            "mel_retrieval_metadata_complete_citation_count": mel_retrieval_metadata_complete_citation_count,
            "mel_retrieval_metadata_complete_citation_rate": mel_retrieval_metadata_complete_citation_rate,
            "retrieval_expected_mode": retrieval_expected_mode,
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
            "architect_claim_support_rate_avg": _avg(citation_summary_rows, "architect_claim_support_rate"),
        },
        "priority_signal_breakdown": priority_signal_breakdown,
        "donor_weighted_risk_breakdown": donor_weighted_risk_breakdown,
        "donor_grounding_risk_breakdown": donor_grounding_risk_breakdown,
        "donor_needs_revision_counts": donor_needs_revision_counts,
        "donor_open_findings_counts": donor_open_findings_counts,
    }


def public_portfolio_review_workflow_payload(
    jobs_by_id: Dict[str, Dict[str, Any]],
    *,
    donor_id: Optional[str] = None,
    status: Optional[str] = None,
    hitl_enabled: Optional[bool] = None,
    warning_level: Optional[str] = None,
    grounding_risk_level: Optional[str] = None,
    toc_text_risk_level: Optional[str] = None,
    event_type: Optional[str] = None,
    finding_id: Optional[str] = None,
    finding_code: Optional[str] = None,
    finding_section: Optional[str] = None,
    comment_status: Optional[str] = None,
    workflow_state: Optional[str] = None,
    overdue_after_hours: int = REVIEW_WORKFLOW_OVERDUE_DEFAULT_HOURS,
) -> Dict[str, Any]:
    warning_level_filter = _normalize_warning_level_filter(warning_level)
    grounding_risk_filter = _normalize_grounding_risk_filter(grounding_risk_level)
    toc_text_risk_filter = _normalize_toc_text_risk_filter(toc_text_risk_level)
    workflow_state_filter = _normalize_review_workflow_state_filter(workflow_state)
    event_type_filter = str(event_type or "").strip() or None
    finding_id_filter = str(finding_id or "").strip() or None
    finding_code_filter = str(finding_code or "").strip() or None
    finding_section_filter = str(finding_section or "").strip().lower() or None
    comment_status_filter = str(comment_status or "").strip().lower() or None
    overdue_after_hours_value = (
        int(overdue_after_hours)
        if isinstance(overdue_after_hours, int) and overdue_after_hours > 0
        else REVIEW_WORKFLOW_OVERDUE_DEFAULT_HOURS
    )

    filtered: list[tuple[str, Dict[str, Any]]] = []
    for job_id, job in jobs_by_id.items():
        if not isinstance(job, dict):
            continue
        job_status = str(job.get("status") or "")
        job_donor = _job_donor_id(job)
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
        if toc_text_risk_filter is not None and _job_toc_text_risk_level(job) != toc_text_risk_filter:
            continue
        filtered.append((str(job_id), job))

    finding_status_counts: Dict[str, int] = {"open": 0, "acknowledged": 0, "resolved": 0}
    finding_severity_counts: Dict[str, int] = {"high": 0, "medium": 0, "low": 0}
    comment_status_counts: Dict[str, int] = {}
    timeline_event_type_counts: Dict[str, int] = {}
    timeline_kind_counts: Dict[str, int] = {}
    timeline_section_counts: Dict[str, int] = {}
    timeline_status_counts: Dict[str, int] = {}
    donor_event_counts: Dict[str, int] = {}
    job_event_counts: Dict[str, int] = {}

    finding_count = 0
    comment_count = 0
    linked_comment_count = 0
    orphan_linked_comment_count = 0
    open_finding_count = 0
    acknowledged_finding_count = 0
    resolved_finding_count = 0
    pending_finding_count = 0
    overdue_finding_count = 0
    open_comment_count = 0
    resolved_comment_count = 0
    pending_comment_count = 0
    overdue_comment_count = 0
    timeline_event_count = 0
    jobs_with_activity = 0
    jobs_with_overdue = 0
    activity_dt_values: list[datetime] = []

    latest_timeline_all: list[Dict[str, Any]] = []
    latest_timeline_limit = 200

    def _merge_counts(target: Dict[str, int], source: Any) -> None:
        if not isinstance(source, dict):
            return
        for key, count in source.items():
            token = str(key or "").strip().lower() or "unknown"
            target[token] = int(target.get(token) or 0) + _coerce_int(count, default=0)

    for job_id, job in filtered:
        workflow_payload = public_job_review_workflow_payload(
            job_id,
            job,
            event_type=event_type_filter,
            finding_id=finding_id_filter,
            finding_code=finding_code_filter,
            finding_section=finding_section_filter,
            comment_status=comment_status_filter,
            workflow_state=workflow_state_filter,
            overdue_after_hours=overdue_after_hours_value,
        )
        summary = workflow_payload.get("summary")
        summary_dict = summary if isinstance(summary, dict) else {}
        timeline = workflow_payload.get("timeline")
        timeline_rows = [row for row in timeline if isinstance(row, dict)] if isinstance(timeline, list) else []

        donor_token = _job_donor_id(job, default="unknown")
        job_timeline_event_count = _coerce_int(
            summary_dict.get("timeline_event_count"),
            default=len(timeline_rows),
        )
        job_event_counts[str(job_id)] = job_timeline_event_count
        donor_event_counts[donor_token] = int(donor_event_counts.get(donor_token) or 0) + job_timeline_event_count
        timeline_event_count += job_timeline_event_count
        if job_timeline_event_count > 0:
            jobs_with_activity += 1

        job_overdue_total = _coerce_int(summary_dict.get("overdue_finding_count")) + _coerce_int(
            summary_dict.get("overdue_comment_count")
        )
        if job_overdue_total > 0:
            jobs_with_overdue += 1

        finding_count += _coerce_int(summary_dict.get("finding_count"))
        comment_count += _coerce_int(summary_dict.get("comment_count"))
        linked_comment_count += _coerce_int(summary_dict.get("linked_comment_count"))
        orphan_linked_comment_count += _coerce_int(summary_dict.get("orphan_linked_comment_count"))
        open_finding_count += _coerce_int(summary_dict.get("open_finding_count"))
        acknowledged_finding_count += _coerce_int(summary_dict.get("acknowledged_finding_count"))
        resolved_finding_count += _coerce_int(summary_dict.get("resolved_finding_count"))
        pending_finding_count += _coerce_int(summary_dict.get("pending_finding_count"))
        overdue_finding_count += _coerce_int(summary_dict.get("overdue_finding_count"))
        open_comment_count += _coerce_int(summary_dict.get("open_comment_count"))
        resolved_comment_count += _coerce_int(summary_dict.get("resolved_comment_count"))
        pending_comment_count += _coerce_int(summary_dict.get("pending_comment_count"))
        overdue_comment_count += _coerce_int(summary_dict.get("overdue_comment_count"))

        _merge_counts(finding_status_counts, summary_dict.get("finding_status_counts"))
        _merge_counts(finding_severity_counts, summary_dict.get("finding_severity_counts"))
        _merge_counts(comment_status_counts, summary_dict.get("comment_status_counts"))

        summary_last_activity_dt = _parse_event_ts(summary_dict.get("last_activity_at"))
        if summary_last_activity_dt is not None:
            activity_dt_values.append(summary_last_activity_dt)

        for row in timeline_rows:
            event_type_key = str(row.get("type") or "").strip().lower() or "unknown"
            timeline_event_type_counts[event_type_key] = int(timeline_event_type_counts.get(event_type_key) or 0) + 1

            kind_key = str(row.get("kind") or "").strip().lower() or "unknown"
            timeline_kind_counts[kind_key] = int(timeline_kind_counts.get(kind_key) or 0) + 1

            section_key = str(row.get("section") or "").strip().lower() or "unknown"
            timeline_section_counts[section_key] = int(timeline_section_counts.get(section_key) or 0) + 1

            status_key = str(row.get("status") or "").strip().lower() or "unknown"
            timeline_status_counts[status_key] = int(timeline_status_counts.get(status_key) or 0) + 1

            row_ts_dt = _parse_event_ts(row.get("ts"))
            if row_ts_dt is not None:
                activity_dt_values.append(row_ts_dt)

            timeline_item = dict(row)
            timeline_item["job_id"] = str(job_id)
            timeline_item["donor_id"] = donor_token
            latest_timeline_all.append(timeline_item)

    latest_timeline_all.sort(key=lambda row: str(row.get("ts") or ""), reverse=True)
    latest_timeline = latest_timeline_all[:latest_timeline_limit]
    latest_timeline_truncated = len(latest_timeline_all) > latest_timeline_limit

    top_event_type = None
    top_event_type_count = -1
    for key, total in timeline_event_type_counts.items():
        if int(total) > top_event_type_count:
            top_event_type = key
            top_event_type_count = int(total)

    top_donor_id = None
    top_donor_event_count = -1
    for key, total in donor_event_counts.items():
        if int(total) > top_donor_event_count:
            top_donor_id = key
            top_donor_event_count = int(total)

    last_activity_at = max(activity_dt_values).isoformat() if activity_dt_values else None
    job_count = len(filtered)
    jobs_without_activity = max(0, job_count - jobs_with_activity)
    jobs_without_overdue = max(0, job_count - jobs_with_overdue)

    return {
        "job_count": job_count,
        "jobs_with_activity": jobs_with_activity,
        "jobs_without_activity": jobs_without_activity,
        "jobs_with_overdue": jobs_with_overdue,
        "jobs_without_overdue": jobs_without_overdue,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "filters": {
            "donor_id": donor_id,
            "status": status,
            "hitl_enabled": hitl_enabled,
            "warning_level": warning_level_filter,
            "grounding_risk_level": grounding_risk_filter,
            "toc_text_risk_level": toc_text_risk_filter,
            "event_type": event_type_filter,
            "finding_id": finding_id_filter,
            "finding_code": finding_code_filter,
            "finding_section": finding_section_filter,
            "comment_status": comment_status_filter,
            "workflow_state": workflow_state_filter,
            "overdue_after_hours": overdue_after_hours_value,
        },
        "summary": {
            "finding_count": finding_count,
            "comment_count": comment_count,
            "linked_comment_count": linked_comment_count,
            "orphan_linked_comment_count": orphan_linked_comment_count,
            "open_finding_count": open_finding_count,
            "acknowledged_finding_count": acknowledged_finding_count,
            "resolved_finding_count": resolved_finding_count,
            "pending_finding_count": pending_finding_count,
            "overdue_finding_count": overdue_finding_count,
            "open_comment_count": open_comment_count,
            "resolved_comment_count": resolved_comment_count,
            "pending_comment_count": pending_comment_count,
            "overdue_comment_count": overdue_comment_count,
            "finding_status_counts": finding_status_counts,
            "finding_severity_counts": finding_severity_counts,
            "comment_status_counts": dict(sorted(comment_status_counts.items())),
            "timeline_event_count": timeline_event_count,
            "last_activity_at": last_activity_at,
        },
        "top_event_type": top_event_type,
        "top_event_type_count": top_event_type_count if top_event_type is not None else None,
        "top_donor_id": top_donor_id,
        "top_donor_event_count": top_donor_event_count if top_donor_id is not None else None,
        "timeline_event_type_counts": dict(sorted(timeline_event_type_counts.items())),
        "timeline_kind_counts": dict(sorted(timeline_kind_counts.items())),
        "timeline_section_counts": dict(sorted(timeline_section_counts.items())),
        "timeline_status_counts": dict(sorted(timeline_status_counts.items())),
        "donor_event_counts": dict(sorted(donor_event_counts.items())),
        "job_event_counts": dict(sorted(job_event_counts.items())),
        "latest_timeline_limit": latest_timeline_limit,
        "latest_timeline_truncated": latest_timeline_truncated,
        "latest_timeline": latest_timeline,
    }


def public_portfolio_review_workflow_sla_payload(
    jobs_by_id: Dict[str, Dict[str, Any]],
    *,
    donor_id: Optional[str] = None,
    status: Optional[str] = None,
    hitl_enabled: Optional[bool] = None,
    warning_level: Optional[str] = None,
    grounding_risk_level: Optional[str] = None,
    toc_text_risk_level: Optional[str] = None,
    finding_id: Optional[str] = None,
    finding_code: Optional[str] = None,
    finding_section: Optional[str] = None,
    comment_status: Optional[str] = None,
    workflow_state: Optional[str] = None,
    overdue_after_hours: int = REVIEW_WORKFLOW_OVERDUE_DEFAULT_HOURS,
    top_limit: int = 10,
) -> Dict[str, Any]:
    warning_level_filter = _normalize_warning_level_filter(warning_level)
    grounding_risk_filter = _normalize_grounding_risk_filter(grounding_risk_level)
    toc_text_risk_filter = _normalize_toc_text_risk_filter(toc_text_risk_level)
    workflow_state_filter = _normalize_review_workflow_state_filter(workflow_state)
    finding_id_filter = str(finding_id or "").strip() or None
    finding_code_filter = str(finding_code or "").strip() or None
    finding_section_filter = str(finding_section or "").strip().lower() or None
    comment_status_filter = str(comment_status or "").strip().lower() or None
    overdue_after_hours_value = (
        int(overdue_after_hours)
        if isinstance(overdue_after_hours, int) and overdue_after_hours > 0
        else REVIEW_WORKFLOW_OVERDUE_DEFAULT_HOURS
    )
    top_n = 1
    if isinstance(top_limit, int):
        top_n = max(1, top_limit)

    filtered: list[tuple[str, Dict[str, Any]]] = []
    for job_id, job in jobs_by_id.items():
        if not isinstance(job, dict):
            continue
        job_status = str(job.get("status") or "")
        job_donor = _job_donor_id(job)
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
        if toc_text_risk_filter is not None and _job_toc_text_risk_level(job) != toc_text_risk_filter:
            continue
        filtered.append((str(job_id), job))

    finding_total = 0
    comment_total = 0
    unresolved_finding_count = 0
    unresolved_comment_count = 0
    unresolved_total = 0
    overdue_finding_count = 0
    overdue_comment_count = 0
    overdue_total = 0
    jobs_with_overdue = 0
    overdue_by_severity: Dict[str, int] = {}
    overdue_by_section: Dict[str, int] = {}
    donor_overdue_counts: Dict[str, int] = {}
    job_overdue_counts: Dict[str, int] = {}
    overdue_rows_all: list[Dict[str, Any]] = []

    def _merge_counts(target: Dict[str, int], source: Any) -> None:
        if not isinstance(source, dict):
            return
        for key, count in source.items():
            token = str(key or "").strip().lower() or "unknown"
            target[token] = int(target.get(token) or 0) + _coerce_int(count, default=0)

    for job_id, job in filtered:
        snapshot = _review_workflow_sla_snapshot(
            job_id,
            job,
            finding_id=finding_id_filter,
            finding_code=finding_code_filter,
            finding_section=finding_section_filter,
            comment_status=comment_status_filter,
            workflow_state=workflow_state_filter,
            overdue_after_hours=overdue_after_hours_value,
        )
        job_overdue_total = _coerce_int(snapshot.get("overdue_total"))
        job_overdue_counts[str(job_id)] = job_overdue_total
        if job_overdue_total > 0:
            jobs_with_overdue += 1

        donor_token = _job_donor_id(job, default="unknown")
        donor_overdue_counts[donor_token] = int(donor_overdue_counts.get(donor_token) or 0) + job_overdue_total

        finding_total += _coerce_int(snapshot.get("finding_total"))
        comment_total += _coerce_int(snapshot.get("comment_total"))
        unresolved_finding_count += _coerce_int(snapshot.get("unresolved_finding_count"))
        unresolved_comment_count += _coerce_int(snapshot.get("unresolved_comment_count"))
        unresolved_total += _coerce_int(snapshot.get("unresolved_total"))
        overdue_finding_count += _coerce_int(snapshot.get("overdue_finding_count"))
        overdue_comment_count += _coerce_int(snapshot.get("overdue_comment_count"))
        overdue_total += job_overdue_total

        _merge_counts(overdue_by_severity, snapshot.get("overdue_by_severity"))
        _merge_counts(overdue_by_section, snapshot.get("overdue_by_section"))

        overdue_rows = snapshot.get("overdue_rows")
        overdue_rows_list = (
            [item for item in overdue_rows if isinstance(item, dict)] if isinstance(overdue_rows, list) else []
        )
        for row in overdue_rows_list:
            current = dict(row)
            current["job_id"] = str(job_id)
            current["donor_id"] = donor_token
            overdue_rows_all.append(current)

    def _sort_key(item: Dict[str, Any]) -> tuple[float, str]:
        overdue_hours = item.get("overdue_hours")
        overdue_hours_value = -1.0
        if isinstance(overdue_hours, (int, float, str)):
            try:
                overdue_hours_value = float(overdue_hours)
            except (TypeError, ValueError):
                overdue_hours_value = -1.0
        due_at = str(item.get("due_at") or "")
        return overdue_hours_value, due_at

    overdue_rows_all.sort(key=_sort_key, reverse=True)
    top_overdue = overdue_rows_all[:top_n]
    oldest_overdue = top_overdue[0] if top_overdue else None
    breach_rate = (overdue_total / unresolved_total) if unresolved_total else None
    job_count = len(filtered)
    jobs_without_overdue = max(0, job_count - jobs_with_overdue)

    top_donor_id = None
    top_donor_overdue_count = -1
    for key, total in donor_overdue_counts.items():
        if int(total) > top_donor_overdue_count:
            top_donor_id = key
            top_donor_overdue_count = int(total)

    return {
        "job_count": job_count,
        "jobs_with_overdue": jobs_with_overdue,
        "jobs_without_overdue": jobs_without_overdue,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "filters": {
            "donor_id": donor_id,
            "status": status,
            "hitl_enabled": hitl_enabled,
            "warning_level": warning_level_filter,
            "grounding_risk_level": grounding_risk_filter,
            "toc_text_risk_level": toc_text_risk_filter,
            "finding_id": finding_id_filter,
            "finding_code": finding_code_filter,
            "finding_section": finding_section_filter,
            "comment_status": comment_status_filter,
            "workflow_state": workflow_state_filter,
            "overdue_after_hours": overdue_after_hours_value,
            "top_limit": top_n,
        },
        "overdue_after_hours": overdue_after_hours_value,
        "finding_total": finding_total,
        "comment_total": comment_total,
        "unresolved_finding_count": unresolved_finding_count,
        "unresolved_comment_count": unresolved_comment_count,
        "unresolved_total": unresolved_total,
        "overdue_finding_count": overdue_finding_count,
        "overdue_comment_count": overdue_comment_count,
        "overdue_total": overdue_total,
        "breach_rate": round(breach_rate, 4) if breach_rate is not None else None,
        "overdue_by_severity": dict(sorted(overdue_by_severity.items())),
        "overdue_by_section": dict(sorted(overdue_by_section.items())),
        "oldest_overdue": oldest_overdue,
        "top_overdue": top_overdue,
        "top_donor_id": top_donor_id,
        "top_donor_overdue_count": top_donor_overdue_count if top_donor_id is not None else None,
        "donor_overdue_counts": dict(sorted(donor_overdue_counts.items())),
        "job_overdue_counts": dict(sorted(job_overdue_counts.items())),
    }


def public_portfolio_review_workflow_sla_hotspots_payload(
    jobs_by_id: Dict[str, Dict[str, Any]],
    *,
    donor_id: Optional[str] = None,
    status: Optional[str] = None,
    hitl_enabled: Optional[bool] = None,
    warning_level: Optional[str] = None,
    grounding_risk_level: Optional[str] = None,
    toc_text_risk_level: Optional[str] = None,
    finding_id: Optional[str] = None,
    finding_code: Optional[str] = None,
    finding_section: Optional[str] = None,
    comment_status: Optional[str] = None,
    workflow_state: Optional[str] = None,
    overdue_after_hours: int = REVIEW_WORKFLOW_OVERDUE_DEFAULT_HOURS,
    top_limit: int = 10,
    hotspot_kind: Optional[str] = None,
    hotspot_severity: Optional[str] = None,
    min_overdue_hours: Optional[float] = None,
) -> Dict[str, Any]:
    warning_level_filter = _normalize_warning_level_filter(warning_level)
    grounding_risk_filter = _normalize_grounding_risk_filter(grounding_risk_level)
    toc_text_risk_filter = _normalize_toc_text_risk_filter(toc_text_risk_level)
    workflow_state_filter = _normalize_review_workflow_state_filter(workflow_state)
    finding_id_filter = str(finding_id or "").strip() or None
    finding_code_filter = str(finding_code or "").strip() or None
    finding_section_filter = str(finding_section or "").strip().lower() or None
    comment_status_filter = str(comment_status or "").strip().lower() or None
    overdue_after_hours_value = (
        int(overdue_after_hours)
        if isinstance(overdue_after_hours, int) and overdue_after_hours > 0
        else REVIEW_WORKFLOW_OVERDUE_DEFAULT_HOURS
    )
    top_n = max(1, int(top_limit or 1))
    hotspot_kind_filter = str(hotspot_kind or "").strip().lower() or None
    if hotspot_kind_filter not in {None, "finding", "comment"}:
        hotspot_kind_filter = None
    hotspot_severity_filter = str(hotspot_severity or "").strip().lower() or None
    if hotspot_severity_filter not in {None, "high", "medium", "low", "unknown"}:
        hotspot_severity_filter = None
    min_overdue_hours_value: Optional[float] = None
    if isinstance(min_overdue_hours, (int, float)):
        min_overdue_hours_value = max(0.0, float(min_overdue_hours))

    filtered: list[tuple[str, Dict[str, Any]]] = []
    for job_id, job in jobs_by_id.items():
        if not isinstance(job, dict):
            continue
        job_status = str(job.get("status") or "")
        job_donor = _job_donor_id(job)
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
        if toc_text_risk_filter is not None and _job_toc_text_risk_level(job) != toc_text_risk_filter:
            continue
        filtered.append((str(job_id), job))

    overdue_rows_all: list[Dict[str, Any]] = []
    donor_hotspot_counts: Dict[str, int] = {}
    job_hotspot_counts: Dict[str, int] = {}
    jobs_with_overdue = 0

    for job_id, job in filtered:
        snapshot = _review_workflow_sla_snapshot(
            job_id,
            job,
            finding_id=finding_id_filter,
            finding_code=finding_code_filter,
            finding_section=finding_section_filter,
            comment_status=comment_status_filter,
            workflow_state=workflow_state_filter,
            overdue_after_hours=overdue_after_hours_value,
        )
        overdue_rows = snapshot.get("overdue_rows")
        overdue_rows_list = (
            [item for item in overdue_rows if isinstance(item, dict)] if isinstance(overdue_rows, list) else []
        )
        donor_token = _job_donor_id(job, default="unknown")
        job_matches = 0
        for row in overdue_rows_list:
            current = dict(row)
            row_kind = str(current.get("kind") or "").strip().lower() or None
            row_severity = str(current.get("severity") or "").strip().lower() or "unknown"
            row_overdue_hours_raw = current.get("overdue_hours")
            row_overdue_hours: Optional[float] = None
            if isinstance(row_overdue_hours_raw, (int, float, str)):
                try:
                    row_overdue_hours = float(row_overdue_hours_raw)
                except (TypeError, ValueError):
                    row_overdue_hours = None

            if hotspot_kind_filter and row_kind != hotspot_kind_filter:
                continue
            if hotspot_severity_filter and row_severity != hotspot_severity_filter:
                continue
            if min_overdue_hours_value is not None and (
                row_overdue_hours is None or row_overdue_hours < min_overdue_hours_value
            ):
                continue

            current["job_id"] = str(job_id)
            current["donor_id"] = donor_token
            overdue_rows_all.append(current)
            job_matches += 1

        job_hotspot_counts[str(job_id)] = job_matches
        if job_matches > 0:
            jobs_with_overdue += 1
        donor_hotspot_counts[donor_token] = int(donor_hotspot_counts.get(donor_token) or 0) + job_matches

    def _sort_key(item: Dict[str, Any]) -> tuple[float, str]:
        overdue_hours = item.get("overdue_hours")
        overdue_hours_value = -1.0
        if isinstance(overdue_hours, (int, float, str)):
            try:
                overdue_hours_value = float(overdue_hours)
            except (TypeError, ValueError):
                overdue_hours_value = -1.0
        due_at = str(item.get("due_at") or "")
        return overdue_hours_value, due_at

    overdue_rows_all.sort(key=_sort_key, reverse=True)
    top_overdue = overdue_rows_all[:top_n]
    oldest_overdue = top_overdue[0] if top_overdue else None
    total_overdue_items = len(overdue_rows_all)
    overdue_hours_values: list[float] = []
    for item in overdue_rows_all:
        raw_value = item.get("overdue_hours")
        if isinstance(raw_value, (int, float)):
            overdue_hours_values.append(float(raw_value))
    max_overdue_hours = max(overdue_hours_values) if overdue_hours_values else None
    avg_overdue_hours = (sum(overdue_hours_values) / len(overdue_hours_values)) if overdue_hours_values else None

    top_donor_id = None
    top_donor_overdue_count = -1
    for key, total in donor_hotspot_counts.items():
        if int(total) > top_donor_overdue_count:
            top_donor_id = key
            top_donor_overdue_count = int(total)

    job_count = len(filtered)
    jobs_without_overdue = max(0, job_count - jobs_with_overdue)

    return {
        "job_count": job_count,
        "jobs_with_overdue": jobs_with_overdue,
        "jobs_without_overdue": jobs_without_overdue,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "filters": {
            "donor_id": donor_id,
            "status": status,
            "hitl_enabled": hitl_enabled,
            "warning_level": warning_level_filter,
            "grounding_risk_level": grounding_risk_filter,
            "toc_text_risk_level": toc_text_risk_filter,
            "finding_id": finding_id_filter,
            "finding_code": finding_code_filter,
            "finding_section": finding_section_filter,
            "comment_status": comment_status_filter,
            "workflow_state": workflow_state_filter,
            "overdue_after_hours": overdue_after_hours_value,
            "top_limit": top_n,
            "hotspot_kind": hotspot_kind_filter,
            "hotspot_severity": hotspot_severity_filter,
            "min_overdue_hours": min_overdue_hours_value,
        },
        "overdue_after_hours": overdue_after_hours_value,
        "top_limit": top_n,
        "hotspot_count": len(top_overdue),
        "total_overdue_items": total_overdue_items,
        "max_overdue_hours": (round(max_overdue_hours, 3) if max_overdue_hours is not None else None),
        "avg_overdue_hours": (round(avg_overdue_hours, 3) if avg_overdue_hours is not None else None),
        "oldest_overdue": oldest_overdue,
        "top_overdue": top_overdue,
        "top_donor_id": top_donor_id,
        "top_donor_overdue_count": top_donor_overdue_count if top_donor_id is not None else None,
        "donor_hotspot_counts": dict(sorted(donor_hotspot_counts.items())),
        "job_hotspot_counts": dict(sorted(job_hotspot_counts.items())),
    }


def public_portfolio_review_workflow_sla_hotspots_trends_payload(
    jobs_by_id: Dict[str, Dict[str, Any]],
    *,
    donor_id: Optional[str] = None,
    status: Optional[str] = None,
    hitl_enabled: Optional[bool] = None,
    warning_level: Optional[str] = None,
    grounding_risk_level: Optional[str] = None,
    toc_text_risk_level: Optional[str] = None,
    finding_id: Optional[str] = None,
    finding_code: Optional[str] = None,
    finding_section: Optional[str] = None,
    comment_status: Optional[str] = None,
    workflow_state: Optional[str] = None,
    overdue_after_hours: int = REVIEW_WORKFLOW_OVERDUE_DEFAULT_HOURS,
    top_limit: int = 10,
    hotspot_kind: Optional[str] = None,
    hotspot_severity: Optional[str] = None,
    min_overdue_hours: Optional[float] = None,
) -> Dict[str, Any]:
    warning_level_filter = _normalize_warning_level_filter(warning_level)
    grounding_risk_filter = _normalize_grounding_risk_filter(grounding_risk_level)
    toc_text_risk_filter = _normalize_toc_text_risk_filter(toc_text_risk_level)
    workflow_state_filter = _normalize_review_workflow_state_filter(workflow_state)
    finding_id_filter = str(finding_id or "").strip() or None
    finding_code_filter = str(finding_code or "").strip() or None
    finding_section_filter = str(finding_section or "").strip().lower() or None
    comment_status_filter = str(comment_status or "").strip().lower() or None
    overdue_after_hours_value = (
        int(overdue_after_hours)
        if isinstance(overdue_after_hours, int) and overdue_after_hours > 0
        else REVIEW_WORKFLOW_OVERDUE_DEFAULT_HOURS
    )
    top_n = max(1, int(top_limit or 1))
    hotspot_kind_filter = str(hotspot_kind or "").strip().lower() or None
    if hotspot_kind_filter not in {None, "finding", "comment"}:
        hotspot_kind_filter = None
    hotspot_severity_filter = str(hotspot_severity or "").strip().lower() or None
    if hotspot_severity_filter not in {None, "high", "medium", "low", "unknown"}:
        hotspot_severity_filter = None
    min_overdue_hours_value: Optional[float] = None
    if isinstance(min_overdue_hours, (int, float)):
        min_overdue_hours_value = max(0.0, float(min_overdue_hours))

    filtered: list[tuple[str, Dict[str, Any]]] = []
    for job_id, job in jobs_by_id.items():
        if not isinstance(job, dict):
            continue
        job_status = str(job.get("status") or "")
        job_donor = _job_donor_id(job)
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
        if toc_text_risk_filter is not None and _job_toc_text_risk_level(job) != toc_text_risk_filter:
            continue
        filtered.append((str(job_id), job))

    total_bucket_counts: Dict[str, int] = {}
    severity_bucket_counts: Dict[str, Dict[str, int]] = {}
    section_bucket_counts: Dict[str, Dict[str, int]] = {}
    kind_bucket_counts: Dict[str, Dict[str, int]] = {}
    donor_bucket_counts: Dict[str, Dict[str, int]] = {}
    donor_hotspot_counts: Dict[str, int] = {}
    job_hotspot_counts: Dict[str, int] = {}
    jobs_with_overdue = 0
    all_hotspots: list[Dict[str, Any]] = []

    for job_id, job in filtered:
        snapshot = _review_workflow_sla_snapshot(
            job_id,
            job,
            finding_id=finding_id_filter,
            finding_code=finding_code_filter,
            finding_section=finding_section_filter,
            comment_status=comment_status_filter,
            workflow_state=workflow_state_filter,
            overdue_after_hours=overdue_after_hours_value,
        )
        overdue_rows = snapshot.get("overdue_rows")
        overdue_rows_list = (
            [item for item in overdue_rows if isinstance(item, dict)] if isinstance(overdue_rows, list) else []
        )
        donor_token = _job_donor_id(job, default="unknown")
        donor_buckets = donor_bucket_counts.setdefault(donor_token, {})
        job_matches = 0

        for row in overdue_rows_list:
            current = dict(row)
            row_kind = str(current.get("kind") or "").strip().lower() or "unknown"
            row_severity = str(current.get("severity") or "").strip().lower() or "unknown"
            row_section = str(current.get("section") or "").strip().lower() or "unknown"
            row_overdue_hours_raw = current.get("overdue_hours")
            row_overdue_hours: Optional[float] = None
            if isinstance(row_overdue_hours_raw, (int, float, str)):
                try:
                    row_overdue_hours = float(row_overdue_hours_raw)
                except (TypeError, ValueError):
                    row_overdue_hours = None

            if hotspot_kind_filter and row_kind != hotspot_kind_filter:
                continue
            if hotspot_severity_filter and row_severity != hotspot_severity_filter:
                continue
            if min_overdue_hours_value is not None and (
                row_overdue_hours is None or row_overdue_hours < min_overdue_hours_value
            ):
                continue

            due_dt = _parse_event_ts(current.get("due_at"))
            bucket = due_dt.date().isoformat() if due_dt is not None else "unknown"
            total_bucket_counts[bucket] = int(total_bucket_counts.get(bucket) or 0) + 1

            severity_counts = severity_bucket_counts.setdefault(row_severity, {})
            severity_counts[bucket] = int(severity_counts.get(bucket) or 0) + 1

            section_counts = section_bucket_counts.setdefault(row_section, {})
            section_counts[bucket] = int(section_counts.get(bucket) or 0) + 1

            kind_counts = kind_bucket_counts.setdefault(row_kind, {})
            kind_counts[bucket] = int(kind_counts.get(bucket) or 0) + 1

            donor_buckets[bucket] = int(donor_buckets.get(bucket) or 0) + 1

            current["job_id"] = str(job_id)
            current["donor_id"] = donor_token
            all_hotspots.append(current)
            job_matches += 1

        job_hotspot_counts[str(job_id)] = job_matches
        if job_matches > 0:
            jobs_with_overdue += 1
        donor_hotspot_counts[donor_token] = int(donor_hotspot_counts.get(donor_token) or 0) + job_matches

    def _series_rows(counts: Dict[str, int]) -> list[Dict[str, Any]]:
        return [{"bucket": bucket, "count": int(counts.get(bucket) or 0)} for bucket in sorted(counts.keys())]

    total_series = _series_rows(total_bucket_counts)

    severity_series: Dict[str, list[Dict[str, Any]]] = {}
    for level in ("high", "medium", "low", "unknown"):
        severity_series[level] = _series_rows(severity_bucket_counts.get(level, {}))
    for level in sorted(severity_bucket_counts.keys()):
        if level in severity_series:
            continue
        severity_series[level] = _series_rows(severity_bucket_counts.get(level, {}))

    section_series: Dict[str, list[Dict[str, Any]]] = {}
    for section in sorted(section_bucket_counts.keys()):
        section_series[section] = _series_rows(section_bucket_counts.get(section, {}))

    kind_series: Dict[str, list[Dict[str, Any]]] = {}
    for kind in sorted(kind_bucket_counts.keys()):
        kind_series[kind] = _series_rows(kind_bucket_counts.get(kind, {}))

    donor_series: Dict[str, list[Dict[str, Any]]] = {}
    for donor_key in sorted(donor_bucket_counts.keys()):
        donor_series[donor_key] = _series_rows(donor_bucket_counts.get(donor_key, {}))

    dated_buckets = []
    for point in total_series:
        bucket = str(point.get("bucket") or "").strip()
        try:
            datetime.strptime(bucket, "%Y-%m-%d")
            dated_buckets.append(bucket)
        except ValueError:
            continue
    time_window_start = dated_buckets[0] if dated_buckets else None
    time_window_end = dated_buckets[-1] if dated_buckets else None

    def _top_key_by_series(series_map: Dict[str, list[Dict[str, Any]]]) -> tuple[Optional[str], Optional[int]]:
        top_key = None
        top_total = -1
        for key, rows in series_map.items():
            current_total = sum(int(row.get("count") or 0) for row in rows if isinstance(row, dict))
            if current_total > top_total:
                top_key = key
                top_total = current_total
        return top_key, (top_total if top_key is not None else None)

    top_kind, top_kind_count = _top_key_by_series(kind_series)
    top_severity, top_severity_count = _top_key_by_series(severity_series)
    top_section, top_section_count = _top_key_by_series(section_series)

    top_donor_id = None
    top_donor_hotspot_count = -1
    for key, total in donor_hotspot_counts.items():
        if int(total) > top_donor_hotspot_count:
            top_donor_id = key
            top_donor_hotspot_count = int(total)

    all_hotspots.sort(
        key=lambda row: (
            float(row.get("overdue_hours") or -1.0) if isinstance(row.get("overdue_hours"), (int, float)) else -1.0,
            str(row.get("due_at") or ""),
        ),
        reverse=True,
    )
    top_overdue = all_hotspots[:top_n]
    oldest_overdue = top_overdue[0] if top_overdue else None

    job_count = len(filtered)
    jobs_without_overdue = max(0, job_count - jobs_with_overdue)
    hotspot_count_total = len(all_hotspots)

    return {
        "job_count": job_count,
        "jobs_with_overdue": jobs_with_overdue,
        "jobs_without_overdue": jobs_without_overdue,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "filters": {
            "donor_id": donor_id,
            "status": status,
            "hitl_enabled": hitl_enabled,
            "warning_level": warning_level_filter,
            "grounding_risk_level": grounding_risk_filter,
            "toc_text_risk_level": toc_text_risk_filter,
            "finding_id": finding_id_filter,
            "finding_code": finding_code_filter,
            "finding_section": finding_section_filter,
            "comment_status": comment_status_filter,
            "workflow_state": workflow_state_filter,
            "overdue_after_hours": overdue_after_hours_value,
            "top_limit": top_n,
            "hotspot_kind": hotspot_kind_filter,
            "hotspot_severity": hotspot_severity_filter,
            "min_overdue_hours": min_overdue_hours_value,
        },
        "bucket_granularity": "day",
        "bucket_count": len(total_series),
        "time_window_start": time_window_start,
        "time_window_end": time_window_end,
        "hotspot_count_total": hotspot_count_total,
        "avg_hotspots_per_job": (round(hotspot_count_total / job_count, 3) if job_count else None),
        "avg_hotspots_per_active_job": (
            round(hotspot_count_total / jobs_with_overdue, 3) if jobs_with_overdue else None
        ),
        "top_kind": top_kind,
        "top_kind_count": top_kind_count,
        "top_severity": top_severity,
        "top_severity_count": top_severity_count,
        "top_section": top_section,
        "top_section_count": top_section_count,
        "top_donor_id": top_donor_id,
        "top_donor_hotspot_count": top_donor_hotspot_count if top_donor_id is not None else None,
        "donor_hotspot_counts": dict(sorted(donor_hotspot_counts.items())),
        "job_hotspot_counts": dict(sorted(job_hotspot_counts.items())),
        "oldest_overdue": oldest_overdue,
        "top_overdue": top_overdue,
        "total_series": total_series,
        "severity_series": severity_series,
        "section_series": section_series,
        "kind_series": kind_series,
        "donor_series": donor_series,
    }


def public_portfolio_review_workflow_trends_payload(
    jobs_by_id: Dict[str, Dict[str, Any]],
    *,
    donor_id: Optional[str] = None,
    status: Optional[str] = None,
    hitl_enabled: Optional[bool] = None,
    warning_level: Optional[str] = None,
    grounding_risk_level: Optional[str] = None,
    toc_text_risk_level: Optional[str] = None,
    event_type: Optional[str] = None,
    finding_id: Optional[str] = None,
    finding_code: Optional[str] = None,
    finding_section: Optional[str] = None,
    comment_status: Optional[str] = None,
    workflow_state: Optional[str] = None,
    overdue_after_hours: int = REVIEW_WORKFLOW_OVERDUE_DEFAULT_HOURS,
) -> Dict[str, Any]:
    warning_level_filter = _normalize_warning_level_filter(warning_level)
    grounding_risk_filter = _normalize_grounding_risk_filter(grounding_risk_level)
    toc_text_risk_filter = _normalize_toc_text_risk_filter(toc_text_risk_level)
    workflow_state_filter = _normalize_review_workflow_state_filter(workflow_state)
    event_type_filter = str(event_type or "").strip() or None
    finding_id_filter = str(finding_id or "").strip() or None
    finding_code_filter = str(finding_code or "").strip() or None
    finding_section_filter = str(finding_section or "").strip().lower() or None
    comment_status_filter = str(comment_status or "").strip().lower() or None
    overdue_after_hours_value = (
        int(overdue_after_hours)
        if isinstance(overdue_after_hours, int) and overdue_after_hours > 0
        else REVIEW_WORKFLOW_OVERDUE_DEFAULT_HOURS
    )

    filtered: list[tuple[str, Dict[str, Any]]] = []
    for job_id, job in jobs_by_id.items():
        if not isinstance(job, dict):
            continue
        job_status = str(job.get("status") or "")
        job_donor = _job_donor_id(job)
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
        if toc_text_risk_filter is not None and _job_toc_text_risk_level(job) != toc_text_risk_filter:
            continue
        filtered.append((str(job_id), job))

    total_bucket_counts: Dict[str, int] = {}
    event_type_bucket_counts: Dict[str, Dict[str, int]] = {}
    kind_bucket_counts: Dict[str, Dict[str, int]] = {}
    section_bucket_counts: Dict[str, Dict[str, int]] = {}
    status_bucket_counts: Dict[str, Dict[str, int]] = {}
    donor_bucket_counts: Dict[str, Dict[str, int]] = {}
    donor_event_counts: Dict[str, int] = {}
    job_event_counts: Dict[str, int] = {}
    jobs_with_events = 0

    def _merge_series(target: Dict[str, Dict[str, int]], source: Any) -> None:
        if not isinstance(source, dict):
            return
        for key, rows in source.items():
            key_token = str(key or "").strip().lower() or "unknown"
            if not isinstance(rows, list):
                continue
            key_buckets = target.setdefault(key_token, {})
            for point in rows:
                if not isinstance(point, dict):
                    continue
                bucket = str(point.get("bucket") or "").strip()
                if not bucket:
                    continue
                count = _coerce_int(point.get("count"), default=0)
                key_buckets[bucket] = int(key_buckets.get(bucket) or 0) + count

    for job_id, job in filtered:
        trends_payload = public_job_review_workflow_trends_payload(
            job_id,
            job,
            event_type=event_type_filter,
            finding_id=finding_id_filter,
            finding_code=finding_code_filter,
            finding_section=finding_section_filter,
            comment_status=comment_status_filter,
            workflow_state=workflow_state_filter,
            overdue_after_hours=overdue_after_hours_value,
        )
        total_series = trends_payload.get("total_series")
        total_rows = [row for row in total_series if isinstance(row, dict)] if isinstance(total_series, list) else []
        timeline_event_count = _coerce_int(
            trends_payload.get("timeline_event_count"),
            default=sum(_coerce_int(row.get("count"), default=0) for row in total_rows),
        )
        if timeline_event_count > 0:
            jobs_with_events += 1
        job_event_counts[str(job_id)] = timeline_event_count

        donor_token = _job_donor_id(job, default="unknown")
        donor_event_counts[donor_token] = int(donor_event_counts.get(donor_token) or 0) + timeline_event_count
        donor_buckets = donor_bucket_counts.setdefault(donor_token, {})

        for point in total_rows:
            bucket = str(point.get("bucket") or "").strip()
            if not bucket:
                continue
            count = _coerce_int(point.get("count"), default=0)
            total_bucket_counts[bucket] = int(total_bucket_counts.get(bucket) or 0) + count
            donor_buckets[bucket] = int(donor_buckets.get(bucket) or 0) + count

        _merge_series(event_type_bucket_counts, trends_payload.get("event_type_series"))
        _merge_series(kind_bucket_counts, trends_payload.get("kind_series"))
        _merge_series(section_bucket_counts, trends_payload.get("section_series"))
        _merge_series(status_bucket_counts, trends_payload.get("status_series"))

    def _series_rows(counts: Dict[str, int]) -> list[Dict[str, Any]]:
        return [{"bucket": bucket, "count": int(counts.get(bucket) or 0)} for bucket in sorted(counts.keys())]

    total_series = _series_rows(total_bucket_counts)
    event_type_series = {
        key: _series_rows(event_type_bucket_counts.get(key, {})) for key in sorted(event_type_bucket_counts.keys())
    }
    kind_series = {key: _series_rows(kind_bucket_counts.get(key, {})) for key in sorted(kind_bucket_counts.keys())}
    section_series = {
        key: _series_rows(section_bucket_counts.get(key, {})) for key in sorted(section_bucket_counts.keys())
    }
    status_series = {
        key: _series_rows(status_bucket_counts.get(key, {})) for key in sorted(status_bucket_counts.keys())
    }
    donor_series = {key: _series_rows(donor_bucket_counts.get(key, {})) for key in sorted(donor_bucket_counts.keys())}

    dated_buckets = []
    for point in total_series:
        bucket = str(point.get("bucket") or "").strip()
        try:
            datetime.strptime(bucket, "%Y-%m-%d")
            dated_buckets.append(bucket)
        except ValueError:
            continue
    time_window_start = dated_buckets[0] if dated_buckets else None
    time_window_end = dated_buckets[-1] if dated_buckets else None

    top_event_type = None
    top_event_type_count = -1
    for key, rows in event_type_series.items():
        total = sum(int(row.get("count") or 0) for row in rows if isinstance(row, dict))
        if total > top_event_type_count:
            top_event_type = key
            top_event_type_count = total

    top_donor_id = None
    top_donor_event_count = -1
    for key, total in donor_event_counts.items():
        if int(total) > top_donor_event_count:
            top_donor_id = key
            top_donor_event_count = int(total)

    timeline_event_count_total = sum(int(point.get("count") or 0) for point in total_series if isinstance(point, dict))
    job_count = len(filtered)
    jobs_without_events = max(0, job_count - jobs_with_events)

    return {
        "job_count": job_count,
        "jobs_with_events": jobs_with_events,
        "jobs_without_events": jobs_without_events,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "filters": {
            "donor_id": donor_id,
            "status": status,
            "hitl_enabled": hitl_enabled,
            "warning_level": warning_level_filter,
            "grounding_risk_level": grounding_risk_filter,
            "toc_text_risk_level": toc_text_risk_filter,
            "event_type": event_type_filter,
            "finding_id": finding_id_filter,
            "finding_code": finding_code_filter,
            "finding_section": finding_section_filter,
            "comment_status": comment_status_filter,
            "workflow_state": workflow_state_filter,
            "overdue_after_hours": overdue_after_hours_value,
        },
        "bucket_granularity": "day",
        "bucket_count": len(total_series),
        "time_window_start": time_window_start,
        "time_window_end": time_window_end,
        "timeline_event_count_total": timeline_event_count_total,
        "avg_events_per_job": (round(timeline_event_count_total / job_count, 3) if job_count else None),
        "avg_events_per_active_job": (
            round(timeline_event_count_total / jobs_with_events, 3) if jobs_with_events else None
        ),
        "top_event_type": top_event_type,
        "top_event_type_count": top_event_type_count if top_event_type is not None else None,
        "top_donor_id": top_donor_id,
        "top_donor_event_count": top_donor_event_count if top_donor_id is not None else None,
        "donor_event_counts": dict(sorted(donor_event_counts.items())),
        "job_event_counts": dict(sorted(job_event_counts.items())),
        "total_series": total_series,
        "event_type_series": event_type_series,
        "kind_series": kind_series,
        "section_series": section_series,
        "status_series": status_series,
        "donor_series": donor_series,
    }


def public_portfolio_review_workflow_sla_trends_payload(
    jobs_by_id: Dict[str, Dict[str, Any]],
    *,
    donor_id: Optional[str] = None,
    status: Optional[str] = None,
    hitl_enabled: Optional[bool] = None,
    warning_level: Optional[str] = None,
    grounding_risk_level: Optional[str] = None,
    toc_text_risk_level: Optional[str] = None,
    finding_id: Optional[str] = None,
    finding_code: Optional[str] = None,
    finding_section: Optional[str] = None,
    comment_status: Optional[str] = None,
    workflow_state: Optional[str] = None,
    overdue_after_hours: int = REVIEW_WORKFLOW_OVERDUE_DEFAULT_HOURS,
) -> Dict[str, Any]:
    warning_level_filter = _normalize_warning_level_filter(warning_level)
    grounding_risk_filter = _normalize_grounding_risk_filter(grounding_risk_level)
    toc_text_risk_filter = _normalize_toc_text_risk_filter(toc_text_risk_level)
    workflow_state_filter = _normalize_review_workflow_state_filter(workflow_state)
    finding_id_filter = str(finding_id or "").strip() or None
    finding_code_filter = str(finding_code or "").strip() or None
    finding_section_filter = str(finding_section or "").strip().lower() or None
    comment_status_filter = str(comment_status or "").strip().lower() or None
    overdue_after_hours_value = (
        int(overdue_after_hours)
        if isinstance(overdue_after_hours, int) and overdue_after_hours > 0
        else REVIEW_WORKFLOW_OVERDUE_DEFAULT_HOURS
    )

    filtered: list[tuple[str, Dict[str, Any]]] = []
    for job_id, job in jobs_by_id.items():
        if not isinstance(job, dict):
            continue
        job_status = str(job.get("status") or "")
        job_donor = _job_donor_id(job)
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
        if toc_text_risk_filter is not None and _job_toc_text_risk_level(job) != toc_text_risk_filter:
            continue
        filtered.append((str(job_id), job))

    total_bucket_counts: Dict[str, int] = {}
    severity_bucket_counts: Dict[str, Dict[str, int]] = {}
    section_bucket_counts: Dict[str, Dict[str, int]] = {}
    donor_bucket_counts: Dict[str, Dict[str, int]] = {}
    donor_overdue_counts: Dict[str, int] = {}
    job_overdue_counts: Dict[str, int] = {}
    jobs_with_overdue = 0
    overdue_finding_count = 0
    overdue_comment_count = 0
    overdue_total = 0
    unresolved_total = 0

    def _merge_series(target: Dict[str, Dict[str, int]], source: Any) -> None:
        if not isinstance(source, dict):
            return
        for key, rows in source.items():
            key_token = str(key or "").strip().lower() or "unknown"
            if not isinstance(rows, list):
                continue
            key_buckets = target.setdefault(key_token, {})
            for point in rows:
                if not isinstance(point, dict):
                    continue
                bucket = str(point.get("bucket") or "").strip()
                if not bucket:
                    continue
                count = _coerce_int(point.get("count"), default=0)
                key_buckets[bucket] = int(key_buckets.get(bucket) or 0) + count

    for job_id, job in filtered:
        trends_payload = public_job_review_workflow_sla_trends_payload(
            job_id,
            job,
            finding_id=finding_id_filter,
            finding_code=finding_code_filter,
            finding_section=finding_section_filter,
            comment_status=comment_status_filter,
            workflow_state=workflow_state_filter,
            overdue_after_hours=overdue_after_hours_value,
        )
        total_series = trends_payload.get("total_series")
        total_rows = [row for row in total_series if isinstance(row, dict)] if isinstance(total_series, list) else []
        job_overdue_total = _coerce_int(
            trends_payload.get("overdue_total"),
            default=sum(_coerce_int(row.get("count"), default=0) for row in total_rows),
        )
        if job_overdue_total > 0:
            jobs_with_overdue += 1
        job_overdue_counts[str(job_id)] = job_overdue_total

        donor_token = _job_donor_id(job, default="unknown")
        donor_overdue_counts[donor_token] = int(donor_overdue_counts.get(donor_token) or 0) + job_overdue_total
        donor_buckets = donor_bucket_counts.setdefault(donor_token, {})

        for point in total_rows:
            bucket = str(point.get("bucket") or "").strip()
            if not bucket:
                continue
            count = _coerce_int(point.get("count"), default=0)
            total_bucket_counts[bucket] = int(total_bucket_counts.get(bucket) or 0) + count
            donor_buckets[bucket] = int(donor_buckets.get(bucket) or 0) + count

        _merge_series(severity_bucket_counts, trends_payload.get("severity_series"))
        _merge_series(section_bucket_counts, trends_payload.get("section_series"))
        overdue_finding_count += _coerce_int(trends_payload.get("overdue_finding_count"))
        overdue_comment_count += _coerce_int(trends_payload.get("overdue_comment_count"))
        overdue_total += job_overdue_total
        unresolved_total += _coerce_int(trends_payload.get("unresolved_total"))

    def _series_rows(counts: Dict[str, int]) -> list[Dict[str, Any]]:
        return [{"bucket": bucket, "count": int(counts.get(bucket) or 0)} for bucket in sorted(counts.keys())]

    total_series = _series_rows(total_bucket_counts)
    severity_series: Dict[str, list[Dict[str, Any]]] = {}
    for level in ("high", "medium", "low", "unknown"):
        severity_series[level] = _series_rows(severity_bucket_counts.get(level, {}))
    for level in sorted(severity_bucket_counts.keys()):
        if level in severity_series:
            continue
        severity_series[level] = _series_rows(severity_bucket_counts.get(level, {}))
    section_series: Dict[str, list[Dict[str, Any]]] = {}
    for section in sorted(section_bucket_counts.keys()):
        section_series[section] = _series_rows(section_bucket_counts.get(section, {}))
    donor_series = {key: _series_rows(donor_bucket_counts.get(key, {})) for key in sorted(donor_bucket_counts.keys())}

    dated_buckets = []
    for point in total_series:
        bucket = str(point.get("bucket") or "").strip()
        try:
            datetime.strptime(bucket, "%Y-%m-%d")
            dated_buckets.append(bucket)
        except ValueError:
            continue
    time_window_start = dated_buckets[0] if dated_buckets else None
    time_window_end = dated_buckets[-1] if dated_buckets else None

    top_severity = None
    top_severity_count = -1
    for key, rows in severity_series.items():
        total = sum(int(row.get("count") or 0) for row in rows if isinstance(row, dict))
        if total > top_severity_count:
            top_severity = key
            top_severity_count = total

    top_section = None
    top_section_count = -1
    for key, rows in section_series.items():
        total = sum(int(row.get("count") or 0) for row in rows if isinstance(row, dict))
        if total > top_section_count:
            top_section = key
            top_section_count = total

    top_donor_id = None
    top_donor_overdue_count = -1
    for key, total in donor_overdue_counts.items():
        if int(total) > top_donor_overdue_count:
            top_donor_id = key
            top_donor_overdue_count = int(total)

    job_count = len(filtered)
    jobs_without_overdue = max(0, job_count - jobs_with_overdue)
    breach_rate = (overdue_total / unresolved_total) if unresolved_total else None

    return {
        "job_count": job_count,
        "jobs_with_overdue": jobs_with_overdue,
        "jobs_without_overdue": jobs_without_overdue,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "filters": {
            "donor_id": donor_id,
            "status": status,
            "hitl_enabled": hitl_enabled,
            "warning_level": warning_level_filter,
            "grounding_risk_level": grounding_risk_filter,
            "toc_text_risk_level": toc_text_risk_filter,
            "finding_id": finding_id_filter,
            "finding_code": finding_code_filter,
            "finding_section": finding_section_filter,
            "comment_status": comment_status_filter,
            "workflow_state": workflow_state_filter,
            "overdue_after_hours": overdue_after_hours_value,
        },
        "bucket_granularity": "day",
        "bucket_count": len(total_series),
        "time_window_start": time_window_start,
        "time_window_end": time_window_end,
        "overdue_finding_count": overdue_finding_count,
        "overdue_comment_count": overdue_comment_count,
        "overdue_total": overdue_total,
        "unresolved_total": unresolved_total,
        "breach_rate": round(breach_rate, 4) if breach_rate is not None else None,
        "avg_overdue_per_job": (round(overdue_total / job_count, 3) if job_count else None),
        "avg_overdue_per_active_job": (round(overdue_total / jobs_with_overdue, 3) if jobs_with_overdue else None),
        "top_severity": top_severity,
        "top_severity_count": top_severity_count if top_severity is not None else None,
        "top_section": top_section,
        "top_section_count": top_section_count if top_section is not None else None,
        "top_donor_id": top_donor_id,
        "top_donor_overdue_count": top_donor_overdue_count if top_donor_id is not None else None,
        "donor_overdue_counts": dict(sorted(donor_overdue_counts.items())),
        "job_overdue_counts": dict(sorted(job_overdue_counts.items())),
        "total_series": total_series,
        "severity_series": severity_series,
        "section_series": section_series,
        "donor_series": donor_series,
    }


def public_portfolio_quality_csv_text(payload: Dict[str, Any]) -> str:
    return csv_text_from_mapping(payload)


def public_portfolio_metrics_csv_text(payload: Dict[str, Any]) -> str:
    return csv_text_from_mapping(payload)


def public_portfolio_review_workflow_csv_text(payload: Dict[str, Any]) -> str:
    return csv_text_from_mapping(payload)


def public_portfolio_review_workflow_sla_csv_text(payload: Dict[str, Any]) -> str:
    return csv_text_from_mapping(payload)


def public_portfolio_review_workflow_sla_hotspots_csv_text(payload: Dict[str, Any]) -> str:
    return csv_text_from_mapping(payload)


def public_portfolio_review_workflow_sla_hotspots_trends_csv_text(payload: Dict[str, Any]) -> str:
    return csv_text_from_mapping(payload)


def public_portfolio_review_workflow_trends_csv_text(payload: Dict[str, Any]) -> str:
    return csv_text_from_mapping(payload)


def public_portfolio_review_workflow_sla_trends_csv_text(payload: Dict[str, Any]) -> str:
    return csv_text_from_mapping(payload)


def public_ingest_inventory_csv_text(payload: Dict[str, Any]) -> str:
    return csv_text_from_mapping(payload)


def public_job_review_workflow_csv_text(payload: Dict[str, Any]) -> str:
    return csv_text_from_mapping(payload)


def public_job_review_workflow_trends_csv_text(payload: Dict[str, Any]) -> str:
    return csv_text_from_mapping(payload)


def public_job_review_workflow_sla_csv_text(payload: Dict[str, Any]) -> str:
    return csv_text_from_mapping(payload)


def public_job_review_workflow_sla_trends_csv_text(payload: Dict[str, Any]) -> str:
    return csv_text_from_mapping(payload)


def public_job_review_workflow_sla_hotspots_csv_text(payload: Dict[str, Any]) -> str:
    return csv_text_from_mapping(payload)


def public_job_review_workflow_sla_hotspots_trends_csv_text(payload: Dict[str, Any]) -> str:
    return csv_text_from_mapping(payload)


def public_checkpoint_payload(checkpoint: Dict[str, Any]) -> Dict[str, Any]:
    public_checkpoint: Dict[str, Any] = {}
    for key, value in checkpoint.items():
        if key == "state_snapshot":
            continue
        public_checkpoint[str(key)] = sanitize_for_public_response(value)
    public_checkpoint["has_state_snapshot"] = "state_snapshot" in checkpoint
    return public_checkpoint
