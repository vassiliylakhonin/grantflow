#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from grantflow.api.public_views import (
    _comment_triage_summary_payload,
    _critic_triage_summary_payload,
    _review_action_queue_summary_payload,
    _review_workflow_queue_delta_summary_payload,
    _review_workflow_policy_summary_payload,
    _review_workflow_throughput_summary_payload,
    _reviewer_workflow_summary_payload,
)

STALE_BUCKET_KEYS = ("logic", "grounding", "measurement", "compliance", "general")
BASELINE_FIELD_DEFAULTS = {
    "baseline_type": "",
    "baseline_method": "",
    "baseline_source": "",
    "baseline_confidence": "",
    "baseline_time_to_first_draft_seconds": "",
    "baseline_time_to_terminal_seconds": "",
    "baseline_review_loops": "",
    "baseline_owner": "",
    "baseline_capture_date": "",
    "baseline_notes": "",
}

MEASURED_BASELINE_FIELD_KEYS = (
    "baseline_type",
    "baseline_method",
    "baseline_source",
    "baseline_confidence",
    "baseline_time_to_first_draft_seconds",
    "baseline_time_to_terminal_seconds",
    "baseline_review_loops",
    "baseline_owner",
    "baseline_capture_date",
    "baseline_notes",
)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _safe_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_int(value: Any) -> int | None:
    try:
        if value is None or value == "":
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _avg(values: list[float | int | None]) -> float | None:
    clean = [float(value) for value in values if value is not None]
    if not clean:
        return None
    return sum(clean) / len(clean)


def _fmt(value: float | int | None) -> str:
    if value is None:
        return "-"
    if isinstance(value, int):
        return str(value)
    if float(value).is_integer():
        return str(int(value))
    return f"{value:.3f}"


def _rate_delta(current: float | None, baseline: float | None) -> float | None:
    if current is None or baseline is None or baseline <= 0:
        return None
    return (baseline - current) / baseline


def _merge_measured_baseline(
    rows: list[dict[str, Any]],
    *,
    measured_rows: list[dict[str, str]] | None,
) -> list[dict[str, Any]]:
    if not measured_rows:
        return rows
    by_case: dict[str, dict[str, str]] = {}
    by_preset: dict[str, dict[str, str]] = {}
    for row in measured_rows:
        case_dir = str(row.get("case_dir") or "").strip()
        preset_key = str(row.get("preset_key") or "").strip()
        if case_dir:
            by_case[case_dir] = row
        if preset_key:
            by_preset[preset_key] = row
    out: list[dict[str, Any]] = []
    for row in rows:
        enriched = dict(row)
        baseline_row = by_case.get(str(row.get("case_dir") or "").strip()) or by_preset.get(
            str(row.get("preset_key") or "").strip()
        )
        if baseline_row:
            for key, default in BASELINE_FIELD_DEFAULTS.items():
                value = str(baseline_row.get(key) or "").strip()
                enriched[key] = value if value else default
        else:
            for key, default in BASELINE_FIELD_DEFAULTS.items():
                enriched.setdefault(key, default)
        baseline_type = str(enriched.get("baseline_type") or "").strip().lower()
        current_first = _safe_float(enriched.get("time_to_first_draft_seconds"))
        current_terminal = _safe_float(enriched.get("time_to_terminal_seconds"))
        current_loops = _safe_float(enriched.get("status_change_count"))
        baseline_first = _safe_float(enriched.get("baseline_time_to_first_draft_seconds"))
        baseline_terminal = _safe_float(enriched.get("baseline_time_to_terminal_seconds"))
        baseline_loops = _safe_float(enriched.get("baseline_review_loops"))
        enriched["baseline_present"] = 1 if baseline_type in {"measured", "illustrative"} else 0
        enriched["measured_baseline_present"] = 1 if baseline_type == "measured" else 0
        enriched["delta_time_to_first_draft_seconds"] = (
            (baseline_first - current_first) if baseline_first is not None and current_first is not None else ""
        )
        enriched["delta_time_to_terminal_seconds"] = (
            (baseline_terminal - current_terminal)
            if baseline_terminal is not None and current_terminal is not None
            else ""
        )
        enriched["delta_review_loops"] = (
            (baseline_loops - current_loops) if baseline_loops is not None and current_loops is not None else ""
        )
        enriched["time_to_first_draft_improvement_rate"] = _rate_delta(current_first, baseline_first) or ""
        enriched["time_to_terminal_improvement_rate"] = _rate_delta(current_terminal, baseline_terminal) or ""
        enriched["review_loops_improvement_rate"] = _rate_delta(current_loops, baseline_loops) or ""
        out.append(enriched)
    return out


def _merge_benchmark_baseline(
    rows: list[dict[str, Any]],
    *,
    benchmark_rows: list[dict[str, str]] | None,
) -> list[dict[str, Any]]:
    if not benchmark_rows:
        for row in rows:
            for key, default in BASELINE_FIELD_DEFAULTS.items():
                row.setdefault(key, default)
        return rows
    by_case = {
        str(row.get("case_dir") or "").strip(): row for row in benchmark_rows if str(row.get("case_dir") or "").strip()
    }
    by_preset = {
        str(row.get("preset_key") or "").strip(): row
        for row in benchmark_rows
        if str(row.get("preset_key") or "").strip()
    }
    out: list[dict[str, Any]] = []
    for row in rows:
        enriched = dict(row)
        if str(enriched.get("baseline_type") or "").strip():
            out.append(enriched)
            continue
        benchmark_row = by_case.get(str(row.get("case_dir") or "").strip()) or by_preset.get(
            str(row.get("preset_key") or "").strip()
        )
        if benchmark_row:
            for key in MEASURED_BASELINE_FIELD_KEYS:
                value = str(benchmark_row.get(key) or "").strip()
                if value:
                    enriched[key] = value
        else:
            for key, default in BASELINE_FIELD_DEFAULTS.items():
                enriched.setdefault(key, default)
        out.append(enriched)
    return out


def _bucket_map(summary: dict[str, Any] | None) -> dict[str, int]:
    raw = summary.get("stale_comment_bucket_counts") if isinstance(summary, dict) else {}
    if not isinstance(raw, dict):
        return {}
    return {token: int(raw.get(token) or 0) for token in STALE_BUCKET_KEYS if int(raw.get(token) or 0) > 0}


def _bucket_mix_text(bucket_counts: dict[str, float | int]) -> str:
    parts = [f"{bucket}={int(count)}" for bucket, count in bucket_counts.items() if int(count) > 0]
    return ", ".join(parts) if parts else "-"


def _donor_bucket_mix_text(rows: list[dict[str, Any]]) -> str:
    donor_stale_bucket_totals: dict[str, dict[str, int]] = {}
    for row in rows:
        donor = str(row.get("donor_id") or "").strip() or "unknown"
        donor_bucket_counts = donor_stale_bucket_totals.setdefault(
            donor, {"logic": 0, "grounding": 0, "measurement": 0, "compliance": 0, "general": 0}
        )
        donor_bucket_counts["logic"] += int(_safe_int(row.get("stale_comment_bucket_logic")) or 0)
        donor_bucket_counts["grounding"] += int(_safe_int(row.get("stale_comment_bucket_grounding")) or 0)
        donor_bucket_counts["measurement"] += int(_safe_int(row.get("stale_comment_bucket_measurement")) or 0)
        donor_bucket_counts["compliance"] += int(_safe_int(row.get("stale_comment_bucket_compliance")) or 0)
        donor_bucket_counts["general"] += int(_safe_int(row.get("stale_comment_bucket_general")) or 0)
    donor_mix = "; ".join(
        f"{donor}: {_bucket_mix_text(bucket_counts)}"
        for donor, bucket_counts in donor_stale_bucket_totals.items()
        if _bucket_mix_text(bucket_counts) != "-"
    )
    return donor_mix or "-"


