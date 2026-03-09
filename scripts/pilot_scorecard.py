#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REQUIRED_TRACE_FILES = (
    "status.json",
    "quality.json",
    "critic.json",
    "citations.json",
    "versions.json",
    "events.json",
    "export-payload.json",
    "metrics.json",
)

REQUIRED_EXPORT_FILES = (
    "toc-review-package.docx",
    "logframe-review-package.xlsx",
    "review-package.zip",
)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _safe_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _avg(values: list[float | None]) -> float | None:
    clean = [value for value in values if value is not None]
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
    return f"{value:.2f}"


def _pct(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return numerator / denominator


@dataclass
class CaseScorecard:
    case_dir: str
    preset_key: str
    donor_id: str
    status: str
    hitl_enabled: bool
    quality_score: float | None
    critic_score: float | None
    trace_complete: bool
    export_complete: bool
    hitl_history_present: bool
    baseline_present: bool
    open_critic_findings: int | None
    high_severity_open_findings: int | None
    open_review_comments: int | None
    resolved_review_comments: int | None
    acknowledged_review_comments: int | None
    overdue_review_comments: int | None
    stale_open_review_comments: int | None
    orphan_linked_review_comments: int | None
    reviewer_workflow_resolution_rate: float | None
    reviewer_workflow_acknowledgment_rate: float | None
    critic_finding_resolution_rate: float | None
    critic_finding_acknowledgment_rate: float | None
    finding_ack_queue_count: float | None
    finding_resolve_queue_count: float | None
    comment_ack_queue_count: float | None
    comment_resolve_queue_count: float | None
    comment_reopen_queue_count: float | None
    review_workflow_policy_status: str
    review_workflow_policy_go_no_go_flag: str
    review_workflow_policy_breach_count: int | None
    review_workflow_policy_attention_count: int | None
    review_workflow_next_operational_action: str
    comment_age_gt_7d: float | None
    stale_comment_bucket_logic: int | None
    stale_comment_bucket_grounding: int | None
    stale_comment_bucket_measurement: int | None
    stale_comment_bucket_compliance: int | None
    stale_comment_bucket_general: int | None
    fallback_strategy_citations: int | None
    low_confidence_citations: int | None
    smart_field_coverage_rate: float | None
    means_of_verification_coverage_rate: float | None
    owner_coverage_rate: float | None
    complete_logframe_operational_coverage: bool
    architect_retrieval_hits_count: float | None
    architect_retrieval_grounded_citation_rate: float | None
    architect_fallback_namespace_citation_count: float | None
    mel_retrieval_hits_count: float | None
    mel_retrieval_grounded_citation_rate: float | None
    mel_fallback_namespace_citation_count: float | None
    missing_trace_files: list[str]
    missing_export_files: list[str]


def _load_metrics_rows(metrics_csv_path: Path) -> dict[str, dict[str, str]]:
    if not metrics_csv_path.exists():
        return {}

    metrics_rows: dict[str, dict[str, str]] = {}
    with metrics_csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            case_dir = str(row.get("case_dir") or "").strip()
            if not case_dir:
                continue
            metrics_rows[case_dir] = dict(row)
    return metrics_rows


def _first_nonempty_metric(metrics_rows: dict[str, dict[str, str]], key: str) -> str:
    for row in metrics_rows.values():
        value = str(row.get(key) or "").strip()
        if value:
            return value
    return ""


def _missing_files(case_path: Path, required_files: tuple[str, ...]) -> list[str]:
    return [name for name in required_files if not (case_path / name).exists()]


def _load_case_scorecards(
    pilot_pack_dir: Path,
    benchmark_rows: list[dict[str, Any]],
    metrics_rows: dict[str, dict[str, str]],
) -> list[CaseScorecard]:
    cases: list[CaseScorecard] = []
    live_runs_dir = pilot_pack_dir / "live-runs"
    for row in benchmark_rows:
        case_dir = str(row.get("case_dir") or "").strip()
        if not case_dir:
            raise SystemExit(f"Missing case_dir in benchmark row: {row}")
        case_path = live_runs_dir / case_dir
        if not case_path.exists():
            raise SystemExit(f"Missing case directory: {case_path}")

        quality_path = case_path / "quality.json"
        quality_payload = _read_json(quality_path) if quality_path.exists() else {}
        metrics_row = metrics_rows.get(case_dir, {})
        missing_trace_files = _missing_files(case_path, REQUIRED_TRACE_FILES)
        missing_export_files = _missing_files(case_path, REQUIRED_EXPORT_FILES)
        hitl_history_present = (case_path / "hitl-history.json").exists()
        baseline_present = any(
            str(metrics_row.get(key) or "").strip()
            for key in (
                "baseline_time_to_first_draft_seconds",
                "baseline_time_to_terminal_seconds",
                "baseline_review_loops",
                "baseline_notes",
            )
        )

        cases.append(
            CaseScorecard(
                case_dir=case_dir,
                preset_key=str(row.get("preset_key") or "").strip(),
                donor_id=str(row.get("donor_id") or "").strip(),
                status=str(row.get("status") or "").strip(),
                hitl_enabled=bool(row.get("hitl_enabled")),
                quality_score=_safe_float(quality_payload.get("quality_score", row.get("quality_score"))),
                critic_score=_safe_float(quality_payload.get("critic_score", row.get("critic_score"))),
                trace_complete=not missing_trace_files,
                export_complete=not missing_export_files,
                hitl_history_present=hitl_history_present,
                baseline_present=baseline_present,
                open_critic_findings=(
                    int(metrics_row["open_critic_findings"])
                    if str(metrics_row.get("open_critic_findings") or "").strip()
                    else None
                ),
                high_severity_open_findings=(
                    int(metrics_row["high_severity_open_findings"])
                    if str(metrics_row.get("high_severity_open_findings") or "").strip()
                    else None
                ),
                open_review_comments=(
                    int(metrics_row["open_review_comments"])
                    if str(metrics_row.get("open_review_comments") or "").strip()
                    else None
                ),
                resolved_review_comments=(
                    int(metrics_row["resolved_review_comments"])
                    if str(metrics_row.get("resolved_review_comments") or "").strip()
                    else None
                ),
                acknowledged_review_comments=(
                    int(metrics_row["acknowledged_review_comments"])
                    if str(metrics_row.get("acknowledged_review_comments") or "").strip()
                    else None
                ),
                overdue_review_comments=(
                    int(metrics_row["overdue_review_comments"])
                    if str(metrics_row.get("overdue_review_comments") or "").strip()
                    else None
                ),
                stale_open_review_comments=(
                    int(metrics_row["stale_open_review_comments"])
                    if str(metrics_row.get("stale_open_review_comments") or "").strip()
                    else None
                ),
                orphan_linked_review_comments=(
                    int(metrics_row["orphan_linked_review_comments"])
                    if str(metrics_row.get("orphan_linked_review_comments") or "").strip()
                    else None
                ),
                reviewer_workflow_resolution_rate=_safe_float(metrics_row.get("reviewer_workflow_resolution_rate")),
                reviewer_workflow_acknowledgment_rate=_safe_float(
                    metrics_row.get("reviewer_workflow_acknowledgment_rate")
                ),
                critic_finding_resolution_rate=_safe_float(metrics_row.get("critic_finding_resolution_rate")),
                critic_finding_acknowledgment_rate=_safe_float(metrics_row.get("critic_finding_acknowledgment_rate")),
                finding_ack_queue_count=_safe_float(metrics_row.get("finding_ack_queue_count")),
                finding_resolve_queue_count=_safe_float(metrics_row.get("finding_resolve_queue_count")),
                comment_ack_queue_count=_safe_float(metrics_row.get("comment_ack_queue_count")),
                comment_resolve_queue_count=_safe_float(metrics_row.get("comment_resolve_queue_count")),
                comment_reopen_queue_count=_safe_float(metrics_row.get("comment_reopen_queue_count")),
                review_workflow_policy_status=str(metrics_row.get("review_workflow_policy_status") or "").strip(),
                review_workflow_policy_go_no_go_flag=str(
                    metrics_row.get("review_workflow_policy_go_no_go_flag") or ""
                ).strip(),
                review_workflow_policy_breach_count=(
                    int(metrics_row["review_workflow_policy_breach_count"])
                    if str(metrics_row.get("review_workflow_policy_breach_count") or "").strip()
                    else None
                ),
                review_workflow_policy_attention_count=(
                    int(metrics_row["review_workflow_policy_attention_count"])
                    if str(metrics_row.get("review_workflow_policy_attention_count") or "").strip()
                    else None
                ),
                review_workflow_next_operational_action=str(
                    metrics_row.get("review_workflow_next_operational_action") or ""
                ).strip(),
                comment_age_gt_7d=_safe_float(metrics_row.get("comment_age_gt_7d")),
                stale_comment_bucket_logic=(
                    int(metrics_row["stale_comment_bucket_logic"])
                    if str(metrics_row.get("stale_comment_bucket_logic") or "").strip()
                    else None
                ),
                stale_comment_bucket_grounding=(
                    int(metrics_row["stale_comment_bucket_grounding"])
                    if str(metrics_row.get("stale_comment_bucket_grounding") or "").strip()
                    else None
                ),
                stale_comment_bucket_measurement=(
                    int(metrics_row["stale_comment_bucket_measurement"])
                    if str(metrics_row.get("stale_comment_bucket_measurement") or "").strip()
                    else None
                ),
                stale_comment_bucket_compliance=(
                    int(metrics_row["stale_comment_bucket_compliance"])
                    if str(metrics_row.get("stale_comment_bucket_compliance") or "").strip()
                    else None
                ),
                stale_comment_bucket_general=(
                    int(metrics_row["stale_comment_bucket_general"])
                    if str(metrics_row.get("stale_comment_bucket_general") or "").strip()
                    else None
                ),
                fallback_strategy_citations=(
                    int(metrics_row["fallback_strategy_citations"])
                    if str(metrics_row.get("fallback_strategy_citations") or "").strip()
                    else None
                ),
                low_confidence_citations=(
                    int(metrics_row["low_confidence_citations"])
                    if str(metrics_row.get("low_confidence_citations") or "").strip()
                    else None
                ),
                smart_field_coverage_rate=_safe_float(metrics_row.get("smart_field_coverage_rate")),
                means_of_verification_coverage_rate=_safe_float(metrics_row.get("means_of_verification_coverage_rate")),
                owner_coverage_rate=_safe_float(metrics_row.get("owner_coverage_rate")),
                complete_logframe_operational_coverage=(
                    str(metrics_row.get("complete_logframe_operational_coverage") or "").strip() == "1"
                ),
                architect_retrieval_hits_count=_safe_float(metrics_row.get("architect_retrieval_hits_count")),
                architect_retrieval_grounded_citation_rate=_safe_float(
                    metrics_row.get("architect_retrieval_grounded_citation_rate")
                ),
                architect_fallback_namespace_citation_count=_safe_float(
                    metrics_row.get("architect_fallback_namespace_citation_count")
                ),
                mel_retrieval_hits_count=_safe_float(metrics_row.get("mel_retrieval_hits_count")),
                mel_retrieval_grounded_citation_rate=_safe_float(
                    metrics_row.get("mel_retrieval_grounded_citation_rate")
                ),
                mel_fallback_namespace_citation_count=_safe_float(
                    metrics_row.get("mel_fallback_namespace_citation_count")
                ),
                missing_trace_files=missing_trace_files,
                missing_export_files=missing_export_files,
            )
        )
    return cases


def _gate_status(passed: bool, *, conditional: bool = False) -> str:
    if passed:
        return "pass"
    if conditional:
        return "conditional"
    return "fail"


def _build_scorecard(
    cases: list[CaseScorecard],
    *,
    pilot_pack_name: str,
    min_avg_quality: float,
    min_avg_critic: float,
    min_terminal_done_rate: float,
    portfolio_next_bucket: str,
    portfolio_next_action: str,
) -> str:
    total_cases = len(cases)
    done_cases = sum(1 for case in cases if case.status.lower() == "done")
    trace_complete_cases = sum(1 for case in cases if case.trace_complete)
    export_complete_cases = sum(1 for case in cases if case.export_complete)
    baseline_cases = sum(1 for case in cases if case.baseline_present)
    complete_logframe_cases = sum(1 for case in cases if case.complete_logframe_operational_coverage)
    hitl_cases = sum(1 for case in cases if case.hitl_enabled)
    hitl_history_cases = sum(1 for case in cases if case.hitl_enabled and case.hitl_history_present)

    avg_quality = _avg([case.quality_score for case in cases])
    avg_critic = _avg([case.critic_score for case in cases])
    avg_open_findings = _avg(
        [float(case.open_critic_findings) for case in cases if case.open_critic_findings is not None]
    )
    avg_open_comments = _avg(
        [float(case.open_review_comments) for case in cases if case.open_review_comments is not None]
    )
    avg_acknowledged_comments = _avg(
        [float(case.acknowledged_review_comments) for case in cases if case.acknowledged_review_comments is not None]
    )
    avg_overdue_comments = _avg(
        [float(case.overdue_review_comments) for case in cases if case.overdue_review_comments is not None]
    )
    avg_stale_comments = _avg(
        [float(case.stale_open_review_comments) for case in cases if case.stale_open_review_comments is not None]
    )
    avg_reviewer_workflow_resolution = _avg(
        [case.reviewer_workflow_resolution_rate for case in cases if case.reviewer_workflow_resolution_rate is not None]
    )
    avg_reviewer_workflow_ack = _avg(
        [
            case.reviewer_workflow_acknowledgment_rate
            for case in cases
            if case.reviewer_workflow_acknowledgment_rate is not None
        ]
    )
    avg_critic_finding_resolution = _avg(
        [case.critic_finding_resolution_rate for case in cases if case.critic_finding_resolution_rate is not None]
    )
    avg_critic_finding_ack = _avg(
        [
            case.critic_finding_acknowledgment_rate
            for case in cases
            if case.critic_finding_acknowledgment_rate is not None
        ]
    )
    avg_finding_ack_queue = _avg(
        [case.finding_ack_queue_count for case in cases if case.finding_ack_queue_count is not None]
    )
    avg_finding_resolve_queue = _avg(
        [case.finding_resolve_queue_count for case in cases if case.finding_resolve_queue_count is not None]
    )
    avg_comment_ack_queue = _avg(
        [case.comment_ack_queue_count for case in cases if case.comment_ack_queue_count is not None]
    )
    avg_comment_resolve_queue = _avg(
        [case.comment_resolve_queue_count for case in cases if case.comment_resolve_queue_count is not None]
    )
    avg_comment_reopen_queue = _avg(
        [case.comment_reopen_queue_count for case in cases if case.comment_reopen_queue_count is not None]
    )
    policy_status_rank = {"breach": 3, "attention": 2, "healthy": 1}
    portfolio_policy_status = ""
    portfolio_policy_go_no_go = ""
    portfolio_policy_next_action = ""
    total_policy_breaches = 0
    total_policy_attention = 0
    for case in cases:
        current_status = str(case.review_workflow_policy_status or "").strip().lower()
        if current_status and policy_status_rank.get(current_status, 0) > policy_status_rank.get(
            portfolio_policy_status, 0
        ):
            portfolio_policy_status = current_status
            portfolio_policy_go_no_go = str(case.review_workflow_policy_go_no_go_flag or "").strip().lower()
            portfolio_policy_next_action = str(case.review_workflow_next_operational_action or "").strip()
        total_policy_breaches += int(case.review_workflow_policy_breach_count or 0)
        total_policy_attention += int(case.review_workflow_policy_attention_count or 0)
    avg_comment_age_gt_7d = _avg([case.comment_age_gt_7d for case in cases if case.comment_age_gt_7d is not None])
    stale_bucket_totals = {
        "logic": sum(int(case.stale_comment_bucket_logic or 0) for case in cases),
        "grounding": sum(int(case.stale_comment_bucket_grounding or 0) for case in cases),
        "measurement": sum(int(case.stale_comment_bucket_measurement or 0) for case in cases),
        "compliance": sum(int(case.stale_comment_bucket_compliance or 0) for case in cases),
        "general": sum(int(case.stale_comment_bucket_general or 0) for case in cases),
    }
    stale_bucket_mix = ", ".join(f"{bucket}={count}" for bucket, count in stale_bucket_totals.items() if count > 0)
    top_stale_bucket = (
        max(stale_bucket_totals.items(), key=lambda item: item[1])[0] if any(stale_bucket_totals.values()) else ""
    )
    avg_high_severity_findings = _avg(
        [float(case.high_severity_open_findings) for case in cases if case.high_severity_open_findings is not None]
    )
    avg_fallback_citations = _avg(
        [float(case.fallback_strategy_citations) for case in cases if case.fallback_strategy_citations is not None]
    )
    avg_low_confidence_citations = _avg(
        [float(case.low_confidence_citations) for case in cases if case.low_confidence_citations is not None]
    )
    avg_architect_hits = _avg([case.architect_retrieval_hits_count for case in cases])
    avg_architect_grounded_rate = _avg([case.architect_retrieval_grounded_citation_rate for case in cases])
    avg_architect_fallback = _avg([case.architect_fallback_namespace_citation_count for case in cases])
    avg_mel_hits = _avg([case.mel_retrieval_hits_count for case in cases])
    avg_mel_grounded_rate = _avg([case.mel_retrieval_grounded_citation_rate for case in cases])
    avg_mel_fallback = _avg([case.mel_fallback_namespace_citation_count for case in cases])
    avg_smart = _avg([case.smart_field_coverage_rate for case in cases])
    avg_mov = _avg([case.means_of_verification_coverage_rate for case in cases])
    avg_owner = _avg([case.owner_coverage_rate for case in cases])
    done_rate = _pct(done_cases, total_cases)
    baseline_rate = _pct(baseline_cases, total_cases)
    complete_logframe_rate = _pct(complete_logframe_cases, total_cases)

    fail_reasons: list[str] = []
    conditional_reasons: list[str] = []

    if done_rate < min_terminal_done_rate:
        fail_reasons.append(
            f"terminal completion below threshold ({done_cases}/{total_cases}, target >= {min_terminal_done_rate:.0%})"
        )
    if avg_quality is None or avg_quality < min_avg_quality:
        fail_reasons.append(
            f"average quality score below threshold ({_fmt(avg_quality)}, target >= {_fmt(min_avg_quality)})"
        )
    if avg_critic is None or avg_critic < min_avg_critic:
        fail_reasons.append(
            f"average critic score below threshold ({_fmt(avg_critic)}, target >= {_fmt(min_avg_critic)})"
        )
    if trace_complete_cases < total_cases:
        fail_reasons.append(f"trace artifact coverage incomplete ({trace_complete_cases}/{total_cases} cases)")
    if export_complete_cases < total_cases:
        fail_reasons.append(f"export artifact coverage incomplete ({export_complete_cases}/{total_cases} cases)")
    if hitl_cases and hitl_history_cases < hitl_cases:
        fail_reasons.append(f"HITL history missing for enabled cases ({hitl_history_cases}/{hitl_cases})")

    if baseline_cases < total_cases:
        conditional_reasons.append(
            f"baseline comparison not yet captured for all cases ({baseline_cases}/{total_cases})"
        )
    if complete_logframe_cases < total_cases:
        conditional_reasons.append(
            f"logframe operational coverage incomplete ({complete_logframe_cases}/{total_cases} cases)"
        )
    if any((case.open_critic_findings or 0) > 0 for case in cases):
        conditional_reasons.append("open critic findings remain in at least one case")
    if any((case.overdue_review_comments or 0) > 0 for case in cases):
        conditional_reasons.append("overdue reviewer comments remain in at least one case")
    if any((case.stale_open_review_comments or 0) > 0 for case in cases):
        conditional_reasons.append("stale reviewer comment threads remain in at least one case")
    if any((case.orphan_linked_review_comments or 0) > 0 for case in cases):
        conditional_reasons.append("orphan linked reviewer comments remain in at least one case")
    if portfolio_policy_status == "breach":
        conditional_reasons.append("review workflow SLA policy is in breach state")
    elif portfolio_policy_status == "attention":
        conditional_reasons.append("review workflow SLA policy requires operational cleanup before buyer handoff")
    if any((case.fallback_strategy_citations or 0) > 0 for case in cases):
        conditional_reasons.append("fallback/strategy citations remain present in at least one case")
    if hitl_cases == 0:
        conditional_reasons.append("no HITL evidence captured in this pack")

    if fail_reasons:
        verdict = "Not ready"
        readiness = "red"
    elif conditional_reasons:
        verdict = "Proceed with conditions"
        readiness = "amber"
    else:
        verdict = "Proceed to bounded pilot"
        readiness = "green"

    gate_rows = [
        (
            "Terminal completion",
            _gate_status(done_rate >= min_terminal_done_rate),
            f"{done_cases}/{total_cases} done",
            f"target >= {min_terminal_done_rate:.0%}",
        ),
        (
            "Average quality score",
            _gate_status(avg_quality is not None and avg_quality >= min_avg_quality),
            _fmt(avg_quality),
            f"target >= {_fmt(min_avg_quality)}",
        ),
        (
            "Average critic score",
            _gate_status(avg_critic is not None and avg_critic >= min_avg_critic),
            _fmt(avg_critic),
            f"target >= {_fmt(min_avg_critic)}",
        ),
        (
            "Trace artifact coverage",
            _gate_status(trace_complete_cases == total_cases),
            f"{trace_complete_cases}/{total_cases}",
            "status/quality/critic/citations/versions/events/export-payload/metrics",
        ),
        (
            "Export artifact coverage",
            _gate_status(export_complete_cases == total_cases),
            f"{export_complete_cases}/{total_cases}",
            "docx/xlsx/zip for every case",
        ),
        (
            "Baseline comparison coverage",
            _gate_status(baseline_cases == total_cases, conditional=True),
            f"{baseline_cases}/{total_cases}",
            "capture before buyer go/no-go review",
        ),
        (
            "LogFrame operational coverage",
            _gate_status(complete_logframe_cases == total_cases, conditional=True),
            f"{complete_logframe_cases}/{total_cases}",
            "complete SMART + MoV + owner coverage for every case",
        ),
    ]

    lines: list[str] = []
    lines.append("# Pilot Scorecard")
    lines.append("")
    lines.append(f"Generated at: {datetime.now(timezone.utc).isoformat()}")
    lines.append(f"- Pilot pack: `{pilot_pack_name}`")
    lines.append("")
    lines.append("## Executive Verdict")
    lines.append(f"- Verdict: `{verdict}`")
    lines.append(f"- Readiness: `{readiness}`")
    lines.append("")
    lines.append("## Evidence Snapshot")
    lines.append(f"- Cases reviewed: `{total_cases}`")
    lines.append(f"- Terminal done cases: `{done_cases}/{total_cases}`")
    lines.append(f"- Average quality score: `{_fmt(avg_quality)}`")
    lines.append(f"- Average critic score: `{_fmt(avg_critic)}`")
    lines.append(f"- Trace-complete cases: `{trace_complete_cases}/{total_cases}`")
    lines.append(f"- Export-complete cases: `{export_complete_cases}/{total_cases}`")
    lines.append(f"- Average open critic findings per case: `{_fmt(avg_open_findings)}`")
    lines.append(f"- Average open review comments per case: `{_fmt(avg_open_comments)}`")
    lines.append(f"- Average acknowledged review comments per case: `{_fmt(avg_acknowledged_comments)}`")
    lines.append(f"- Average overdue review comments per case: `{_fmt(avg_overdue_comments)}`")
    lines.append(f"- Average stale open review comments per case: `{_fmt(avg_stale_comments)}`")
    lines.append(f"- Average reviewer workflow resolution rate: `{_fmt(avg_reviewer_workflow_resolution)}`")
    lines.append(f"- Average reviewer workflow acknowledgment rate: `{_fmt(avg_reviewer_workflow_ack)}`")
    lines.append(f"- Average critic finding resolution rate: `{_fmt(avg_critic_finding_resolution)}`")
    lines.append(f"- Average critic finding acknowledgment rate: `{_fmt(avg_critic_finding_ack)}`")
    lines.append(f"- Average finding ack queue per case: `{_fmt(avg_finding_ack_queue)}`")
    lines.append(f"- Average finding resolve queue per case: `{_fmt(avg_finding_resolve_queue)}`")
    lines.append(f"- Average comment ack queue per case: `{_fmt(avg_comment_ack_queue)}`")
    lines.append(f"- Average comment resolve queue per case: `{_fmt(avg_comment_resolve_queue)}`")
    lines.append(f"- Average comment reopen queue per case: `{_fmt(avg_comment_reopen_queue)}`")
    if portfolio_policy_status:
        lines.append(f"- Review workflow policy status: `{portfolio_policy_status}`")
    if portfolio_policy_go_no_go:
        lines.append(f"- Review workflow policy go/no-go: `{portfolio_policy_go_no_go}`")
    lines.append(f"- Review workflow policy breach count: `{total_policy_breaches}`")
    lines.append(f"- Review workflow policy attention count: `{total_policy_attention}`")
    if portfolio_policy_next_action:
        lines.append(f"- Review workflow next operational action: `{portfolio_policy_next_action}`")
    lines.append(f"- Average comment threads aged >7d per case: `{_fmt(avg_comment_age_gt_7d)}`")
    if stale_bucket_mix:
        lines.append(f"- Stale comment bucket mix: `{stale_bucket_mix}`")
        lines.append(f"- Top stale comment bucket: `{top_stale_bucket}`")
        donor_stale_bucket_totals: dict[str, dict[str, int]] = {}
        for case in cases:
            donor = case.donor_id or "unknown"
            donor_bucket_counts = donor_stale_bucket_totals.setdefault(
                donor, {"logic": 0, "grounding": 0, "measurement": 0, "compliance": 0, "general": 0}
            )
            donor_bucket_counts["logic"] += int(case.stale_comment_bucket_logic or 0)
            donor_bucket_counts["grounding"] += int(case.stale_comment_bucket_grounding or 0)
            donor_bucket_counts["measurement"] += int(case.stale_comment_bucket_measurement or 0)
            donor_bucket_counts["compliance"] += int(case.stale_comment_bucket_compliance or 0)
            donor_bucket_counts["general"] += int(case.stale_comment_bucket_general or 0)
        donor_mix = "; ".join(
            f"{donor}: {', '.join(f'{bucket}={count}' for bucket, count in bucket_counts.items() if count > 0)}"
            for donor, bucket_counts in donor_stale_bucket_totals.items()
            if any(bucket_counts.values())
        )
        if donor_mix:
            lines.append(f"- Stale thread donor/bucket mix: `{donor_mix}`")
    lines.append(f"- Average high-severity open findings per case: `{_fmt(avg_high_severity_findings)}`")
    lines.append(f"- Average fallback/strategy citations per case: `{_fmt(avg_fallback_citations)}`")
    lines.append(f"- Average low-confidence citations per case: `{_fmt(avg_low_confidence_citations)}`")
    lines.append(f"- Average architect retrieval hits per case: `{_fmt(avg_architect_hits)}`")
    lines.append(f"- Average architect grounded citation rate: `{_fmt(avg_architect_grounded_rate)}`")
    lines.append(f"- Average architect fallback citations per case: `{_fmt(avg_architect_fallback)}`")
    lines.append(f"- Average MEL retrieval hits per case: `{_fmt(avg_mel_hits)}`")
    lines.append(f"- Average MEL grounded citation rate: `{_fmt(avg_mel_grounded_rate)}`")
    lines.append(f"- Average MEL fallback citations per case: `{_fmt(avg_mel_fallback)}`")
    lines.append(f"- Average SMART field coverage: `{_fmt(avg_smart)}`")
    lines.append(f"- Average MoV coverage: `{_fmt(avg_mov)}`")
    lines.append(f"- Average owner coverage: `{_fmt(avg_owner)}`")
    if portfolio_next_bucket:
        lines.append(f"- Portfolio next review bucket: `{portfolio_next_bucket}`")
    if portfolio_next_action:
        lines.append(f"- Portfolio next recommended action: {portfolio_next_action}")
    lines.append(
        f"- Cases with complete LogFrame operational coverage: `{complete_logframe_cases}/{total_cases}` ({complete_logframe_rate:.0%})"
    )
    lines.append(f"- Cases with HITL enabled: `{hitl_cases}`")
    lines.append(
        f"- HITL-enabled cases with history: `{hitl_history_cases}/{hitl_cases}`"
        if hitl_cases
        else "- HITL-enabled cases with history: `0/0`"
    )
    lines.append(f"- Baseline-complete cases: `{baseline_cases}/{total_cases}` ({baseline_rate:.0%})")
    lines.append("")
    lines.append("## Gate Summary")
    lines.append("")
    lines.append("| Gate | Result | Actual | Expectation |")
    lines.append("|---|---|---|---|")
    for gate_name, status, actual, expectation in gate_rows:
        lines.append(f"| {gate_name} | `{status}` | {actual} | {expectation} |")
    lines.append("")
    lines.append("## Case Coverage")
    lines.append("")
    lines.append(
        "| Preset | Donor | Status | HITL | Quality | Critic | Open Findings | Open Comments | Overdue Comments | Fallback | SMART | MoV | Owner | Ops Ready | Baseline |"
    )
    lines.append("|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|")
    for case in cases:
        lines.append(
            f"| `{case.preset_key}` | `{case.donor_id}` | {case.status} | "
            f"{'yes' if case.hitl_enabled else 'no'} | {_fmt(case.quality_score)} | {_fmt(case.critic_score)} | "
            f"{_fmt(case.open_critic_findings)} | {_fmt(case.open_review_comments)} | {_fmt(case.overdue_review_comments)} | {_fmt(case.fallback_strategy_citations)} | "
            f"{_fmt(case.smart_field_coverage_rate)} | {_fmt(case.means_of_verification_coverage_rate)} | {_fmt(case.owner_coverage_rate)} | "
            f"{'yes' if case.complete_logframe_operational_coverage else 'no'} | "
            f"{'yes' if case.baseline_present else 'no'} |"
        )
    lines.append("")
    if fail_reasons:
        lines.append("## Blockers")
        for reason in fail_reasons:
            lines.append(f"- {reason}")
        lines.append("")
    if conditional_reasons:
        lines.append("## Conditions Before Buyer Decision")
        for reason in conditional_reasons:
            lines.append(f"- {reason}")
        lines.append("")
    lines.append("## Recommended Next Action")
    if verdict == "Not ready":
        lines.append("1. Fix failed gates and regenerate the pilot pack.")
        lines.append("2. Re-run `make pilot-scorecard-refresh` before sharing externally.")
    elif verdict == "Proceed with conditions":
        lines.append("1. Capture baseline metrics in `pilot-metrics.csv` for each case.")
        lines.append("2. Re-run `make pilot-scorecard` to refresh the decision memo.")
        lines.append("3. Use this scorecard with `buyer-brief.md` for the pilot go/no-go conversation.")
    else:
        lines.append("1. Use this scorecard and `buyer-brief.md` as the bounded pilot decision packet.")
        lines.append("2. Expand from demo presets to real customer proposal cases with baseline capture.")
    lines.append("")
    lines.append("## Notes")
    lines.append("- This scorecard evaluates demo/pilot evidence, not final donor submission quality.")
    lines.append("- Human compliance review remains mandatory before external submission.")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a go/no-go pilot scorecard from an existing GrantFlow pilot pack."
    )
    parser.add_argument("--pilot-pack-dir", default="build/pilot-pack")
    parser.add_argument("--output", default="")
    parser.add_argument("--min-avg-quality", type=float, default=7.0)
    parser.add_argument("--min-avg-critic", type=float, default=7.0)
    parser.add_argument("--min-terminal-done-rate", type=float, default=1.0)
    args = parser.parse_args()

    pilot_pack_dir = Path(str(args.pilot_pack_dir)).resolve()
    benchmark_path = pilot_pack_dir / "live-runs" / "benchmark-results.json"
    if not benchmark_path.exists():
        raise SystemExit(f"Missing pilot benchmark results: {benchmark_path}")

    benchmark_rows = _read_json(benchmark_path)
    if not isinstance(benchmark_rows, list) or not benchmark_rows:
        raise SystemExit("pilot pack live-runs/benchmark-results.json must contain a non-empty list")

    metrics_rows = _load_metrics_rows(pilot_pack_dir / "pilot-metrics.csv")
    cases = _load_case_scorecards(pilot_pack_dir, benchmark_rows, metrics_rows)
    portfolio_next_bucket = _first_nonempty_metric(metrics_rows, "next_review_bucket")
    portfolio_next_action = _first_nonempty_metric(metrics_rows, "next_recommended_action")
    output_path = (
        Path(str(args.output)).resolve() if str(args.output).strip() else pilot_pack_dir / "pilot-scorecard.md"
    )
    output_path.write_text(
        _build_scorecard(
            cases,
            pilot_pack_name=pilot_pack_dir.name,
            min_avg_quality=args.min_avg_quality,
            min_avg_critic=args.min_avg_critic,
            min_terminal_done_rate=args.min_terminal_done_rate,
            portfolio_next_bucket=portfolio_next_bucket,
            portfolio_next_action=portfolio_next_action,
        ),
        encoding="utf-8",
    )
    print(f"pilot scorecard saved to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
