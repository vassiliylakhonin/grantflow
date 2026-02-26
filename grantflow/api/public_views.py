from __future__ import annotations

import difflib
import json
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional, cast

from grantflow.api.csv_utils import csv_text_from_mapping

PORTFOLIO_QUALITY_SIGNAL_WEIGHTS: dict[str, int] = {
    "high_severity_findings_total": 5,
    "medium_severity_findings_total": 3,
    "open_findings_total": 4,
    "needs_revision_job_count": 4,
    "rag_low_confidence_citation_count": 3,
    "low_confidence_citation_count": 1,
}
PORTFOLIO_QUALITY_HIGH_PRIORITY_SIGNALS = {
    "high_severity_findings_total",
    "open_findings_total",
    "needs_revision_job_count",
    "rag_low_confidence_citation_count",
}


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


def public_job_critic_payload(job_id: str, job: Dict[str, Any]) -> Dict[str, Any]:
    state = job.get("state")
    critic_notes = (state or {}).get("critic_notes") if isinstance(state, dict) else {}
    if not isinstance(critic_notes, dict):
        critic_notes = {}

    raw_flaws = critic_notes.get("fatal_flaws")
    fatal_flaws = (
        [sanitize_for_public_response(item) for item in raw_flaws if isinstance(item, dict)]
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
            finding_id = str(flaw.get("finding_id") or "").strip()
            if not finding_id:
                continue
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

    return {
        "preset_key": sanitize_for_public_response(client_metadata.get("demo_generate_preset_key")),
        "donor_id": donor_id,
        "expected_doc_families": expected_doc_families,
        "present_doc_families": present_doc_families,
        "missing_doc_families": missing_doc_families,
        "expected_count": expected_count,
        "loaded_count": loaded_count,
        "coverage_rate": coverage_rate,
        "inventory_total_uploads": sanitize_for_public_response(inventory_payload.get("total_uploads")),
        "inventory_family_count": sanitize_for_public_response(inventory_payload.get("family_count")),
        "doc_family_counts": sanitize_for_public_response(doc_family_counts),
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

    confidence_values: list[float] = []
    high_conf = 0
    low_conf = 0
    rag_low_conf = 0
    fallback_ns = 0
    architect_threshold_considered = 0
    architect_threshold_hits = 0
    for c in citations:
        if not isinstance(c, dict):
            continue
        if str(c.get("citation_type") or "") == "rag_low_confidence":
            rag_low_conf += 1
        if str(c.get("citation_type") or "") == "fallback_namespace":
            fallback_ns += 1
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

    return {
        "job_id": str(job_id),
        "status": str(job.get("status") or ""),
        "quality_score": sanitize_for_public_response(state_dict.get("quality_score")),
        "critic_score": sanitize_for_public_response(state_dict.get("critic_score")),
        "needs_revision": sanitize_for_public_response(state_dict.get("needs_revision")),
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
        "readiness": readiness_payload,
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


def public_portfolio_quality_payload(
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
    donor_needs_revision_counts: Dict[str, int] = {}
    donor_open_findings_counts: Dict[str, int] = {}
    donor_weighted_risk_breakdown: Dict[str, Dict[str, int]] = {}
    quality_rows: list[Dict[str, Any]] = []

    for job_id, job in filtered:
        job_status = str(job.get("status") or "")
        status_counts[job_status] = status_counts.get(job_status, 0) + 1
        state = job.get("state") if isinstance(job.get("state"), dict) else {}
        job_donor = str((state or {}).get("donor_id") or (state or {}).get("donor") or "unknown")
        donor_counts[job_donor] = donor_counts.get(job_donor, 0) + 1

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
        citation_count_total += int(row_citations.get("citation_count") or 0)
        low_confidence_citation_count += int(row_citations.get("low_confidence_citation_count") or 0)
        rag_low_confidence_citation_count += int(row_citations.get("rag_low_confidence_citation_count") or 0)
        architect_rag_low_confidence_citation_count += int(
            row_citations.get("architect_rag_low_confidence_citation_count") or 0
        )
        mel_rag_low_confidence_citation_count += int(row_citations.get("mel_rag_low_confidence_citation_count") or 0)
        fallback_namespace_citation_count += int(row_citations.get("fallback_namespace_citation_count") or 0)

        donor_for_row = str(row.get("_donor_id") or "unknown")
        donor_row = donor_weighted_risk_breakdown.setdefault(
            donor_for_row,
            {
                "weighted_score": 0,
                "high_priority_signal_count": 0,
                "open_findings_total": 0,
                "high_severity_findings_total": 0,
                "needs_revision_job_count": 0,
                "low_confidence_citation_count": 0,
                "rag_low_confidence_citation_count": 0,
                "architect_rag_low_confidence_citation_count": 0,
                "mel_rag_low_confidence_citation_count": 0,
                "fallback_namespace_citation_count": 0,
            },
        )
        donor_row["open_findings_total"] += int(row_critic.get("open_finding_count") or 0)
        donor_row["high_severity_findings_total"] += int(row_critic.get("high_severity_fatal_flaw_count") or 0)
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
        if bool(row.get("needs_revision")):
            donor_row["needs_revision_job_count"] += 1

    signal_counts = {
        "high_severity_findings_total": critic_high_severity_total,
        "medium_severity_findings_total": critic_medium_severity_total,
        "open_findings_total": critic_open_findings_total,
        "needs_revision_job_count": needs_revision_job_count,
        "rag_low_confidence_citation_count": rag_low_confidence_citation_count,
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

    for donor_row in donor_weighted_risk_breakdown.values():
        donor_row["weighted_score"] = (
            donor_row["high_severity_findings_total"] * PORTFOLIO_QUALITY_SIGNAL_WEIGHTS["high_severity_findings_total"]
            + donor_row["open_findings_total"] * PORTFOLIO_QUALITY_SIGNAL_WEIGHTS["open_findings_total"]
            + donor_row["needs_revision_job_count"] * PORTFOLIO_QUALITY_SIGNAL_WEIGHTS["needs_revision_job_count"]
            + donor_row["rag_low_confidence_citation_count"]
            * PORTFOLIO_QUALITY_SIGNAL_WEIGHTS["rag_low_confidence_citation_count"]
            + donor_row["low_confidence_citation_count"]
            * PORTFOLIO_QUALITY_SIGNAL_WEIGHTS["low_confidence_citation_count"]
        )
        donor_row["high_priority_signal_count"] = (
            donor_row["high_severity_findings_total"]
            + donor_row["open_findings_total"]
            + donor_row["needs_revision_job_count"]
            + donor_row["rag_low_confidence_citation_count"]
        )

    job_count = len(filtered)
    quality_score_job_count = sum(1 for row in quality_rows if isinstance(row.get("quality_score"), (int, float)))
    critic_score_job_count = sum(1 for row in quality_rows if isinstance(row.get("critic_score"), (int, float)))

    citation_summary_rows: list[Dict[str, Any]] = [
        cast(Dict[str, Any], row.get("citations")) for row in quality_rows if isinstance(row.get("citations"), dict)
    ]

    return {
        "job_count": job_count,
        "filters": {
            "donor_id": donor_id,
            "status": status,
            "hitl_enabled": hitl_enabled,
        },
        "status_counts": status_counts,
        "donor_counts": donor_counts,
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
            "fallback_namespace_citation_rate": (
                round(fallback_namespace_citation_count / citation_count_total, 4) if citation_count_total else None
            ),
            "architect_threshold_hit_rate_avg": _avg(citation_summary_rows, "architect_threshold_hit_rate"),
        },
        "priority_signal_breakdown": priority_signal_breakdown,
        "donor_weighted_risk_breakdown": donor_weighted_risk_breakdown,
        "donor_needs_revision_counts": donor_needs_revision_counts,
        "donor_open_findings_counts": donor_open_findings_counts,
    }


def public_portfolio_quality_csv_text(payload: Dict[str, Any]) -> str:
    return csv_text_from_mapping(payload)


def public_portfolio_metrics_csv_text(payload: Dict[str, Any]) -> str:
    return csv_text_from_mapping(payload)


def public_ingest_inventory_csv_text(payload: Dict[str, Any]) -> str:
    return csv_text_from_mapping(payload)


def public_checkpoint_payload(checkpoint: Dict[str, Any]) -> Dict[str, Any]:
    public_checkpoint: Dict[str, Any] = {}
    for key, value in checkpoint.items():
        if key == "state_snapshot":
            continue
        public_checkpoint[str(key)] = sanitize_for_public_response(value)
    public_checkpoint["has_state_snapshot"] = "state_snapshot" in checkpoint
    return public_checkpoint