def _build_case_row(case_dir: Path, benchmark_row: dict[str, Any]) -> dict[str, Any]:
    metrics_path = case_dir / "metrics.json"
    quality_path = case_dir / "quality.json"
    critic_path = case_dir / "critic.json"
    export_payload_path = case_dir / "export-payload.json"
    status_path = case_dir / "status.json"
    metrics = _read_json(metrics_path) if metrics_path.exists() else {}
    quality = _read_json(quality_path) if quality_path.exists() else {}
    critic = _read_json(critic_path) if critic_path.exists() else {}
    export_payload = _read_json(export_payload_path) if export_payload_path.exists() else {}
    status_payload = _read_json(status_path) if status_path.exists() else {}
    readiness = (
        quality.get("review_readiness_summary") if isinstance(quality.get("review_readiness_summary"), dict) else {}
    )
    export_review_comments = []
    if isinstance(export_payload, dict):
        payload_root = export_payload.get("payload")
        if isinstance(payload_root, dict) and isinstance(payload_root.get("review_comments"), list):
            export_review_comments = [row for row in payload_root.get("review_comments") or [] if isinstance(row, dict)]
    comment_triage = (
        readiness.get("comment_triage_summary") if isinstance(readiness.get("comment_triage_summary"), dict) else {}
    )
    if not comment_triage and isinstance(critic, dict) and export_review_comments:
        raw_findings = critic.get("fatal_flaws")
        findings = [row for row in raw_findings if isinstance(row, dict)] if isinstance(raw_findings, list) else []
        comment_triage = _comment_triage_summary_payload(
            review_comments=export_review_comments,
            critic_findings=findings,
            donor_id=str(benchmark_row.get("donor_id") or "").strip(),
        )
        readiness = {
            **readiness,
            "open_review_comments": comment_triage.get("open_comment_count"),
            "resolved_review_comments": comment_triage.get("resolved_comment_count"),
            "acknowledged_review_comments": comment_triage.get("acknowledged_comment_count"),
            "pending_review_comments": comment_triage.get("pending_comment_count"),
            "overdue_review_comments": comment_triage.get("overdue_comment_count"),
            "stale_open_review_comments": comment_triage.get("stale_open_comment_count"),
            "linked_review_comments": comment_triage.get("linked_comment_count"),
            "orphan_linked_review_comments": comment_triage.get("orphan_linked_comment_count"),
            "comment_triage_summary": comment_triage,
        }
    action_queue_summary = (
        readiness.get("action_queue_summary") if isinstance(readiness.get("action_queue_summary"), dict) else {}
    )
    throughput_summary = (
        readiness.get("throughput_summary") if isinstance(readiness.get("throughput_summary"), dict) else {}
    )
    queue_delta_summary = (
        readiness.get("queue_delta_summary") if isinstance(readiness.get("queue_delta_summary"), dict) else {}
    )
    reviewer_workflow_summary = (
        readiness.get("reviewer_workflow_summary")
        if isinstance(readiness.get("reviewer_workflow_summary"), dict)
        else {}
    )
    status_payload_events = (
        status_payload.get("job_events") if isinstance(status_payload.get("job_events"), list) else []
    )
    timeline = []
    for item in status_payload_events:
        if not isinstance(item, dict):
            continue
        event_type = str(item.get("type") or "").strip()
        if event_type not in {
            "critic_finding_status_changed",
            "review_comment_added",
            "review_comment_status_changed",
        }:
            continue
        timeline.append(
            {
                "ts": item.get("ts"),
                "type": event_type,
                "status": item.get("status"),
            }
        )
    if not action_queue_summary and isinstance(critic, dict):
        raw_findings = critic.get("fatal_flaws")
        findings = [row for row in raw_findings if isinstance(row, dict)] if isinstance(raw_findings, list) else []
        action_queue_summary = _review_action_queue_summary_payload(
            critic_findings=findings,
            comment_triage_summary=comment_triage,
        )
        throughput_summary = _review_workflow_throughput_summary_payload(timeline=timeline)
        queue_delta_summary = _review_workflow_queue_delta_summary_payload(
            action_queue_summary=action_queue_summary,
            throughput_summary=throughput_summary,
        )
        reviewer_workflow_summary = _reviewer_workflow_summary_payload(
            critic_findings=findings,
            comment_triage_summary=comment_triage,
        )
        readiness = {
            **readiness,
            "reviewer_workflow_summary": reviewer_workflow_summary,
            "action_queue_summary": action_queue_summary,
            "throughput_summary": throughput_summary,
            "queue_delta_summary": queue_delta_summary,
        }
    if not throughput_summary:
        throughput_summary = _review_workflow_throughput_summary_payload(timeline=timeline)
        readiness = {**readiness, "throughput_summary": throughput_summary}
    if not queue_delta_summary and action_queue_summary:
        queue_delta_summary = _review_workflow_queue_delta_summary_payload(
            action_queue_summary=action_queue_summary,
            throughput_summary=throughput_summary,
        )
        readiness = {**readiness, "queue_delta_summary": queue_delta_summary}
    if not isinstance(readiness.get("review_workflow_policy_summary"), dict):
        readiness = {
            **readiness,
            "review_workflow_policy_summary": _review_workflow_policy_summary_payload(
                reviewer_workflow_summary=reviewer_workflow_summary,
                action_queue_summary=action_queue_summary,
                comment_triage_summary=comment_triage,
            ),
        }
    if (
        readiness.get("critic_finding_resolution_rate") in {None, ""}
        or readiness.get("critic_finding_acknowledgment_rate") in {None, ""}
    ) and isinstance(critic, dict):
        raw_findings = critic.get("fatal_flaws")
        findings = [row for row in raw_findings if isinstance(row, dict)] if isinstance(raw_findings, list) else []
        total_findings = len(findings)
        resolved_finding_count = sum(
            1 for item in findings if str(item.get("status") or "").strip().lower() in {"resolved", "closed"}
        )
        acknowledged_finding_count = sum(
            1 for item in findings if str(item.get("status") or "").strip().lower() == "acknowledged"
        )
        readiness = {
            **readiness,
            "critic_finding_resolution_rate": (
                round(resolved_finding_count / total_findings, 4) if total_findings else None
            ),
            "critic_finding_acknowledgment_rate": (
                round((resolved_finding_count + acknowledged_finding_count) / total_findings, 4)
                if total_findings
                else None
            ),
        }
    comment_defaults = {
        "open_review_comments": 0,
        "resolved_review_comments": 0,
        "acknowledged_review_comments": 0,
        "pending_review_comments": 0,
        "overdue_review_comments": 0,
        "stale_open_review_comments": 0,
        "linked_review_comments": 0,
        "orphan_linked_review_comments": 0,
        "review_comment_resolution_rate": None,
        "review_comment_acknowledgment_rate": None,
    }
    readiness = {**comment_defaults, **readiness}
    triage = quality.get("triage_summary") if isinstance(quality.get("triage_summary"), dict) else {}
    if not triage and isinstance(critic, dict):
        triage = critic.get("triage_summary") if isinstance(critic.get("triage_summary"), dict) else {}
    if not triage and isinstance(critic, dict):
        raw_findings = critic.get("fatal_flaws")
        findings = [row for row in raw_findings if isinstance(row, dict)] if isinstance(raw_findings, list) else []
        triage = (
            _critic_triage_summary_payload(findings, donor_id=str(benchmark_row.get("donor_id") or "").strip())
            if findings
            else {}
        )
    mel = quality.get("mel") if isinstance(quality.get("mel"), dict) else {}
    citations = quality.get("citations") if isinstance(quality.get("citations"), dict) else {}
    architect_signal_summary = (
        citations.get("architect_signal_summary") if isinstance(citations.get("architect_signal_summary"), dict) else {}
    )
    architect_retrieval = (
        status_payload.get("state", {}).get("architect_retrieval")
        if isinstance(status_payload.get("state"), dict)
        else {}
    )
    mov_rate = _safe_float(mel.get("means_of_verification_coverage_rate"))
    owner_rate = _safe_float(mel.get("owner_coverage_rate"))
    smart_rate = _safe_float(mel.get("smart_field_coverage_rate"))
    stale_bucket_counts = _bucket_map(comment_triage if isinstance(comment_triage, dict) else {})
    architect_evidence_counts = (
        architect_signal_summary.get("evidence_signal_counts")
        if isinstance(architect_signal_summary.get("evidence_signal_counts"), dict)
        else {}
    )
    architect_primary_signal = next(
        (
            str(key).strip()
            for key, value in sorted(
                architect_evidence_counts.items(),
                key=lambda item: int(item[1] or 0),
                reverse=True,
            )
            if str(key).strip() and int(value or 0) > 0
        ),
        "",
    )
    mel_citation_type_counts = (
        citations.get("mel_citation_type_counts") if isinstance(citations.get("mel_citation_type_counts"), dict) else {}
    )
    mel_primary_signal = (
        "retrieved donor evidence"
        if int(_safe_int(citations.get("mel_retrieval_grounded_citation_count")) or 0) > 0
        else (
            "strategy reference" if int(_safe_int(mel_citation_type_counts.get("strategy_reference")) or 0) > 0 else ""
        )
    )

    return {
        "case_dir": case_dir.name,
        "preset_key": benchmark_row.get("preset_key"),
        "donor_id": benchmark_row.get("donor_id"),
        "job_id": benchmark_row.get("job_id"),
        "status": benchmark_row.get("status"),
        "hitl_enabled": benchmark_row.get("hitl_enabled"),
        "quality_score": quality.get("quality_score", benchmark_row.get("quality_score")),
        "critic_score": quality.get("critic_score", benchmark_row.get("critic_score")),
        "citation_count": metrics.get("citation_count", benchmark_row.get("citation_count")),
        "time_to_first_draft_seconds": metrics.get("time_to_first_draft_seconds"),
        "time_to_terminal_seconds": metrics.get("time_to_terminal_seconds"),
        "time_in_pending_hitl_seconds": metrics.get("time_in_pending_hitl_seconds"),
        "status_change_count": metrics.get("status_change_count"),
        "pause_count": metrics.get("pause_count"),
        "resume_count": metrics.get("resume_count"),
        "grounding_risk_level": metrics.get("grounding_risk_level"),
        "retrieval_expected": metrics.get("retrieval_expected"),
        "architect_retrieval_hits_count": (
            architect_retrieval.get("hits_count") if isinstance(architect_retrieval, dict) else None
        ),
        "architect_retrieval_used_results": (
            architect_retrieval.get("used_results") if isinstance(architect_retrieval, dict) else None
        ),
        "architect_retrieval_grounded_citation_count": citations.get("architect_retrieval_grounded_citation_count"),
        "architect_retrieval_grounded_citation_rate": citations.get("architect_retrieval_grounded_citation_rate"),
        "architect_fallback_namespace_citation_count": citations.get("architect_fallback_namespace_citation_count"),
        "architect_primary_evidence_signal": architect_primary_signal or None,
        "architect_evidence_signal_mix": _bucket_mix_text(
            {str(key): int(value or 0) for key, value in architect_evidence_counts.items()}
        ),
        "mel_retrieval_hits_count": mel.get("retrieval_hits_count"),
        "mel_retrieval_used": mel.get("retrieval_used"),
        "mel_retrieval_grounded_citation_count": citations.get("mel_retrieval_grounded_citation_count"),
        "mel_retrieval_grounded_citation_rate": citations.get("mel_retrieval_grounded_citation_rate"),
        "mel_fallback_namespace_citation_count": citations.get("mel_fallback_namespace_citation_count"),
        "mel_primary_evidence_signal": mel_primary_signal or None,
        "open_critic_findings": readiness.get("open_critic_findings"),
        "high_severity_open_findings": readiness.get("high_severity_open_findings"),
        "resolved_critic_findings": readiness.get("resolved_critic_findings"),
        "acknowledged_critic_findings": readiness.get("acknowledged_critic_findings"),
        "critic_finding_resolution_rate": readiness.get("critic_finding_resolution_rate"),
        "critic_finding_acknowledgment_rate": readiness.get("critic_finding_acknowledgment_rate"),
        "open_review_comments": readiness.get("open_review_comments"),
        "resolved_review_comments": readiness.get("resolved_review_comments"),
        "acknowledged_review_comments": readiness.get("acknowledged_review_comments"),
        "pending_review_comments": readiness.get("pending_review_comments"),
        "overdue_review_comments": readiness.get("overdue_review_comments"),
        "stale_open_review_comments": readiness.get("stale_open_review_comments"),
        "linked_review_comments": readiness.get("linked_review_comments"),
        "orphan_linked_review_comments": readiness.get("orphan_linked_review_comments"),
        "review_comment_resolution_rate": readiness.get("review_comment_resolution_rate"),
        "review_comment_acknowledgment_rate": readiness.get("review_comment_acknowledgment_rate"),
        "reviewer_workflow_resolution_rate": (
            readiness.get("reviewer_workflow_summary", {}).get("resolution_rate")
            if isinstance(readiness.get("reviewer_workflow_summary"), dict)
            else None
        ),
        "reviewer_workflow_acknowledgment_rate": (
            readiness.get("reviewer_workflow_summary", {}).get("acknowledgment_rate")
            if isinstance(readiness.get("reviewer_workflow_summary"), dict)
            else None
        ),
        "finding_ack_queue_count": (
            readiness.get("action_queue_summary", {}).get("finding_ack_queue_count")
            if isinstance(readiness.get("action_queue_summary"), dict)
            else None
        ),
        "finding_resolve_queue_count": (
            readiness.get("action_queue_summary", {}).get("finding_resolve_queue_count")
            if isinstance(readiness.get("action_queue_summary"), dict)
            else None
        ),
        "comment_ack_queue_count": (
            readiness.get("action_queue_summary", {}).get("comment_ack_queue_count")
            if isinstance(readiness.get("action_queue_summary"), dict)
            else None
        ),
        "comment_resolve_queue_count": (
            readiness.get("action_queue_summary", {}).get("comment_resolve_queue_count")
            if isinstance(readiness.get("action_queue_summary"), dict)
            else None
        ),
        "comment_reopen_queue_count": (
            readiness.get("action_queue_summary", {}).get("comment_reopen_queue_count")
            if isinstance(readiness.get("action_queue_summary"), dict)
            else None
        ),
        "finding_ack_completed_count": (
            readiness.get("throughput_summary", {}).get("finding_ack_completed_count")
            if isinstance(readiness.get("throughput_summary"), dict)
            else None
        ),
        "finding_resolve_completed_count": (
            readiness.get("throughput_summary", {}).get("finding_resolve_completed_count")
            if isinstance(readiness.get("throughput_summary"), dict)
            else None
        ),
        "comment_ack_completed_count": (
            readiness.get("throughput_summary", {}).get("comment_ack_completed_count")
            if isinstance(readiness.get("throughput_summary"), dict)
            else None
        ),
        "comment_resolve_completed_count": (
            readiness.get("throughput_summary", {}).get("comment_resolve_completed_count")
            if isinstance(readiness.get("throughput_summary"), dict)
            else None
        ),
        "comment_reopen_completed_count": (
            readiness.get("throughput_summary", {}).get("comment_reopen_completed_count")
            if isinstance(readiness.get("throughput_summary"), dict)
            else None
        ),
        "dominant_completed_action": (
            readiness.get("throughput_summary", {}).get("dominant_completed_action")
            if isinstance(readiness.get("throughput_summary"), dict)
            else None
        ),
        "finding_ack_net_delta": (
            readiness.get("queue_delta_summary", {}).get("finding_ack_net_delta")
            if isinstance(readiness.get("queue_delta_summary"), dict)
            else None
        ),
        "finding_resolve_net_delta": (
            readiness.get("queue_delta_summary", {}).get("finding_resolve_net_delta")
            if isinstance(readiness.get("queue_delta_summary"), dict)
            else None
        ),
        "comment_ack_net_delta": (
            readiness.get("queue_delta_summary", {}).get("comment_ack_net_delta")
            if isinstance(readiness.get("queue_delta_summary"), dict)
            else None
        ),
        "comment_resolve_net_delta": (
            readiness.get("queue_delta_summary", {}).get("comment_resolve_net_delta")
            if isinstance(readiness.get("queue_delta_summary"), dict)
            else None
        ),
        "comment_reopen_net_delta": (
            readiness.get("queue_delta_summary", {}).get("comment_reopen_net_delta")
            if isinstance(readiness.get("queue_delta_summary"), dict)
            else None
        ),
        "next_primary_action": (
            readiness.get("action_queue_summary", {}).get("next_primary_action")
            if isinstance(readiness.get("action_queue_summary"), dict)
            else None
        ),
        "review_workflow_policy_status": (
            readiness.get("review_workflow_policy_summary", {}).get("status")
            if isinstance(readiness.get("review_workflow_policy_summary"), dict)
            else None
        ),
        "review_workflow_policy_go_no_go_flag": (
            readiness.get("review_workflow_policy_summary", {}).get("go_no_go_flag")
            if isinstance(readiness.get("review_workflow_policy_summary"), dict)
            else None
        ),
        "review_workflow_policy_breach_count": (
            readiness.get("review_workflow_policy_summary", {}).get("breach_count")
            if isinstance(readiness.get("review_workflow_policy_summary"), dict)
            else None
        ),
        "review_workflow_policy_attention_count": (
            readiness.get("review_workflow_policy_summary", {}).get("attention_count")
            if isinstance(readiness.get("review_workflow_policy_summary"), dict)
            else None
        ),
        "review_workflow_next_operational_action": (
            readiness.get("review_workflow_policy_summary", {}).get("next_operational_action")
            if isinstance(readiness.get("review_workflow_policy_summary"), dict)
            else None
        ),
        "fallback_strategy_citations": readiness.get("fallback_strategy_citations"),
        "low_confidence_citations": readiness.get("low_confidence_citations"),
        "next_review_bucket": triage.get("next_review_bucket"),
        "next_recommended_action": triage.get("next_recommended_action"),
        "next_comment_section": (
            comment_triage.get("next_comment_section") if isinstance(comment_triage, dict) else None
        ),
        "next_comment_bucket": (
            comment_triage.get("next_comment_bucket") if isinstance(comment_triage, dict) else None
        ),
        "next_comment_action": (
            comment_triage.get("next_recommended_action") if isinstance(comment_triage, dict) else None
        ),
        "comment_age_lt_24h": (
            comment_triage.get("aging_band_counts", {}).get("lt_24h") if isinstance(comment_triage, dict) else None
        ),
        "comment_age_d1_3": (
            comment_triage.get("aging_band_counts", {}).get("d1_3") if isinstance(comment_triage, dict) else None
        ),
        "comment_age_d3_7": (
            comment_triage.get("aging_band_counts", {}).get("d3_7") if isinstance(comment_triage, dict) else None
        ),
        "comment_age_gt_7d": (
            comment_triage.get("aging_band_counts", {}).get("gt_7d") if isinstance(comment_triage, dict) else None
        ),
        "stale_comment_bucket_logic": stale_bucket_counts.get("logic", 0),
        "stale_comment_bucket_grounding": stale_bucket_counts.get("grounding", 0),
        "stale_comment_bucket_measurement": stale_bucket_counts.get("measurement", 0),
        "stale_comment_bucket_compliance": stale_bucket_counts.get("compliance", 0),
        "stale_comment_bucket_general": stale_bucket_counts.get("general", 0),
        "smart_field_coverage_rate": mel.get("smart_field_coverage_rate"),
        "means_of_verification_coverage_rate": mel.get("means_of_verification_coverage_rate"),
        "owner_coverage_rate": mel.get("owner_coverage_rate"),
        "complete_logframe_operational_coverage": (
            1 if mov_rate == 1.0 and owner_rate == 1.0 and smart_rate == 1.0 else 0
        ),
        **BASELINE_FIELD_DEFAULTS,
        "baseline_present": 0,
        "measured_baseline_present": 0,
        "delta_time_to_first_draft_seconds": "",
        "delta_time_to_terminal_seconds": "",
        "delta_review_loops": "",
        "time_to_first_draft_improvement_rate": "",
        "time_to_terminal_improvement_rate": "",
        "review_loops_improvement_rate": "",
    }


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "case_dir",
        "preset_key",
        "donor_id",
        "job_id",
        "status",
        "hitl_enabled",
        "quality_score",
        "critic_score",
        "citation_count",
        "time_to_first_draft_seconds",
        "time_to_terminal_seconds",
        "time_in_pending_hitl_seconds",
        "status_change_count",
        "pause_count",
        "resume_count",
        "grounding_risk_level",
        "retrieval_expected",
        "architect_retrieval_hits_count",
        "architect_retrieval_used_results",
        "architect_retrieval_grounded_citation_count",
        "architect_retrieval_grounded_citation_rate",
        "architect_fallback_namespace_citation_count",
        "architect_primary_evidence_signal",
        "architect_evidence_signal_mix",
        "mel_retrieval_hits_count",
        "mel_retrieval_used",
        "mel_retrieval_grounded_citation_count",
        "mel_retrieval_grounded_citation_rate",
        "mel_fallback_namespace_citation_count",
        "mel_primary_evidence_signal",
        "open_critic_findings",
        "high_severity_open_findings",
        "resolved_critic_findings",
        "acknowledged_critic_findings",
        "critic_finding_resolution_rate",
        "critic_finding_acknowledgment_rate",
        "open_review_comments",
        "resolved_review_comments",
        "acknowledged_review_comments",
        "pending_review_comments",
        "overdue_review_comments",
        "stale_open_review_comments",
        "linked_review_comments",
        "orphan_linked_review_comments",
        "review_comment_resolution_rate",
        "review_comment_acknowledgment_rate",
        "reviewer_workflow_resolution_rate",
        "reviewer_workflow_acknowledgment_rate",
        "finding_ack_queue_count",
        "finding_resolve_queue_count",
        "comment_ack_queue_count",
        "comment_resolve_queue_count",
        "comment_reopen_queue_count",
        "finding_ack_completed_count",
        "finding_resolve_completed_count",
        "comment_ack_completed_count",
        "comment_resolve_completed_count",
        "comment_reopen_completed_count",
        "dominant_completed_action",
        "finding_ack_net_delta",
        "finding_resolve_net_delta",
        "comment_ack_net_delta",
        "comment_resolve_net_delta",
        "comment_reopen_net_delta",
        "next_primary_action",
        "review_workflow_policy_status",
        "review_workflow_policy_go_no_go_flag",
        "review_workflow_policy_breach_count",
        "review_workflow_policy_attention_count",
        "review_workflow_next_operational_action",
        "fallback_strategy_citations",
        "low_confidence_citations",
        "next_review_bucket",
        "next_recommended_action",
        "next_comment_section",
        "next_comment_bucket",
        "next_comment_action",
        "comment_age_lt_24h",
        "comment_age_d1_3",
        "comment_age_d3_7",
        "comment_age_gt_7d",
        "stale_comment_bucket_logic",
        "stale_comment_bucket_grounding",
        "stale_comment_bucket_measurement",
        "stale_comment_bucket_compliance",
        "stale_comment_bucket_general",
        "smart_field_coverage_rate",
        "means_of_verification_coverage_rate",
        "owner_coverage_rate",
        "complete_logframe_operational_coverage",
        "baseline_time_to_first_draft_seconds",
        "baseline_time_to_terminal_seconds",
        "baseline_review_loops",
        "baseline_type",
        "baseline_method",
        "baseline_source",
        "baseline_confidence",
        "baseline_owner",
        "baseline_capture_date",
        "baseline_notes",
        "baseline_present",
        "measured_baseline_present",
        "delta_time_to_first_draft_seconds",
        "delta_time_to_terminal_seconds",
        "delta_review_loops",
        "time_to_first_draft_improvement_rate",
        "time_to_terminal_improvement_rate",
        "review_loops_improvement_rate",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _write_summary_csv(path: Path, summary: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summary.keys()))
        writer.writeheader()
        writer.writerow(summary)


