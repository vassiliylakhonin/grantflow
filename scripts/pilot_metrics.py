#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from grantflow.api.public_views import _comment_triage_summary_payload, _critic_triage_summary_payload

STALE_BUCKET_KEYS = ("logic", "grounding", "measurement", "compliance", "general")


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


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


def _bucket_map(summary: dict[str, Any] | None) -> dict[str, int]:
    raw = summary.get("stale_comment_bucket_counts") if isinstance(summary, dict) else {}
    if not isinstance(raw, dict):
        return {}
    return {token: int(raw.get(token) or 0) for token in STALE_BUCKET_KEYS if int(raw.get(token) or 0) > 0}


def _bucket_mix_text(bucket_counts: dict[str, float | int]) -> str:
    parts = [f"{bucket}={int(count)}" for bucket, count in bucket_counts.items() if int(count) > 0]
    return ", ".join(parts) if parts else "-"


def _build_case_row(case_dir: Path, benchmark_row: dict[str, Any]) -> dict[str, Any]:
    metrics_path = case_dir / "metrics.json"
    quality_path = case_dir / "quality.json"
    critic_path = case_dir / "critic.json"
    export_payload_path = case_dir / "export-payload.json"
    metrics = _read_json(metrics_path) if metrics_path.exists() else {}
    quality = _read_json(quality_path) if quality_path.exists() else {}
    critic = _read_json(critic_path) if critic_path.exists() else {}
    export_payload = _read_json(export_payload_path) if export_payload_path.exists() else {}
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
    mov_rate = _safe_float(mel.get("means_of_verification_coverage_rate"))
    owner_rate = _safe_float(mel.get("owner_coverage_rate"))
    smart_rate = _safe_float(mel.get("smart_field_coverage_rate"))
    stale_bucket_counts = _bucket_map(comment_triage if isinstance(comment_triage, dict) else {})

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
        "open_critic_findings": readiness.get("open_critic_findings"),
        "high_severity_open_findings": readiness.get("high_severity_open_findings"),
        "resolved_critic_findings": readiness.get("resolved_critic_findings"),
        "acknowledged_critic_findings": readiness.get("acknowledged_critic_findings"),
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
        "baseline_time_to_first_draft_seconds": "",
        "baseline_time_to_terminal_seconds": "",
        "baseline_review_loops": "",
        "baseline_notes": "",
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
        "open_critic_findings",
        "high_severity_open_findings",
        "resolved_critic_findings",
        "acknowledged_critic_findings",
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
        "baseline_notes",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _build_markdown(rows: list[dict[str, Any]], *, pilot_pack_name: str) -> str:
    avg_quality = _avg([_safe_float(row.get("quality_score")) for row in rows])
    avg_critic = _avg([_safe_float(row.get("critic_score")) for row in rows])
    avg_first_draft = _avg([_safe_float(row.get("time_to_first_draft_seconds")) for row in rows])
    avg_terminal = _avg([_safe_float(row.get("time_to_terminal_seconds")) for row in rows])
    avg_pending_hitl = _avg([_safe_float(row.get("time_in_pending_hitl_seconds")) for row in rows])
    avg_citations = _avg([_safe_int(row.get("citation_count")) for row in rows])
    avg_open_findings = _avg([_safe_int(row.get("open_critic_findings")) for row in rows])
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
    avg_comment_age_d3_7 = _avg([_safe_int(row.get("comment_age_d3_7")) for row in rows])
    avg_comment_age_gt_7d = _avg([_safe_int(row.get("comment_age_gt_7d")) for row in rows])
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
    lines.append(f"- Average open critic findings per case: `{_fmt(avg_open_findings)}`")
    lines.append(f"- Average open review comments per case: `{_fmt(avg_open_comments)}`")
    lines.append(f"- Average resolved review comments per case: `{_fmt(avg_resolved_comments)}`")
    lines.append(f"- Average acknowledged review comments per case: `{_fmt(avg_ack_comments)}`")
    lines.append(f"- Average overdue review comments per case: `{_fmt(avg_overdue_comments)}`")
    lines.append(f"- Average stale open review comments per case: `{_fmt(avg_stale_comments)}`")
    lines.append(f"- Average review comment resolution rate: `{_fmt(avg_comment_resolution_rate)}`")
    lines.append(f"- Average review comment acknowledgment rate: `{_fmt(avg_comment_ack_rate)}`")
    lines.append(f"- Average reviewer workflow resolution rate: `{_fmt(avg_reviewer_workflow_resolution_rate)}`")
    lines.append(f"- Average reviewer workflow acknowledgment rate: `{_fmt(avg_reviewer_workflow_ack_rate)}`")
    lines.append(f"- Average comment threads aged 3-7d per case: `{_fmt(avg_comment_age_d3_7)}`")
    lines.append(f"- Average comment threads aged >7d per case: `{_fmt(avg_comment_age_gt_7d)}`")
    if any(stale_bucket_totals.values()):
        lines.append(f"- Stale comment bucket mix: `{_bucket_mix_text(stale_bucket_totals)}`")
        lines.append(f"- Top stale comment bucket: `{top_stale_bucket}`")
    lines.append(f"- Average fallback/strategy citations per case: `{_fmt(avg_fallback_citations)}`")
    lines.append(f"- Average low-confidence citations per case: `{_fmt(avg_low_confidence)}`")
    lines.append(f"- Average SMART field coverage: `{_fmt(avg_smart_coverage)}`")
    lines.append(f"- Average means-of-verification coverage: `{_fmt(avg_mov_coverage)}`")
    lines.append(f"- Average owner coverage: `{_fmt(avg_owner_coverage)}`")
    lines.append(f"- Cases with complete LogFrame operational coverage: `{complete_logframe_cases}/{len(rows)}`")
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
    lines.append("## Baseline Comparison Template")
    lines.append("- Use `pilot-metrics.csv` to fill baseline values before stakeholder review.")
    lines.append(
        "- Recommended baseline fields: `baseline_time_to_first_draft_seconds`, `baseline_time_to_terminal_seconds`, `baseline_review_loops`."
    )
    lines.append("- Compare those manually captured baseline numbers against pilot values in this pack.")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build pilot metrics tables from an existing GrantFlow pilot pack.")
    parser.add_argument("--pilot-pack-dir", default="build/pilot-pack")
    parser.add_argument("--csv-out", default="")
    parser.add_argument("--md-out", default="")
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

    csv_out = Path(str(args.csv_out)).resolve() if str(args.csv_out).strip() else pilot_pack_dir / "pilot-metrics.csv"
    md_out = Path(str(args.md_out)).resolve() if str(args.md_out).strip() else pilot_pack_dir / "pilot-metrics.md"

    _write_csv(csv_out, rows)
    md_out.write_text(_build_markdown(rows, pilot_pack_name=pilot_pack_dir.name), encoding="utf-8")
    print(f"pilot metrics saved to {csv_out} and {md_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