def _build_summary_payload(rows: list[dict[str, Any]], *, pilot_pack_name: str) -> dict[str, Any]:
    measured_rows = [row for row in rows if str(row.get("baseline_type") or "").strip().lower() == "measured"]
    avg_quality = _avg([_safe_float(row.get("quality_score")) for row in rows])
    avg_critic = _avg([_safe_float(row.get("critic_score")) for row in rows])
    avg_first_draft = _avg([_safe_float(row.get("time_to_first_draft_seconds")) for row in rows])
    avg_terminal = _avg([_safe_float(row.get("time_to_terminal_seconds")) for row in rows])
    avg_pending_hitl = _avg([_safe_float(row.get("time_in_pending_hitl_seconds")) for row in rows])
    avg_citations = _avg([_safe_int(row.get("citation_count")) for row in rows])
    avg_architect_hits = _avg([_safe_int(row.get("architect_retrieval_hits_count")) for row in rows])
    avg_architect_used_results = _avg([_safe_int(row.get("architect_retrieval_used_results")) for row in rows])
    avg_architect_grounded_count = _avg(
        [_safe_int(row.get("architect_retrieval_grounded_citation_count")) for row in rows]
    )
    avg_architect_grounded_rate = _avg(
        [_safe_float(row.get("architect_retrieval_grounded_citation_rate")) for row in rows]
    )
    avg_architect_fallback_count = _avg(
        [_safe_int(row.get("architect_fallback_namespace_citation_count")) for row in rows]
    )
    avg_mel_hits = _avg([_safe_int(row.get("mel_retrieval_hits_count")) for row in rows])
    avg_mel_grounded_count = _avg([_safe_int(row.get("mel_retrieval_grounded_citation_count")) for row in rows])
    avg_mel_grounded_rate = _avg([_safe_float(row.get("mel_retrieval_grounded_citation_rate")) for row in rows])
    avg_mel_fallback_count = _avg([_safe_int(row.get("mel_fallback_namespace_citation_count")) for row in rows])
    avg_mel_hits = _avg([_safe_int(row.get("mel_retrieval_hits_count")) for row in rows])
    avg_mel_grounded_count = _avg([_safe_int(row.get("mel_retrieval_grounded_citation_count")) for row in rows])
    avg_mel_grounded_rate = _avg([_safe_float(row.get("mel_retrieval_grounded_citation_rate")) for row in rows])
    avg_mel_fallback_count = _avg([_safe_int(row.get("mel_fallback_namespace_citation_count")) for row in rows])
    avg_mel_hits = _avg([_safe_int(row.get("mel_retrieval_hits_count")) for row in rows])
    avg_mel_grounded_count = _avg([_safe_int(row.get("mel_retrieval_grounded_citation_count")) for row in rows])
    avg_mel_grounded_rate = _avg([_safe_float(row.get("mel_retrieval_grounded_citation_rate")) for row in rows])
    avg_mel_fallback_count = _avg([_safe_int(row.get("mel_fallback_namespace_citation_count")) for row in rows])
    mel_signal_totals: dict[str, int] = {}
    for row in rows:
        token = str(row.get("mel_primary_evidence_signal") or "").strip()
        if token:
            mel_signal_totals[token] = mel_signal_totals.get(token, 0) + 1
    top_mel_signal = max(mel_signal_totals.items(), key=lambda item: item[1])[0] if mel_signal_totals else ""
    avg_open_findings = _avg([_safe_int(row.get("open_critic_findings")) for row in rows])
    avg_resolved_findings = _avg([_safe_int(row.get("resolved_critic_findings")) for row in rows])
    avg_ack_findings = _avg([_safe_int(row.get("acknowledged_critic_findings")) for row in rows])
    avg_fallback_citations = _avg([_safe_int(row.get("fallback_strategy_citations")) for row in rows])
    avg_low_confidence = _avg([_safe_int(row.get("low_confidence_citations")) for row in rows])
    avg_open_comments = _avg([_safe_int(row.get("open_review_comments")) for row in rows])
    avg_resolved_comments = _avg([_safe_int(row.get("resolved_review_comments")) for row in rows])
    avg_ack_comments = _avg([_safe_int(row.get("acknowledged_review_comments")) for row in rows])
    avg_overdue_comments = _avg([_safe_int(row.get("overdue_review_comments")) for row in rows])
    avg_stale_comments = _avg([_safe_int(row.get("stale_open_review_comments")) for row in rows])
    avg_comment_resolution_rate = _avg([_safe_float(row.get("review_comment_resolution_rate")) for row in rows])
    avg_comment_ack_rate = _avg([_safe_float(row.get("review_comment_acknowledgment_rate")) for row in rows])
    avg_reviewer_workflow_resolution_rate = _avg(
        [_safe_float(row.get("reviewer_workflow_resolution_rate")) for row in rows]
    )
    avg_reviewer_workflow_ack_rate = _avg(
        [_safe_float(row.get("reviewer_workflow_acknowledgment_rate")) for row in rows]
    )
    avg_critic_finding_resolution_rate = _avg([_safe_float(row.get("critic_finding_resolution_rate")) for row in rows])
    avg_critic_finding_ack_rate = _avg([_safe_float(row.get("critic_finding_acknowledgment_rate")) for row in rows])
    avg_comment_age_d3_7 = _avg([_safe_int(row.get("comment_age_d3_7")) for row in rows])
    avg_comment_age_gt_7d = _avg([_safe_int(row.get("comment_age_gt_7d")) for row in rows])
    avg_finding_ack_queue = _avg([_safe_int(row.get("finding_ack_queue_count")) for row in rows])
    avg_finding_resolve_queue = _avg([_safe_int(row.get("finding_resolve_queue_count")) for row in rows])
    avg_comment_ack_queue = _avg([_safe_int(row.get("comment_ack_queue_count")) for row in rows])
    avg_comment_resolve_queue = _avg([_safe_int(row.get("comment_resolve_queue_count")) for row in rows])
    avg_comment_reopen_queue = _avg([_safe_int(row.get("comment_reopen_queue_count")) for row in rows])
    avg_finding_ack_completed = _avg([_safe_int(row.get("finding_ack_completed_count")) for row in rows])
    avg_finding_resolve_completed = _avg([_safe_int(row.get("finding_resolve_completed_count")) for row in rows])
    avg_comment_ack_completed = _avg([_safe_int(row.get("comment_ack_completed_count")) for row in rows])
    avg_comment_resolve_completed = _avg([_safe_int(row.get("comment_resolve_completed_count")) for row in rows])
    avg_comment_reopen_completed = _avg([_safe_int(row.get("comment_reopen_completed_count")) for row in rows])
    avg_finding_ack_net_delta = _avg([_safe_int(row.get("finding_ack_net_delta")) for row in rows])
    avg_finding_resolve_net_delta = _avg([_safe_int(row.get("finding_resolve_net_delta")) for row in rows])
    avg_comment_ack_net_delta = _avg([_safe_int(row.get("comment_ack_net_delta")) for row in rows])
    avg_comment_resolve_net_delta = _avg([_safe_int(row.get("comment_resolve_net_delta")) for row in rows])
    avg_comment_reopen_net_delta = _avg([_safe_int(row.get("comment_reopen_net_delta")) for row in rows])
    dominant_completed_action = next(
        (
            str(row.get("dominant_completed_action") or "").strip()
            for row in rows
            if str(row.get("dominant_completed_action") or "").strip()
        ),
        "",
    )
    avg_mel_hits = _avg([_safe_int(row.get("mel_retrieval_hits_count")) for row in rows])
    avg_mel_grounded_count = _avg([_safe_int(row.get("mel_retrieval_grounded_citation_count")) for row in rows])
    avg_mel_grounded_rate = _avg([_safe_float(row.get("mel_retrieval_grounded_citation_rate")) for row in rows])
    avg_mel_fallback_count = _avg([_safe_int(row.get("mel_fallback_namespace_citation_count")) for row in rows])
    avg_mel_hits = _avg([_safe_int(row.get("mel_retrieval_hits_count")) for row in rows])
    avg_mel_grounded_count = _avg([_safe_int(row.get("mel_retrieval_grounded_citation_count")) for row in rows])
    avg_mel_grounded_rate = _avg([_safe_float(row.get("mel_retrieval_grounded_citation_rate")) for row in rows])
    avg_mel_fallback_count = _avg([_safe_int(row.get("mel_fallback_namespace_citation_count")) for row in rows])
    stale_bucket_totals = {
        "logic": sum(int(_safe_int(row.get("stale_comment_bucket_logic")) or 0) for row in rows),
        "grounding": sum(int(_safe_int(row.get("stale_comment_bucket_grounding")) or 0) for row in rows),
        "measurement": sum(int(_safe_int(row.get("stale_comment_bucket_measurement")) or 0) for row in rows),
        "compliance": sum(int(_safe_int(row.get("stale_comment_bucket_compliance")) or 0) for row in rows),
        "general": sum(int(_safe_int(row.get("stale_comment_bucket_general")) or 0) for row in rows),
    }
    top_stale_bucket = (
        max(stale_bucket_totals.items(), key=lambda item: item[1])[0] if any(stale_bucket_totals.values()) else ""
    )
    avg_smart_coverage = _avg([_safe_float(row.get("smart_field_coverage_rate")) for row in rows])
    avg_mov_coverage = _avg([_safe_float(row.get("means_of_verification_coverage_rate")) for row in rows])
    avg_owner_coverage = _avg([_safe_float(row.get("owner_coverage_rate")) for row in rows])
    measured_baseline_cases = sum(_safe_int(row.get("measured_baseline_present")) == 1 for row in rows)
    illustrative_baseline_cases = sum(
        str(row.get("baseline_type") or "").strip().lower() == "illustrative" for row in rows
    )
    avg_baseline_confidence_measured = _avg(
        [
            _safe_float(row.get("baseline_confidence"))
            for row in measured_rows
            if _safe_float(row.get("baseline_confidence")) is not None
        ]
    )
    avg_first_draft_delta = _avg(
        [
            _safe_float(row.get("delta_time_to_first_draft_seconds"))
            for row in rows
            if str(row.get("baseline_type") or "").strip().lower() == "measured"
        ]
    )
    avg_terminal_delta = _avg(
        [
            _safe_float(row.get("delta_time_to_terminal_seconds"))
            for row in rows
            if str(row.get("baseline_type") or "").strip().lower() == "measured"
        ]
    )
    avg_review_loops_delta = _avg(
        [
            _safe_float(row.get("delta_review_loops"))
            for row in rows
            if str(row.get("baseline_type") or "").strip().lower() == "measured"
        ]
    )
    avg_first_draft_improvement = _avg(
        [
            _safe_float(row.get("time_to_first_draft_improvement_rate"))
            for row in rows
            if str(row.get("baseline_type") or "").strip().lower() == "measured"
        ]
    )
    avg_terminal_improvement = _avg(
        [
            _safe_float(row.get("time_to_terminal_improvement_rate"))
            for row in rows
            if str(row.get("baseline_type") or "").strip().lower() == "measured"
        ]
    )
    avg_review_loops_improvement = _avg(
        [
            _safe_float(row.get("review_loops_improvement_rate"))
            for row in rows
            if str(row.get("baseline_type") or "").strip().lower() == "measured"
        ]
    )
    complete_logframe_cases = sum(_safe_int(row.get("complete_logframe_operational_coverage")) == 1 for row in rows)
    next_bucket = next(
        (
            str(row.get("next_review_bucket") or "").strip()
            for row in rows
            if str(row.get("next_review_bucket") or "").strip()
        ),
        "",
    )
    next_action = next(
        (
            str(row.get("next_recommended_action") or "").strip()
            for row in rows
            if str(row.get("next_recommended_action") or "").strip()
        ),
        "",
    )
    next_comment_section = next(
        (
            str(row.get("next_comment_section") or "").strip()
            for row in rows
            if str(row.get("next_comment_section") or "").strip()
        ),
        "",
    )
    next_comment_bucket = next(
        (
            str(row.get("next_comment_bucket") or "").strip()
            for row in rows
            if str(row.get("next_comment_bucket") or "").strip()
        ),
        "",
    )
    next_comment_action = next(
        (
            str(row.get("next_comment_action") or "").strip()
            for row in rows
            if str(row.get("next_comment_action") or "").strip()
        ),
        "",
    )
    next_primary_action = next(
        (
            str(row.get("next_primary_action") or "").strip()
            for row in rows
            if str(row.get("next_primary_action") or "").strip()
        ),
        "",
    )
    policy_status_rank = {"breach": 3, "attention": 2, "healthy": 1}
    policy_status = ""
    policy_go_no_go_flag = ""
    policy_next_operational_action = ""
    policy_breach_count = 0
    policy_attention_count = 0
    architect_signal_totals: dict[str, int] = {}
    mel_signal_totals: dict[str, int] = {}
    mel_signal_totals: dict[str, int] = {}
    mel_signal_totals: dict[str, int] = {}
    mel_signal_totals: dict[str, int] = {}
    for row in rows:
        current_status = str(row.get("review_workflow_policy_status") or "").strip().lower()
        if current_status and policy_status_rank.get(current_status, 0) > policy_status_rank.get(policy_status, 0):
            policy_status = current_status
            policy_go_no_go_flag = str(row.get("review_workflow_policy_go_no_go_flag") or "").strip().lower()
            policy_next_operational_action = str(row.get("review_workflow_next_operational_action") or "").strip()
        policy_breach_count += int(_safe_int(row.get("review_workflow_policy_breach_count")) or 0)
        policy_attention_count += int(_safe_int(row.get("review_workflow_policy_attention_count")) or 0)
        mix = str(row.get("architect_evidence_signal_mix") or "").strip()
        if mix and mix != "-":
            for part in mix.split(","):
                token = str(part or "").strip()
                if "=" not in token:
                    continue
                key, value = token.split("=", 1)
                key = str(key).strip()
                if not key:
                    continue
                architect_signal_totals[key] = architect_signal_totals.get(key, 0) + int(_safe_int(value) or 0)
        mel_signal = str(row.get("mel_primary_evidence_signal") or "").strip()
        if mel_signal:
            mel_signal_totals[mel_signal] = mel_signal_totals.get(mel_signal, 0) + 1
    top_architect_signal = (
        max(architect_signal_totals.items(), key=lambda item: item[1])[0] if architect_signal_totals else ""
    )
    top_mel_signal = max(mel_signal_totals.items(), key=lambda item: item[1])[0] if mel_signal_totals else ""
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pilot_pack_name": pilot_pack_name,
        "case_count": len(rows),
        "avg_quality_score": avg_quality,
        "avg_critic_score": avg_critic,
        "avg_time_to_first_draft_seconds": avg_first_draft,
        "avg_time_to_terminal_seconds": avg_terminal,
        "avg_time_in_pending_hitl_seconds": avg_pending_hitl,
        "avg_citation_count": avg_citations,
        "avg_architect_retrieval_hits_count": avg_architect_hits,
        "avg_architect_retrieval_used_results": avg_architect_used_results,
        "avg_architect_retrieval_grounded_citation_count": avg_architect_grounded_count,
        "avg_architect_retrieval_grounded_citation_rate": avg_architect_grounded_rate,
        "avg_architect_fallback_namespace_citation_count": avg_architect_fallback_count,
        "architect_evidence_signal_mix": _bucket_mix_text(architect_signal_totals),
        "top_architect_evidence_signal": top_architect_signal or None,
        "avg_mel_retrieval_hits_count": avg_mel_hits,
        "avg_mel_retrieval_grounded_citation_count": avg_mel_grounded_count,
        "avg_mel_retrieval_grounded_citation_rate": avg_mel_grounded_rate,
        "avg_mel_fallback_namespace_citation_count": avg_mel_fallback_count,
        "mel_evidence_signal_mix": _bucket_mix_text(mel_signal_totals),
        "top_mel_evidence_signal": top_mel_signal or None,
        "avg_open_critic_findings": avg_open_findings,
        "avg_acknowledged_critic_findings": avg_ack_findings,
        "avg_resolved_critic_findings": avg_resolved_findings,
        "avg_open_review_comments": avg_open_comments,
        "avg_acknowledged_review_comments": avg_ack_comments,
        "avg_resolved_review_comments": avg_resolved_comments,
        "avg_overdue_review_comments": avg_overdue_comments,
        "avg_stale_open_review_comments": avg_stale_comments,
        "avg_review_comment_resolution_rate": avg_comment_resolution_rate,
        "avg_review_comment_acknowledgment_rate": avg_comment_ack_rate,
        "avg_reviewer_workflow_resolution_rate": avg_reviewer_workflow_resolution_rate,
        "avg_reviewer_workflow_acknowledgment_rate": avg_reviewer_workflow_ack_rate,
        "avg_critic_finding_resolution_rate": avg_critic_finding_resolution_rate,
        "avg_critic_finding_acknowledgment_rate": avg_critic_finding_ack_rate,
        "avg_finding_ack_queue": avg_finding_ack_queue,
        "avg_finding_resolve_queue": avg_finding_resolve_queue,
        "avg_comment_ack_queue": avg_comment_ack_queue,
        "avg_comment_resolve_queue": avg_comment_resolve_queue,
        "avg_comment_reopen_queue": avg_comment_reopen_queue,
        "avg_finding_ack_completed_count": avg_finding_ack_completed,
        "avg_finding_resolve_completed_count": avg_finding_resolve_completed,
        "avg_comment_ack_completed_count": avg_comment_ack_completed,
        "avg_comment_resolve_completed_count": avg_comment_resolve_completed,
        "avg_comment_reopen_completed_count": avg_comment_reopen_completed,
        "avg_finding_ack_net_delta": avg_finding_ack_net_delta,
        "avg_finding_resolve_net_delta": avg_finding_resolve_net_delta,
        "avg_comment_ack_net_delta": avg_comment_ack_net_delta,
        "avg_comment_resolve_net_delta": avg_comment_resolve_net_delta,
        "avg_comment_reopen_net_delta": avg_comment_reopen_net_delta,
        "dominant_completed_action": dominant_completed_action or None,
        "avg_comment_age_d3_7": avg_comment_age_d3_7,
        "avg_comment_age_gt_7d": avg_comment_age_gt_7d,
        "stale_comment_bucket_mix": _bucket_mix_text(stale_bucket_totals),
        "top_stale_comment_bucket": top_stale_bucket or None,
        "stale_thread_donor_bucket_mix": _donor_bucket_mix_text(rows),
        "avg_fallback_strategy_citations": avg_fallback_citations,
        "avg_low_confidence_citations": avg_low_confidence,
        "avg_smart_field_coverage_rate": avg_smart_coverage,
        "avg_means_of_verification_coverage_rate": avg_mov_coverage,
        "avg_owner_coverage_rate": avg_owner_coverage,
        "measured_baseline_case_count": measured_baseline_cases,
        "illustrative_baseline_case_count": illustrative_baseline_cases,
        "measured_baseline_coverage_ratio": round(measured_baseline_cases / len(rows), 4) if rows else None,
        "illustrative_baseline_coverage_ratio": round(illustrative_baseline_cases / len(rows), 4) if rows else None,
        "avg_measured_baseline_confidence": avg_baseline_confidence_measured,
        "avg_time_to_first_draft_delta_seconds_measured": avg_first_draft_delta,
        "avg_time_to_terminal_delta_seconds_measured": avg_terminal_delta,
        "avg_review_loops_delta_measured": avg_review_loops_delta,
        "avg_time_to_first_draft_improvement_rate_measured": avg_first_draft_improvement,
        "avg_time_to_terminal_improvement_rate_measured": avg_terminal_improvement,
        "avg_review_loops_improvement_rate_measured": avg_review_loops_improvement,
        "complete_logframe_operational_coverage_cases": complete_logframe_cases,
        "complete_logframe_operational_coverage_ratio": round(complete_logframe_cases / len(rows), 4) if rows else None,
        "portfolio_next_primary_action": next_primary_action or None,
        "portfolio_review_workflow_policy_status": policy_status or None,
        "portfolio_review_workflow_policy_go_no_go_flag": policy_go_no_go_flag or None,
        "portfolio_review_workflow_policy_breach_count": policy_breach_count,
        "portfolio_review_workflow_policy_attention_count": policy_attention_count,
        "portfolio_review_workflow_next_operational_action": policy_next_operational_action or None,
        "portfolio_next_review_bucket": next_bucket or None,
        "portfolio_next_recommended_action": next_action or None,
        "portfolio_next_comment_section": next_comment_section or None,
        "portfolio_next_comment_bucket": next_comment_bucket or None,
        "portfolio_next_comment_action": next_comment_action or None,
    }


def _build_markdown(rows: list[dict[str, Any]], *, pilot_pack_name: str) -> str:
    avg_quality = _avg([_safe_float(row.get("quality_score")) for row in rows])
    avg_critic = _avg([_safe_float(row.get("critic_score")) for row in rows])
    avg_first_draft = _avg([_safe_float(row.get("time_to_first_draft_seconds")) for row in rows])
    avg_terminal = _avg([_safe_float(row.get("time_to_terminal_seconds")) for row in rows])
    avg_pending_hitl = _avg([_safe_float(row.get("time_in_pending_hitl_seconds")) for row in rows])
    avg_citations = _avg([_safe_int(row.get("citation_count")) for row in rows])
    avg_architect_hits = _avg([_safe_int(row.get("architect_retrieval_hits_count")) for row in rows])
    avg_architect_used_results = _avg([_safe_int(row.get("architect_retrieval_used_results")) for row in rows])
    avg_architect_grounded_count = _avg(
        [_safe_int(row.get("architect_retrieval_grounded_citation_count")) for row in rows]
    )
    avg_architect_grounded_rate = _avg(
        [_safe_float(row.get("architect_retrieval_grounded_citation_rate")) for row in rows]
    )
    avg_architect_fallback_count = _avg(
        [_safe_int(row.get("architect_fallback_namespace_citation_count")) for row in rows]
    )
    avg_open_findings = _avg([_safe_int(row.get("open_critic_findings")) for row in rows])
    avg_resolved_findings = _avg([_safe_int(row.get("resolved_critic_findings")) for row in rows])
    avg_ack_findings = _avg([_safe_int(row.get("acknowledged_critic_findings")) for row in rows])
    avg_fallback_citations = _avg([_safe_int(row.get("fallback_strategy_citations")) for row in rows])
    avg_low_confidence = _avg([_safe_int(row.get("low_confidence_citations")) for row in rows])
    avg_open_comments = _avg([_safe_int(row.get("open_review_comments")) for row in rows])
    avg_resolved_comments = _avg([_safe_int(row.get("resolved_review_comments")) for row in rows])
    avg_ack_comments = _avg([_safe_int(row.get("acknowledged_review_comments")) for row in rows])
    avg_overdue_comments = _avg([_safe_int(row.get("overdue_review_comments")) for row in rows])
    avg_stale_comments = _avg([_safe_int(row.get("stale_open_review_comments")) for row in rows])
    avg_comment_resolution_rate = _avg([_safe_float(row.get("review_comment_resolution_rate")) for row in rows])
    avg_comment_ack_rate = _avg([_safe_float(row.get("review_comment_acknowledgment_rate")) for row in rows])
    avg_reviewer_workflow_resolution_rate = _avg(
        [_safe_float(row.get("reviewer_workflow_resolution_rate")) for row in rows]
    )
    avg_reviewer_workflow_ack_rate = _avg(
        [_safe_float(row.get("reviewer_workflow_acknowledgment_rate")) for row in rows]
    )
    avg_critic_finding_resolution_rate = _avg([_safe_float(row.get("critic_finding_resolution_rate")) for row in rows])
    avg_critic_finding_ack_rate = _avg([_safe_float(row.get("critic_finding_acknowledgment_rate")) for row in rows])
    avg_comment_age_d3_7 = _avg([_safe_int(row.get("comment_age_d3_7")) for row in rows])
    avg_comment_age_gt_7d = _avg([_safe_int(row.get("comment_age_gt_7d")) for row in rows])
    avg_finding_ack_queue = _avg([_safe_int(row.get("finding_ack_queue_count")) for row in rows])
    avg_finding_resolve_queue = _avg([_safe_int(row.get("finding_resolve_queue_count")) for row in rows])
    avg_comment_ack_queue = _avg([_safe_int(row.get("comment_ack_queue_count")) for row in rows])
    avg_comment_resolve_queue = _avg([_safe_int(row.get("comment_resolve_queue_count")) for row in rows])
    avg_comment_reopen_queue = _avg([_safe_int(row.get("comment_reopen_queue_count")) for row in rows])
    avg_finding_ack_completed = _avg([_safe_int(row.get("finding_ack_completed_count")) for row in rows])
    avg_finding_resolve_completed = _avg([_safe_int(row.get("finding_resolve_completed_count")) for row in rows])
    avg_comment_ack_completed = _avg([_safe_int(row.get("comment_ack_completed_count")) for row in rows])
    avg_comment_resolve_completed = _avg([_safe_int(row.get("comment_resolve_completed_count")) for row in rows])
    avg_comment_reopen_completed = _avg([_safe_int(row.get("comment_reopen_completed_count")) for row in rows])
    avg_finding_ack_net_delta = _avg([_safe_int(row.get("finding_ack_net_delta")) for row in rows])
    avg_finding_resolve_net_delta = _avg([_safe_int(row.get("finding_resolve_net_delta")) for row in rows])
    avg_comment_ack_net_delta = _avg([_safe_int(row.get("comment_ack_net_delta")) for row in rows])
    avg_comment_resolve_net_delta = _avg([_safe_int(row.get("comment_resolve_net_delta")) for row in rows])
    avg_comment_reopen_net_delta = _avg([_safe_int(row.get("comment_reopen_net_delta")) for row in rows])
    dominant_completed_action = next(
        (
            str(row.get("dominant_completed_action") or "").strip()
            for row in rows
            if str(row.get("dominant_completed_action") or "").strip()
        ),
        "",
    )
    avg_mel_hits = _avg([_safe_int(row.get("mel_retrieval_hits_count")) for row in rows])
    avg_mel_grounded_count = _avg([_safe_int(row.get("mel_retrieval_grounded_citation_count")) for row in rows])
    avg_mel_grounded_rate = _avg([_safe_float(row.get("mel_retrieval_grounded_citation_rate")) for row in rows])
    avg_mel_fallback_count = _avg([_safe_int(row.get("mel_fallback_namespace_citation_count")) for row in rows])
    stale_bucket_totals = {
        "logic": sum(int(_safe_int(row.get("stale_comment_bucket_logic")) or 0) for row in rows),
        "grounding": sum(int(_safe_int(row.get("stale_comment_bucket_grounding")) or 0) for row in rows),
        "measurement": sum(int(_safe_int(row.get("stale_comment_bucket_measurement")) or 0) for row in rows),
        "compliance": sum(int(_safe_int(row.get("stale_comment_bucket_compliance")) or 0) for row in rows),
        "general": sum(int(_safe_int(row.get("stale_comment_bucket_general")) or 0) for row in rows),
    }
    top_stale_bucket = (
        max(stale_bucket_totals.items(), key=lambda item: item[1])[0] if any(stale_bucket_totals.values()) else ""
    )
    avg_smart_coverage = _avg([_safe_float(row.get("smart_field_coverage_rate")) for row in rows])
    avg_mov_coverage = _avg([_safe_float(row.get("means_of_verification_coverage_rate")) for row in rows])
    avg_owner_coverage = _avg([_safe_float(row.get("owner_coverage_rate")) for row in rows])
    measured_baseline_cases = sum(_safe_int(row.get("measured_baseline_present")) == 1 for row in rows)
    illustrative_baseline_cases = sum(
        str(row.get("baseline_type") or "").strip().lower() == "illustrative" for row in rows
    )
    avg_baseline_confidence_measured = _avg(
        [
            _safe_float(row.get("baseline_confidence"))
            for row in rows
            if str(row.get("baseline_type") or "").strip().lower() == "measured"
            and _safe_float(row.get("baseline_confidence")) is not None
        ]
    )
    avg_first_draft_delta = _avg(
        [
            _safe_float(row.get("delta_time_to_first_draft_seconds"))
            for row in rows
            if str(row.get("baseline_type") or "").strip().lower() == "measured"
        ]
    )
    avg_terminal_delta = _avg(
        [
            _safe_float(row.get("delta_time_to_terminal_seconds"))
            for row in rows
            if str(row.get("baseline_type") or "").strip().lower() == "measured"
        ]
    )
    avg_review_loops_delta = _avg(
        [
            _safe_float(row.get("delta_review_loops"))
            for row in rows
            if str(row.get("baseline_type") or "").strip().lower() == "measured"
        ]
    )
    avg_first_draft_improvement = _avg(
        [
            _safe_float(row.get("time_to_first_draft_improvement_rate"))
            for row in rows
            if str(row.get("baseline_type") or "").strip().lower() == "measured"
        ]
    )
    avg_terminal_improvement = _avg(
        [
            _safe_float(row.get("time_to_terminal_improvement_rate"))
            for row in rows
            if str(row.get("baseline_type") or "").strip().lower() == "measured"
        ]
    )
    avg_review_loops_improvement = _avg(
        [
            _safe_float(row.get("review_loops_improvement_rate"))
            for row in rows
            if str(row.get("baseline_type") or "").strip().lower() == "measured"
        ]
    )
    complete_logframe_cases = sum(_safe_int(row.get("complete_logframe_operational_coverage")) == 1 for row in rows)
    next_bucket = next(
        (
            str(row.get("next_review_bucket") or "").strip()
            for row in rows
            if str(row.get("next_review_bucket") or "").strip()
        ),
        "",
    )
    next_action = next(
        (
            str(row.get("next_recommended_action") or "").strip()
            for row in rows
            if str(row.get("next_recommended_action") or "").strip()
        ),
        "",
    )
    next_comment_section = next(
        (
            str(row.get("next_comment_section") or "").strip()
            for row in rows
            if str(row.get("next_comment_section") or "").strip()
        ),
        "",
    )
    next_comment_bucket = next(
        (
            str(row.get("next_comment_bucket") or "").strip()
            for row in rows
            if str(row.get("next_comment_bucket") or "").strip()
        ),
        "",
    )
    next_comment_action = next(
        (
            str(row.get("next_comment_action") or "").strip()
            for row in rows
            if str(row.get("next_comment_action") or "").strip()
        ),
        "",
    )
    next_primary_action = next(
        (
            str(row.get("next_primary_action") or "").strip()
            for row in rows
            if str(row.get("next_primary_action") or "").strip()
        ),
        "",
    )
    policy_status_rank = {"breach": 3, "attention": 2, "healthy": 1}
    policy_status = ""
    policy_go_no_go_flag = ""
    policy_next_operational_action = ""
    policy_breach_count = 0
    policy_attention_count = 0
    architect_signal_totals: dict[str, int] = {}
    mel_signal_totals: dict[str, int] = {}
    for row in rows:
        current_status = str(row.get("review_workflow_policy_status") or "").strip().lower()
        if current_status and policy_status_rank.get(current_status, 0) > policy_status_rank.get(policy_status, 0):
            policy_status = current_status
            policy_go_no_go_flag = str(row.get("review_workflow_policy_go_no_go_flag") or "").strip().lower()
            policy_next_operational_action = str(row.get("review_workflow_next_operational_action") or "").strip()
        policy_breach_count += int(_safe_int(row.get("review_workflow_policy_breach_count")) or 0)
        policy_attention_count += int(_safe_int(row.get("review_workflow_policy_attention_count")) or 0)
        mix = str(row.get("architect_evidence_signal_mix") or "").strip()
        if mix and mix != "-":
            for part in mix.split(","):
                token = str(part or "").strip()
                if "=" not in token:
                    continue
                key, value = token.split("=", 1)
                key = str(key).strip()
                if not key:
                    continue
                architect_signal_totals[key] = architect_signal_totals.get(key, 0) + int(_safe_int(value) or 0)
        mel_signal = str(row.get("mel_primary_evidence_signal") or "").strip()
        if mel_signal:
            mel_signal_totals[mel_signal] = mel_signal_totals.get(mel_signal, 0) + 1
    top_architect_signal = (
        max(architect_signal_totals.items(), key=lambda item: item[1])[0] if architect_signal_totals else ""
    )
    top_mel_signal = max(mel_signal_totals.items(), key=lambda item: item[1])[0] if mel_signal_totals else ""

    lines: list[str] = []
    lines.append("# Pilot Metrics")
    lines.append("")
    lines.append(f"Generated at: {datetime.now(timezone.utc).isoformat()}")
    lines.append(f"- Pilot pack: `{pilot_pack_name}`")
    lines.append("")
    lines.append("## Aggregate Snapshot")
    lines.append(f"- Cases: `{len(rows)}`")
    lines.append(f"- Average quality score: `{_fmt(avg_quality)}`")
    lines.append(f"- Average critic score: `{_fmt(avg_critic)}`")
    lines.append(f"- Average time to first draft (s): `{_fmt(avg_first_draft)}`")
    lines.append(f"- Average time to terminal status (s): `{_fmt(avg_terminal)}`")
    lines.append(f"- Average time in pending HITL (s): `{_fmt(avg_pending_hitl)}`")
    lines.append(f"- Average citation count: `{_fmt(avg_citations)}`")
    lines.append(f"- Average architect retrieval hits per case: `{_fmt(avg_architect_hits)}`")
    lines.append(f"- Average architect used results per case: `{_fmt(avg_architect_used_results)}`")
    lines.append(f"- Average architect grounded citations per case: `{_fmt(avg_architect_grounded_count)}`")
    lines.append(f"- Average architect grounded citation rate: `{_fmt(avg_architect_grounded_rate)}`")
    lines.append(f"- Average architect fallback citations per case: `{_fmt(avg_architect_fallback_count)}`")
    if architect_signal_totals:
        lines.append(f"- Architect evidence signal mix: `{_bucket_mix_text(architect_signal_totals)}`")
    if top_architect_signal:
        lines.append(f"- Top architect evidence signal: `{top_architect_signal}`")
    lines.append(f"- Average MEL retrieval hits per case: `{_fmt(avg_mel_hits)}`")
    lines.append(f"- Average MEL grounded citations per case: `{_fmt(avg_mel_grounded_count)}`")
    lines.append(f"- Average MEL grounded citation rate: `{_fmt(avg_mel_grounded_rate)}`")
    lines.append(f"- Average MEL fallback citations per case: `{_fmt(avg_mel_fallback_count)}`")
    if mel_signal_totals:
        lines.append(f"- MEL evidence signal mix: `{_bucket_mix_text(mel_signal_totals)}`")
    if top_mel_signal:
        lines.append(f"- Top MEL evidence signal: `{top_mel_signal}`")
    lines.append(f"- Average open critic findings per case: `{_fmt(avg_open_findings)}`")
    lines.append(f"- Average acknowledged critic findings per case: `{_fmt(avg_ack_findings)}`")
    lines.append(f"- Average resolved critic findings per case: `{_fmt(avg_resolved_findings)}`")
    lines.append(f"- Average open review comments per case: `{_fmt(avg_open_comments)}`")
    lines.append(f"- Average resolved review comments per case: `{_fmt(avg_resolved_comments)}`")
    lines.append(f"- Average acknowledged review comments per case: `{_fmt(avg_ack_comments)}`")
    lines.append(f"- Average overdue review comments per case: `{_fmt(avg_overdue_comments)}`")
    lines.append(f"- Average stale open review comments per case: `{_fmt(avg_stale_comments)}`")
    lines.append(f"- Average review comment resolution rate: `{_fmt(avg_comment_resolution_rate)}`")
    lines.append(f"- Average review comment acknowledgment rate: `{_fmt(avg_comment_ack_rate)}`")
    lines.append(f"- Average reviewer workflow resolution rate: `{_fmt(avg_reviewer_workflow_resolution_rate)}`")
    lines.append(f"- Average reviewer workflow acknowledgment rate: `{_fmt(avg_reviewer_workflow_ack_rate)}`")
    lines.append(f"- Average critic finding resolution rate: `{_fmt(avg_critic_finding_resolution_rate)}`")
    lines.append(f"- Average critic finding acknowledgment rate: `{_fmt(avg_critic_finding_ack_rate)}`")
    lines.append(f"- Average finding ack queue per case: `{_fmt(avg_finding_ack_queue)}`")
    lines.append(f"- Average finding resolve queue per case: `{_fmt(avg_finding_resolve_queue)}`")
    lines.append(f"- Average comment ack queue per case: `{_fmt(avg_comment_ack_queue)}`")
    lines.append(f"- Average comment resolve queue per case: `{_fmt(avg_comment_resolve_queue)}`")
    lines.append(f"- Average comment reopen queue per case: `{_fmt(avg_comment_reopen_queue)}`")
    lines.append(f"- Average finding acks completed per case: `{_fmt(avg_finding_ack_completed)}`")
    lines.append(f"- Average finding resolves completed per case: `{_fmt(avg_finding_resolve_completed)}`")
    lines.append(f"- Average comment acks completed per case: `{_fmt(avg_comment_ack_completed)}`")
    lines.append(f"- Average comment resolves completed per case: `{_fmt(avg_comment_resolve_completed)}`")
    lines.append(f"- Average comment reopens per case: `{_fmt(avg_comment_reopen_completed)}`")
    lines.append(f"- Average finding ack net delta: `{_fmt(avg_finding_ack_net_delta)}`")
    lines.append(f"- Average finding resolve net delta: `{_fmt(avg_finding_resolve_net_delta)}`")
    lines.append(f"- Average comment ack net delta: `{_fmt(avg_comment_ack_net_delta)}`")
    lines.append(f"- Average comment resolve net delta: `{_fmt(avg_comment_resolve_net_delta)}`")
    lines.append(f"- Average comment reopen net delta: `{_fmt(avg_comment_reopen_net_delta)}`")
    if dominant_completed_action:
        lines.append(f"- Dominant completed workflow action: `{dominant_completed_action}`")
    lines.append(f"- Average comment threads aged 3-7d per case: `{_fmt(avg_comment_age_d3_7)}`")
    lines.append(f"- Average comment threads aged >7d per case: `{_fmt(avg_comment_age_gt_7d)}`")
    if any(stale_bucket_totals.values()):
        lines.append(f"- Stale comment bucket mix: `{_bucket_mix_text(stale_bucket_totals)}`")
        lines.append(f"- Top stale comment bucket: `{top_stale_bucket}`")
        donor_stale_bucket_totals: dict[str, dict[str, int]] = {}
        for row in rows:
            donor = str(row.get("donor_id") or "").strip() or "unknown"
            donor_bucket_counts = donor_stale_bucket_totals.setdefault(
                donor, {"logic": 0, "grounding": 0, "measurement": 0, "compliance": 0, "general": 0}
            )
            donor_bucket_counts["logic"] += int(_safe_int(row.get("stale_comment_bucket_logic")) or 0)
            donor_bucket_counts["grounding"] += int(_safe_int(row.get("stale_comment_bucket_grounding")) or 0)
            donor_bucket_counts["measurement"] += int(_safe_int(row.get("stale_comment_bucket_measurement")) or 0)
            donor_bucket_counts["compliance"] += int(_safe_int(row.get("stale_comment_bucket_compliance")) or 0)
            donor_bucket_counts["general"] += int(_safe_int(row.get("stale_comment_bucket_general")) or 0)
        donor_mix = "; ".join(
            f"{donor}: {_bucket_mix_text(bucket_counts)}"
            for donor, bucket_counts in donor_stale_bucket_totals.items()
            if _bucket_mix_text(bucket_counts) != "-"
        )
        if donor_mix:
            lines.append(f"- Stale thread donor/bucket mix: `{donor_mix}`")
    lines.append(f"- Average fallback/strategy citations per case: `{_fmt(avg_fallback_citations)}`")
    lines.append(f"- Average low-confidence citations per case: `{_fmt(avg_low_confidence)}`")
    lines.append(f"- Average SMART field coverage: `{_fmt(avg_smart_coverage)}`")
    lines.append(f"- Average means-of-verification coverage: `{_fmt(avg_mov_coverage)}`")
    lines.append(f"- Average owner coverage: `{_fmt(avg_owner_coverage)}`")
    lines.append(f"- Cases with complete LogFrame operational coverage: `{complete_logframe_cases}/{len(rows)}`")
    lines.append(f"- Measured baseline cases: `{measured_baseline_cases}/{len(rows)}`")
    lines.append(f"- Illustrative baseline cases: `{illustrative_baseline_cases}/{len(rows)}`")
    lines.append(f"- Measured baseline coverage ratio: `{_fmt(measured_baseline_cases / len(rows) if rows else None)}`")
    lines.append(
        f"- Illustrative baseline coverage ratio: `{_fmt(illustrative_baseline_cases / len(rows) if rows else None)}`"
    )
    if measured_baseline_cases:
        lines.append(f"- Average measured baseline confidence: `{_fmt(avg_baseline_confidence_measured)}`")
    if measured_baseline_cases:
        lines.append(f"- Average measured first-draft delta (s): `{_fmt(avg_first_draft_delta)}`")
        lines.append(f"- Average measured terminal delta (s): `{_fmt(avg_terminal_delta)}`")
        lines.append(f"- Average measured review-loops delta: `{_fmt(avg_review_loops_delta)}`")
        lines.append(f"- Average measured first-draft improvement rate: `{_fmt(avg_first_draft_improvement)}`")
        lines.append(f"- Average measured terminal improvement rate: `{_fmt(avg_terminal_improvement)}`")
        lines.append(f"- Average measured review-loops improvement rate: `{_fmt(avg_review_loops_improvement)}`")
    if next_primary_action:
        lines.append(f"- Portfolio next primary action: `{next_primary_action}`")
    if policy_status:
        lines.append(f"- Review workflow policy status: `{policy_status}`")
    if policy_go_no_go_flag:
        lines.append(f"- Review workflow policy go/no-go: `{policy_go_no_go_flag}`")
    lines.append(f"- Review workflow policy breach count: `{policy_breach_count}`")
    lines.append(f"- Review workflow policy attention count: `{policy_attention_count}`")
    if policy_next_operational_action:
        lines.append(f"- Review workflow next operational action: `{policy_next_operational_action}`")
    if next_bucket:
        lines.append(f"- Portfolio next review bucket: `{next_bucket}`")
    if next_action:
        lines.append(f"- Portfolio next recommended action: {next_action}")
    if next_comment_section:
        lines.append(f"- Portfolio next comment section: `{next_comment_section}`")
    if next_comment_bucket:
        lines.append(f"- Portfolio next comment bucket: `{next_comment_bucket}`")
    if next_comment_action:
        lines.append(f"- Portfolio next comment action: {next_comment_action}")
    lines.append("")
    lines.append("## Case Table")
    lines.append("")
    lines.append(
        "| Preset | Donor | Status | HITL | Quality | Critic | Open Findings | Open Comments | Overdue Comments | Fallback Citations | Next Bucket | Next Comment Section | SMART | MoV | Owner | Complete Ops |"
    )
    lines.append("|---|---|---|---|---:|---:|---:|---:|---:|---:|---|---|---:|---:|---:|---|")
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{row.get('preset_key')}`",
                    f"`{row.get('donor_id')}`",
                    str(row.get("status")),
                    "yes" if row.get("hitl_enabled") else "no",
                    _fmt(_safe_float(row.get("quality_score"))),
                    _fmt(_safe_float(row.get("critic_score"))),
                    _fmt(_safe_int(row.get("open_critic_findings"))),
                    _fmt(_safe_int(row.get("open_review_comments"))),
                    _fmt(_safe_int(row.get("overdue_review_comments"))),
                    _fmt(_safe_int(row.get("fallback_strategy_citations"))),
                    f"`{str(row.get('next_review_bucket') or '-').strip() or '-'}`",
                    f"`{str(row.get('next_comment_section') or '-').strip() or '-'}`",
                    _fmt(_safe_float(row.get("smart_field_coverage_rate"))),
                    _fmt(_safe_float(row.get("means_of_verification_coverage_rate"))),
                    _fmt(_safe_float(row.get("owner_coverage_rate"))),
                    "yes" if _safe_int(row.get("complete_logframe_operational_coverage")) == 1 else "no",
                ]
            )
            + " |"
        )
    lines.append("")
    lines.append("## Baseline Comparison")
    lines.append(
        "- For real pilot evidence, fill `baseline-fill-template.csv` and save it as `measured-baseline.csv` in the pilot pack."
    )
    lines.append(
        "- Then re-run `make pilot-metrics` so measured deltas are merged into `pilot-metrics.csv`, `pilot-metrics.md`, and `pilot-portfolio-summary.*`."
    )
    lines.append(
        "- `benchmark-baseline.*` remains illustrative demo-only context and must not be treated as measured pilot evidence."
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build pilot metrics tables from an existing GrantFlow pilot pack.")
    parser.add_argument("--pilot-pack-dir", default="build/pilot-pack")
    parser.add_argument("--measured-baseline-csv", default="")
    parser.add_argument("--csv-out", default="")
    parser.add_argument("--md-out", default="")
    parser.add_argument("--summary-json-out", default="")
    parser.add_argument("--summary-csv-out", default="")
    args = parser.parse_args()

    pilot_pack_dir = Path(str(args.pilot_pack_dir)).resolve()
    benchmark_path = pilot_pack_dir / "live-runs" / "benchmark-results.json"
    if not benchmark_path.exists():
        raise SystemExit(f"Missing pilot benchmark results: {benchmark_path}")

    benchmark_rows = _read_json(benchmark_path)
    if not isinstance(benchmark_rows, list) or not benchmark_rows:
        raise SystemExit("pilot pack live-runs/benchmark-results.json must contain a non-empty list")

    rows: list[dict[str, Any]] = []
    for benchmark_row in benchmark_rows:
        case_dir_name = str(benchmark_row.get("case_dir") or "").strip()
        if not case_dir_name:
            raise SystemExit(f"Missing case_dir in benchmark row: {benchmark_row}")
        case_dir = pilot_pack_dir / "live-runs" / case_dir_name
        if not case_dir.exists():
            raise SystemExit(f"Missing case directory: {case_dir}")
        rows.append(_build_case_row(case_dir, benchmark_row))

    benchmark_baseline_csv = pilot_pack_dir / "benchmark-baseline.csv"
    rows = _merge_benchmark_baseline(
        rows, benchmark_rows=_read_csv_rows(benchmark_baseline_csv) if benchmark_baseline_csv.exists() else []
    )

    measured_baseline_csv = (
        Path(str(args.measured_baseline_csv)).resolve()
        if str(args.measured_baseline_csv).strip()
        else pilot_pack_dir / "measured-baseline.csv"
    )
    measured_rows = _read_csv_rows(measured_baseline_csv) if measured_baseline_csv.exists() else []
    rows = _merge_measured_baseline(rows, measured_rows=measured_rows)

    csv_out = Path(str(args.csv_out)).resolve() if str(args.csv_out).strip() else pilot_pack_dir / "pilot-metrics.csv"
    md_out = Path(str(args.md_out)).resolve() if str(args.md_out).strip() else pilot_pack_dir / "pilot-metrics.md"
    summary_json_out = (
        Path(str(args.summary_json_out)).resolve()
        if str(args.summary_json_out).strip()
        else pilot_pack_dir / "pilot-portfolio-summary.json"
    )
    summary_csv_out = (
        Path(str(args.summary_csv_out)).resolve()
        if str(args.summary_csv_out).strip()
        else pilot_pack_dir / "pilot-portfolio-summary.csv"
    )

    _write_csv(csv_out, rows)
    md_out.write_text(_build_markdown(rows, pilot_pack_name=pilot_pack_dir.name), encoding="utf-8")
    summary_payload = _build_summary_payload(rows, pilot_pack_name=pilot_pack_dir.name)
    summary_json_out.write_text(json.dumps(summary_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_summary_csv(summary_csv_out, summary_payload)
    print(f"pilot metrics saved to {csv_out}, {md_out}, {summary_json_out}, and {summary_csv_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
