#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from grantflow.api.public_views import (
    _comment_triage_summary_payload,
    _critic_triage_summary_payload,
    _review_action_queue_summary_payload,
    _review_workflow_policy_summary_payload,
)


ROOT_FILES = (
    "buyer-brief.md",
    "pilot-scorecard.md",
    "pilot-metrics.md",
    "pilot-portfolio-summary.json",
    "pilot-portfolio-summary.csv",
    "pilot-evaluation-checklist.md",
    "buyer-one-pager.md",
    "README.md",
)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _copy_if_exists(src: Path, dst: Path) -> None:
    if src.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def _slugify(value: str) -> str:
    token = "".join(ch if ch.isalnum() else "-" for ch in value.strip().lower())
    while "--" in token:
        token = token.replace("--", "-")
    return token.strip("-") or "bundle"


def _safe_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _format_num(value: float | int | None) -> str:
    if value is None:
        return "-"
    if isinstance(value, int):
        return str(value)
    if float(value).is_integer():
        return str(int(value))
    return f"{value:.2f}"


def _bucket_mix_text(bucket_counts: dict[str, int]) -> str:
    parts = [f"{bucket}={int(count)}" for bucket, count in bucket_counts.items() if int(count) > 0]
    return ", ".join(parts) if parts else "-"


def _donor_bucket_mix_text(donor_bucket_counts: dict[str, dict[str, int]]) -> str:
    parts: list[str] = []
    for donor, bucket_counts in donor_bucket_counts.items():
        mix = _bucket_mix_text(bucket_counts)
        if mix != "-":
            parts.append(f"{donor}: {mix}")
    return "; ".join(parts) if parts else "-"


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


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _top_reviewer_items(
    critic_payload: dict[str, Any],
    *,
    limit: int = 2,
) -> tuple[list[str], list[str]]:
    priority_titles: list[str] = []
    priority_actions: list[str] = []
    fallback_titles: list[str] = []
    fallback_actions: list[str] = []
    for item in critic_payload.get("fatal_flaws") or []:
        if not isinstance(item, dict):
            continue
        title = str(item.get("review_title") or item.get("message") or "").strip()
        action = str(item.get("reviewer_next_step") or item.get("recommended_action") or "").strip()
        if title and title not in fallback_titles:
            fallback_titles.append(title)
        if action and action not in fallback_actions:
            fallback_actions.append(action)
        if str(item.get("triage_priority") or "").strip().lower() not in {"urgent", "high"}:
            continue
        if title and title not in priority_titles:
            priority_titles.append(title)
        if action and action not in priority_actions:
            priority_actions.append(action)
    return (
        priority_titles[:limit] or fallback_titles[:limit],
        priority_actions[:limit] or fallback_actions[:limit],
    )


def _extract_markdown_bullets(text: str, heading: str) -> list[str]:
    lines = text.splitlines()
    bullets: list[str] = []
    capture = False
    for line in lines:
        if line.strip() == heading:
            capture = True
            continue
        if capture and line.startswith("## "):
            break
        if capture and line.startswith("- "):
            bullets.append(line[2:].strip())
    return bullets


def _first_nonempty(rows: list[dict[str, str]], key: str) -> str:
    for row in rows:
        value = str(row.get(key) or "").strip()
        if value:
            return value
    return ""


def _resolve_case_dir(
    rows: list[dict[str, Any]],
    *,
    preset_key: str,
    case_dir: str,
) -> str:
    if case_dir:
        return case_dir
    if preset_key:
        for row in rows:
            if str(row.get("preset_key") or "").strip() == preset_key:
                resolved = str(row.get("case_dir") or "").strip()
                if resolved:
                    return resolved
        raise SystemExit(f"Preset key not found in benchmark results: {preset_key}")
    if not rows:
        raise SystemExit("benchmark-results.json must contain at least one case row")
    resolved = str(rows[0].get("case_dir") or "").strip()
    if not resolved:
        raise SystemExit("First benchmark row has no case_dir")
    return resolved


def _build_summary(
    *,
    executive_pack_name: str,
    pilot_pack_name: str,
    case_dir: str,
    selected_row: dict[str, Any],
    total_cases: int,
    done_cases: int,
    featured_review_readiness: dict[str, Any],
    featured_triage_summary: dict[str, Any],
    featured_critic_payload: dict[str, Any],
    featured_mel_summary: dict[str, Any],
    featured_architect_grounded_rate: float | None,
    featured_architect_fallback_count: int | None,
    featured_architect_signal_mix: str,
    featured_top_architect_signal: str,
    review_ready_cases: str,
    portfolio_open_findings_avg: float | None,
    portfolio_open_comments_avg: float | None,
    portfolio_ack_comments_avg: float | None,
    portfolio_overdue_comments_avg: float | None,
    portfolio_stale_comments_avg: float | None,
    portfolio_comment_resolution_rate_avg: float | None,
    portfolio_comment_acknowledgment_rate_avg: float | None,
    portfolio_critic_finding_resolution_rate_avg: float | None,
    portfolio_critic_finding_ack_rate_avg: float | None,
    portfolio_architect_hits_avg: float | None,
    portfolio_architect_grounded_rate_avg: float | None,
    portfolio_architect_fallback_avg: float | None,
    portfolio_architect_signal_mix: str,
    portfolio_top_architect_signal: str,
    portfolio_fallback_avg: float | None,
    portfolio_low_confidence_avg: float | None,
    portfolio_smart_avg: float | None,
    portfolio_mov_avg: float | None,
    portfolio_owner_avg: float | None,
    portfolio_reviewer_workflow_resolution_rate_avg: float | None,
    portfolio_reviewer_workflow_ack_rate_avg: float | None,
    portfolio_finding_ack_queue_avg: float | None,
    portfolio_finding_resolve_queue_avg: float | None,
    portfolio_comment_ack_queue_avg: float | None,
    portfolio_comment_resolve_queue_avg: float | None,
    portfolio_comment_reopen_queue_avg: float | None,
    portfolio_comment_age_d3_7_avg: float | None,
    portfolio_comment_age_gt_7d_avg: float | None,
    portfolio_stale_bucket_mix: str,
    portfolio_top_stale_bucket: str,
    portfolio_donor_stale_bucket_mix: str,
    portfolio_policy_status: str,
    portfolio_policy_go_no_go: str,
    portfolio_policy_next_operational_action: str,
    portfolio_next_bucket: str,
    portfolio_next_action: str,
    conditional_reasons: list[str],
) -> str:
    lines: list[str] = []
    lines.append("# GrantFlow Executive Pack")
    lines.append("")
    lines.append(f"Generated at: {datetime.now(timezone.utc).isoformat()}")
    lines.append(f"- Executive pack: `{executive_pack_name}`")
    lines.append(f"- Source pilot pack: `{pilot_pack_name}`")
    lines.append("")
    lines.append("## Purpose")
    lines.append(
        "This folder is the shortest buyer-facing bundle for a bounded pilot conversation. "
        "It combines the executive brief, go/no-go scorecard, pilot metrics, and one representative case pack."
    )
    lines.append("")
    lines.append("## Snapshot")
    lines.append(f"- Total pilot cases: `{total_cases}`")
    lines.append(f"- Terminal done cases: `{done_cases}/{total_cases}`")
    lines.append(f"- Featured case dir: `{case_dir}`")
    lines.append(f"- Featured donor: `{selected_row.get('donor_id')}`")
    lines.append(f"- Featured preset: `{selected_row.get('preset_key')}`")
    lines.append(f"- Featured job id: `{selected_row.get('job_id')}`")
    lines.append("")
    lines.append("## Portfolio Readiness Snapshot")
    lines.append(f"- Cases with complete LogFrame operational coverage: `{review_ready_cases}`")
    lines.append(f"- Average open critic findings per case: `{_format_num(portfolio_open_findings_avg)}`")
    lines.append(f"- Average open review comments per case: `{_format_num(portfolio_open_comments_avg)}`")
    lines.append(f"- Average acknowledged review comments per case: `{_format_num(portfolio_ack_comments_avg)}`")
    lines.append(f"- Average overdue review comments per case: `{_format_num(portfolio_overdue_comments_avg)}`")
    lines.append(f"- Average stale open review comments per case: `{_format_num(portfolio_stale_comments_avg)}`")
    lines.append(f"- Average review comment resolution rate: `{_format_num(portfolio_comment_resolution_rate_avg)}`")
    lines.append(
        f"- Average review comment acknowledgment rate: `{_format_num(portfolio_comment_acknowledgment_rate_avg)}`"
    )
    lines.append(f"- Average fallback/strategy citations per case: `{_format_num(portfolio_fallback_avg)}`")
    lines.append(f"- Average low-confidence citations per case: `{_format_num(portfolio_low_confidence_avg)}`")
    lines.append(f"- Average SMART coverage: `{_format_num(portfolio_smart_avg)}`")
    lines.append(f"- Average MoV coverage: `{_format_num(portfolio_mov_avg)}`")
    lines.append(f"- Average owner coverage: `{_format_num(portfolio_owner_avg)}`")
    lines.append(
        f"- Average reviewer workflow resolution rate: `{_format_num(portfolio_reviewer_workflow_resolution_rate_avg)}`"
    )
    lines.append(
        f"- Average reviewer workflow acknowledgment rate: `{_format_num(portfolio_reviewer_workflow_ack_rate_avg)}`"
    )
    lines.append(
        f"- Average critic finding resolution rate: `{_format_num(portfolio_critic_finding_resolution_rate_avg)}`"
    )
    lines.append(
        f"- Average critic finding acknowledgment rate: `{_format_num(portfolio_critic_finding_ack_rate_avg)}`"
    )
    lines.append(f"- Average architect retrieval hits per case: `{_format_num(portfolio_architect_hits_avg)}`")
    lines.append(f"- Average architect grounded citation rate: `{_format_num(portfolio_architect_grounded_rate_avg)}`")
    lines.append(f"- Average architect fallback citations per case: `{_format_num(portfolio_architect_fallback_avg)}`")
    if portfolio_architect_signal_mix != "-":
        lines.append(f"- Architect evidence signal mix: `{portfolio_architect_signal_mix}`")
    if portfolio_top_architect_signal:
        lines.append(f"- Top architect evidence signal: `{portfolio_top_architect_signal}`")
    lines.append(f"- Average finding ack queue per case: `{_format_num(portfolio_finding_ack_queue_avg)}`")
    lines.append(f"- Average finding resolve queue per case: `{_format_num(portfolio_finding_resolve_queue_avg)}`")
    lines.append(f"- Average comment ack queue per case: `{_format_num(portfolio_comment_ack_queue_avg)}`")
    lines.append(f"- Average comment resolve queue per case: `{_format_num(portfolio_comment_resolve_queue_avg)}`")
    lines.append(f"- Average comment reopen queue per case: `{_format_num(portfolio_comment_reopen_queue_avg)}`")
    lines.append(f"- Average comment threads aged 3-7d per case: `{_format_num(portfolio_comment_age_d3_7_avg)}`")
    lines.append(f"- Average comment threads aged >7d per case: `{_format_num(portfolio_comment_age_gt_7d_avg)}`")
    if portfolio_policy_status:
        lines.append(f"- Review workflow policy status: `{portfolio_policy_status}`")
    if portfolio_policy_go_no_go:
        lines.append(f"- Review workflow policy go/no-go: `{portfolio_policy_go_no_go}`")
    if portfolio_policy_next_operational_action:
        lines.append(f"- Review workflow next operational action: `{portfolio_policy_next_operational_action}`")
    if portfolio_stale_bucket_mix != "-":
        lines.append(f"- Stale comment bucket mix: `{portfolio_stale_bucket_mix}`")
    if portfolio_top_stale_bucket:
        lines.append(f"- Top stale comment bucket: `{portfolio_top_stale_bucket}`")
    if portfolio_donor_stale_bucket_mix != "-":
        lines.append(f"- Stale thread donor/bucket mix: `{portfolio_donor_stale_bucket_mix}`")
    if portfolio_next_bucket:
        lines.append(f"- Portfolio next review bucket: `{portfolio_next_bucket}`")
    if portfolio_next_action:
        lines.append(f"- Portfolio next recommended action: {portfolio_next_action}")
    lines.append("")
    lines.append("## Readiness Snapshot")
    lines.append(
        f"- Open critic findings (featured case): `{featured_review_readiness.get('open_critic_findings', '-')}`"
    )
    lines.append(
        f"- Open review comments (featured case): `{featured_review_readiness.get('open_review_comments', '-')}`"
    )
    lines.append(
        f"- Resolved review comments (featured case): `{featured_review_readiness.get('resolved_review_comments', '-')}`"
    )
    lines.append(
        f"- Acknowledged review comments (featured case): `{featured_review_readiness.get('acknowledged_review_comments', '-')}`"
    )
    lines.append(
        f"- Overdue review comments (featured case): `{featured_review_readiness.get('overdue_review_comments', '-')}`"
    )
    lines.append(
        f"- Stale open review comments (featured case): `{featured_review_readiness.get('stale_open_review_comments', '-')}`"
    )
    lines.append(
        f"- Review comment resolution rate (featured case): `{_format_num(_safe_float(featured_review_readiness.get('review_comment_resolution_rate')))}`"
    )
    lines.append(
        f"- Review comment acknowledgment rate (featured case): `{_format_num(_safe_float(featured_review_readiness.get('review_comment_acknowledgment_rate')))}`"
    )
    lines.append(
        f"- High-severity open findings (featured case): `{featured_review_readiness.get('high_severity_open_findings', '-')}`"
    )
    lines.append(
        f"- Fallback/strategy citations (featured case): `{featured_review_readiness.get('fallback_strategy_citations', '-')}`"
    )
    lines.append(
        f"- Low-confidence citations (featured case): `{featured_review_readiness.get('low_confidence_citations', '-')}`"
    )
    lines.append(
        f"- Architect grounded citation rate (featured case): `{_format_num(featured_architect_grounded_rate)}`"
    )
    lines.append(f"- Architect fallback citations (featured case): `{_format_num(featured_architect_fallback_count)}`")
    if featured_architect_signal_mix != "-":
        lines.append(f"- Architect evidence signal mix (featured case): `{featured_architect_signal_mix}`")
    if featured_top_architect_signal:
        lines.append(f"- Top architect evidence signal (featured case): `{featured_top_architect_signal}`")
    lines.append(
        f"- SMART coverage (featured case): "
        f"`{_format_num(_safe_float(featured_mel_summary.get('smart_field_coverage_rate')))}"
        "`"
    )
    lines.append(
        f"- MoV coverage (featured case): "
        f"`{_format_num(_safe_float(featured_mel_summary.get('means_of_verification_coverage_rate')))}"
        "`"
    )
    lines.append(
        f"- Owner coverage (featured case): "
        f"`{_format_num(_safe_float(featured_mel_summary.get('owner_coverage_rate')))}"
        "`"
    )
    if featured_triage_summary:
        next_bucket = str(featured_triage_summary.get("next_review_bucket") or "").strip()
        next_action = str(featured_triage_summary.get("next_recommended_action") or "").strip()
        if next_bucket:
            lines.append(f"- Next review bucket (featured case): `{next_bucket}`")
        if next_action:
            lines.append(f"- Next recommended action (featured case): {next_action}")
    comment_triage = (
        featured_review_readiness.get("comment_triage_summary")
        if isinstance(featured_review_readiness.get("comment_triage_summary"), dict)
        else {}
    )
    if comment_triage:
        stale_bucket_counts = (
            comment_triage.get("stale_comment_bucket_counts")
            if isinstance(comment_triage.get("stale_comment_bucket_counts"), dict)
            else {}
        )
        next_comment_section = str(comment_triage.get("next_comment_section") or "").strip()
        next_comment_bucket = str(comment_triage.get("next_comment_bucket") or "").strip()
        next_comment_action = str(comment_triage.get("next_recommended_action") or "").strip()
        stale_bucket_mix = _bucket_mix_text({str(key): int(value or 0) for key, value in stale_bucket_counts.items()})
        if stale_bucket_mix != "-":
            lines.append(f"- Stale comment bucket mix (featured case): `{stale_bucket_mix}`")
        if next_comment_section:
            lines.append(f"- Next comment section (featured case): `{next_comment_section}`")
        if next_comment_bucket:
            lines.append(f"- Next comment bucket (featured case): `{next_comment_bucket}`")
        if next_comment_action:
            lines.append(f"- Next comment action (featured case): {next_comment_action}")
    action_queue = (
        featured_review_readiness.get("action_queue_summary")
        if isinstance(featured_review_readiness.get("action_queue_summary"), dict)
        else {}
    )
    workflow_policy = (
        featured_review_readiness.get("review_workflow_policy_summary")
        if isinstance(featured_review_readiness.get("review_workflow_policy_summary"), dict)
        else {}
    )
    if workflow_policy:
        if str(workflow_policy.get("status") or "").strip():
            lines.append(f"- Review workflow policy status (featured case): `{workflow_policy.get('status')}`")
        if str(workflow_policy.get("go_no_go_flag") or "").strip():
            lines.append(f"- Review workflow policy go/no-go (featured case): `{workflow_policy.get('go_no_go_flag')}`")
        if str(workflow_policy.get("next_operational_action") or "").strip():
            lines.append(
                f"- Review workflow next operational action (featured case): `{workflow_policy.get('next_operational_action')}`"
            )
    if action_queue:
        if str(action_queue.get("next_primary_action") or "").strip():
            lines.append(f"- Next primary review action (featured case): `{action_queue.get('next_primary_action')}`")
        lines.append(f"- Finding ack queue (featured case): `{action_queue.get('finding_ack_queue_count', '-')}`")
        lines.append(
            f"- Finding resolve queue (featured case): `{action_queue.get('finding_resolve_queue_count', '-')}`"
        )
        lines.append(f"- Comment ack queue (featured case): `{action_queue.get('comment_ack_queue_count', '-')}`")
        lines.append(
            f"- Comment resolve queue (featured case): `{action_queue.get('comment_resolve_queue_count', '-')}`"
        )
        lines.append(f"- Comment reopen queue (featured case): `{action_queue.get('comment_reopen_queue_count', '-')}`")
    priority_titles, priority_actions = _top_reviewer_items(featured_critic_payload)
    fallback_next_action = str(featured_triage_summary.get("next_recommended_action") or "").strip()
    if fallback_next_action and fallback_next_action not in priority_actions:
        priority_actions.insert(0, fallback_next_action)
    if priority_titles:
        lines.append(f"- Priority reviewer items (featured case): {', '.join(priority_titles)}")
    if priority_actions:
        for index, action in enumerate(priority_actions[:2], start=1):
            lines.append(f"- Top reviewer action {index} (featured case): {action}")
    lines.append("")
    if conditional_reasons:
        lines.append("## Current Conditions")
        for reason in conditional_reasons:
            lines.append(f"- {reason}")
        lines.append("")
    lines.append("## Open In Order")
    lines.append("1. `buyer-brief.md`")
    lines.append("2. `pilot-scorecard.md`")
    lines.append("3. `pilot-metrics.md`")
    lines.append(f"4. `case-study/{_slugify(case_dir)}/README.md`")
    lines.append("")
    lines.append("## Notes")
    lines.append("- This is a review and pilot evaluation bundle, not a final donor submission package.")
    lines.append("- The included case pack is representative, not exhaustive.")
    lines.append("- Human compliance review remains mandatory.")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Assemble a short buyer-facing executive pack from an existing GrantFlow pilot pack."
    )
    parser.add_argument("--pilot-pack-dir", default="build/pilot-pack")
    parser.add_argument("--case-study-dir", default="build/case-study-pack")
    parser.add_argument("--output-dir", default="build/executive-pack")
    parser.add_argument("--preset-key", default="")
    parser.add_argument("--case-dir", default="")
    args = parser.parse_args()

    pilot_pack_dir = Path(str(args.pilot_pack_dir)).resolve()
    case_study_dir = Path(str(args.case_study_dir)).resolve()
    output_dir = Path(str(args.output_dir)).resolve()

    benchmark_path = pilot_pack_dir / "live-runs" / "benchmark-results.json"
    if not benchmark_path.exists():
        raise SystemExit(f"Missing pilot benchmark results: {benchmark_path}")
    rows = _read_json(benchmark_path)
    if not isinstance(rows, list) or not rows:
        raise SystemExit("pilot pack live-runs/benchmark-results.json must contain a non-empty list")

    resolved_case_dir = _resolve_case_dir(
        rows,
        preset_key=str(args.preset_key).strip(),
        case_dir=str(args.case_dir).strip(),
    )
    selected_row = next(
        (row for row in rows if str(row.get("case_dir") or "").strip() == resolved_case_dir),
        None,
    )
    if selected_row is None:
        raise SystemExit(f"Selected case not found in benchmark rows: {resolved_case_dir}")

    source_case_pack_dir = case_study_dir / _slugify(resolved_case_dir)
    if not source_case_pack_dir.exists():
        raise SystemExit(f"Missing case-study pack directory: {source_case_pack_dir}. Run make case-study-pack first.")

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for file_name in ROOT_FILES:
        _copy_if_exists(pilot_pack_dir / file_name, output_dir / file_name)

    bundled_case_dir = output_dir / "case-study" / _slugify(resolved_case_dir)
    shutil.copytree(source_case_pack_dir, bundled_case_dir)

    done_cases = sum(1 for row in rows if str(row.get("status") or "").strip().lower() == "done")
    quality_payload = _read_json(pilot_pack_dir / "live-runs" / resolved_case_dir / "quality.json")
    if not isinstance(quality_payload, dict):
        quality_payload = {}
    featured_review_readiness = quality_payload.get("review_readiness_summary")
    if not isinstance(featured_review_readiness, dict):
        featured_review_readiness = {}
    featured_review_readiness = {
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
        **featured_review_readiness,
    }
    featured_triage_summary = quality_payload.get("triage_summary")
    if not isinstance(featured_triage_summary, dict):
        featured_triage_summary = {}
    featured_mel_summary = quality_payload.get("mel")
    if not isinstance(featured_mel_summary, dict):
        featured_mel_summary = {}
    critic_payload = _read_json(pilot_pack_dir / "live-runs" / resolved_case_dir / "critic.json")
    if not isinstance(critic_payload, dict):
        critic_payload = {}
    export_payload = _read_json(pilot_pack_dir / "live-runs" / resolved_case_dir / "export-payload.json")
    if not isinstance(export_payload, dict):
        export_payload = {}
    if not featured_triage_summary:
        triage_from_critic = critic_payload.get("triage_summary")
        featured_triage_summary = triage_from_critic if isinstance(triage_from_critic, dict) else {}
    if not featured_triage_summary:
        raw_findings = critic_payload.get("fatal_flaws")
        findings = [row for row in raw_findings if isinstance(row, dict)] if isinstance(raw_findings, list) else []
        featured_triage_summary = (
            _critic_triage_summary_payload(findings, donor_id=str(selected_row.get("donor_id") or "").strip())
            if findings
            else {}
        )
    if not isinstance(featured_review_readiness.get("comment_triage_summary"), dict):
        payload_root = export_payload.get("payload") if isinstance(export_payload.get("payload"), dict) else {}
        review_comments = (
            [row for row in payload_root.get("review_comments") or [] if isinstance(row, dict)]
            if isinstance(payload_root, dict)
            else []
        )
        raw_findings = critic_payload.get("fatal_flaws")
        findings = [row for row in raw_findings if isinstance(row, dict)] if isinstance(raw_findings, list) else []
        if review_comments:
            comment_triage = _comment_triage_summary_payload(
                review_comments=review_comments,
                critic_findings=findings,
                donor_id=str(selected_row.get("donor_id") or "").strip(),
            )
            action_queue_summary = _review_action_queue_summary_payload(
                critic_findings=findings,
                comment_triage_summary=comment_triage,
            )
            featured_review_readiness = {
                **featured_review_readiness,
                "open_review_comments": comment_triage.get("open_comment_count"),
                "resolved_review_comments": comment_triage.get("resolved_comment_count"),
                "acknowledged_review_comments": comment_triage.get("acknowledged_comment_count"),
                "pending_review_comments": comment_triage.get("pending_comment_count"),
                "overdue_review_comments": comment_triage.get("overdue_comment_count"),
                "stale_open_review_comments": comment_triage.get("stale_open_comment_count"),
                "linked_review_comments": comment_triage.get("linked_comment_count"),
                "orphan_linked_review_comments": comment_triage.get("orphan_linked_comment_count"),
                "review_comment_resolution_rate": featured_review_readiness.get("review_comment_resolution_rate"),
                "review_comment_acknowledgment_rate": featured_review_readiness.get(
                    "review_comment_acknowledgment_rate"
                ),
                "comment_triage_summary": comment_triage,
                "action_queue_summary": action_queue_summary,
                "review_workflow_policy_summary": _review_workflow_policy_summary_payload(
                    reviewer_workflow_summary={},
                    action_queue_summary=action_queue_summary,
                    comment_triage_summary=comment_triage,
                ),
            }
    if not isinstance(featured_review_readiness.get("action_queue_summary"), dict):
        raw_findings = critic_payload.get("fatal_flaws")
        findings = [row for row in raw_findings if isinstance(row, dict)] if isinstance(raw_findings, list) else []
        comment_triage = (
            featured_review_readiness.get("comment_triage_summary")
            if isinstance(featured_review_readiness.get("comment_triage_summary"), dict)
            else {}
        )
        featured_review_readiness = {
            **featured_review_readiness,
            "action_queue_summary": _review_action_queue_summary_payload(
                critic_findings=findings,
                comment_triage_summary=comment_triage if isinstance(comment_triage, dict) else {},
            ),
        }
    if not isinstance(featured_review_readiness.get("review_workflow_policy_summary"), dict):
        featured_review_readiness = {
            **featured_review_readiness,
            "review_workflow_policy_summary": _review_workflow_policy_summary_payload(
                reviewer_workflow_summary=(
                    featured_review_readiness.get("reviewer_workflow_summary")
                    if isinstance(featured_review_readiness.get("reviewer_workflow_summary"), dict)
                    else {}
                ),
                action_queue_summary=(
                    featured_review_readiness.get("action_queue_summary")
                    if isinstance(featured_review_readiness.get("action_queue_summary"), dict)
                    else {}
                ),
                comment_triage_summary=(
                    featured_review_readiness.get("comment_triage_summary")
                    if isinstance(featured_review_readiness.get("comment_triage_summary"), dict)
                    else {}
                ),
            ),
        }
    review_ready_cases_count = 0
    for row in rows:
        case_dir = str(row.get("case_dir") or "").strip()
        quality_path = pilot_pack_dir / "live-runs" / case_dir / "quality.json"
        if not quality_path.exists():
            continue
        payload = _read_json(quality_path)
        if not isinstance(payload, dict):
            continue
        mel = payload.get("mel")
        if not isinstance(mel, dict):
            continue
        smart = _safe_float(mel.get("smart_field_coverage_rate"))
        mov = _safe_float(mel.get("means_of_verification_coverage_rate"))
        owner = _safe_float(mel.get("owner_coverage_rate"))
        if smart == 1.0 and mov == 1.0 and owner == 1.0:
            review_ready_cases_count += 1
    metrics_rows = _read_csv_rows(pilot_pack_dir / "pilot-metrics.csv")
    portfolio_open_findings_avg = _avg([_safe_int(row.get("open_critic_findings")) for row in metrics_rows])
    portfolio_open_comments_avg = _avg([_safe_int(row.get("open_review_comments")) for row in metrics_rows])
    portfolio_ack_comments_avg = _avg([_safe_int(row.get("acknowledged_review_comments")) for row in metrics_rows])
    portfolio_overdue_comments_avg = _avg([_safe_int(row.get("overdue_review_comments")) for row in metrics_rows])
    portfolio_stale_comments_avg = _avg([_safe_int(row.get("stale_open_review_comments")) for row in metrics_rows])
    portfolio_comment_resolution_rate_avg = _avg(
        [_safe_float(row.get("review_comment_resolution_rate")) for row in metrics_rows]
    )
    portfolio_comment_acknowledgment_rate_avg = _avg(
        [_safe_float(row.get("review_comment_acknowledgment_rate")) for row in metrics_rows]
    )
    portfolio_critic_finding_resolution_rate_avg = _avg(
        [_safe_float(row.get("critic_finding_resolution_rate")) for row in metrics_rows]
    )
    portfolio_critic_finding_ack_rate_avg = _avg(
        [_safe_float(row.get("critic_finding_acknowledgment_rate")) for row in metrics_rows]
    )
    portfolio_architect_hits_avg = _avg(
        [_safe_float(row.get("architect_retrieval_hits_count")) for row in metrics_rows]
    )
    portfolio_architect_grounded_rate_avg = _avg(
        [_safe_float(row.get("architect_retrieval_grounded_citation_rate")) for row in metrics_rows]
    )
    portfolio_architect_fallback_avg = _avg(
        [_safe_float(row.get("architect_fallback_namespace_citation_count")) for row in metrics_rows]
    )
    architect_signal_totals: dict[str, int] = {}
    for row in metrics_rows:
        raw_mix = str(row.get("architect_evidence_signal_mix") or "").strip()
        if not raw_mix or raw_mix == "-":
            continue
        for token in raw_mix.split(","):
            part = token.strip()
            if "=" not in part:
                continue
            key, value = part.split("=", 1)
            signal = key.strip()
            count = int(_safe_int(value.strip()) or 0)
            if signal and count > 0:
                architect_signal_totals[signal] = architect_signal_totals.get(signal, 0) + count
    portfolio_architect_signal_mix = _bucket_mix_text(architect_signal_totals)
    portfolio_top_architect_signal = (
        max(architect_signal_totals.items(), key=lambda item: item[1])[0] if architect_signal_totals else ""
    )
    portfolio_fallback_avg = _avg([_safe_int(row.get("fallback_strategy_citations")) for row in metrics_rows])
    portfolio_low_confidence_avg = _avg([_safe_int(row.get("low_confidence_citations")) for row in metrics_rows])
    portfolio_smart_avg = _avg([_safe_float(row.get("smart_field_coverage_rate")) for row in metrics_rows])
    portfolio_mov_avg = _avg([_safe_float(row.get("means_of_verification_coverage_rate")) for row in metrics_rows])
    portfolio_owner_avg = _avg([_safe_float(row.get("owner_coverage_rate")) for row in metrics_rows])
    portfolio_reviewer_workflow_resolution_rate_avg = _avg(
        [_safe_float(row.get("reviewer_workflow_resolution_rate")) for row in metrics_rows]
    )
    portfolio_reviewer_workflow_ack_rate_avg = _avg(
        [_safe_float(row.get("reviewer_workflow_acknowledgment_rate")) for row in metrics_rows]
    )
    portfolio_finding_ack_queue_avg = _avg([_safe_float(row.get("finding_ack_queue_count")) for row in metrics_rows])
    portfolio_finding_resolve_queue_avg = _avg(
        [_safe_float(row.get("finding_resolve_queue_count")) for row in metrics_rows]
    )
    portfolio_comment_ack_queue_avg = _avg([_safe_float(row.get("comment_ack_queue_count")) for row in metrics_rows])
    portfolio_comment_resolve_queue_avg = _avg(
        [_safe_float(row.get("comment_resolve_queue_count")) for row in metrics_rows]
    )
    portfolio_comment_reopen_queue_avg = _avg(
        [_safe_float(row.get("comment_reopen_queue_count")) for row in metrics_rows]
    )
    portfolio_comment_age_d3_7_avg = _avg([_safe_float(row.get("comment_age_d3_7")) for row in metrics_rows])
    portfolio_comment_age_gt_7d_avg = _avg([_safe_float(row.get("comment_age_gt_7d")) for row in metrics_rows])
    portfolio_stale_bucket_totals = {
        "logic": sum(int(_safe_int(row.get("stale_comment_bucket_logic")) or 0) for row in metrics_rows),
        "grounding": sum(int(_safe_int(row.get("stale_comment_bucket_grounding")) or 0) for row in metrics_rows),
        "measurement": sum(int(_safe_int(row.get("stale_comment_bucket_measurement")) or 0) for row in metrics_rows),
        "compliance": sum(int(_safe_int(row.get("stale_comment_bucket_compliance")) or 0) for row in metrics_rows),
        "general": sum(int(_safe_int(row.get("stale_comment_bucket_general")) or 0) for row in metrics_rows),
    }
    portfolio_donor_stale_bucket_totals: dict[str, dict[str, int]] = {}
    for row in metrics_rows:
        donor = str(row.get("donor_id") or "").strip() or "unknown"
        donor_bucket_counts = portfolio_donor_stale_bucket_totals.setdefault(
            donor, {"logic": 0, "grounding": 0, "measurement": 0, "compliance": 0, "general": 0}
        )
        donor_bucket_counts["logic"] += int(_safe_int(row.get("stale_comment_bucket_logic")) or 0)
        donor_bucket_counts["grounding"] += int(_safe_int(row.get("stale_comment_bucket_grounding")) or 0)
        donor_bucket_counts["measurement"] += int(_safe_int(row.get("stale_comment_bucket_measurement")) or 0)
        donor_bucket_counts["compliance"] += int(_safe_int(row.get("stale_comment_bucket_compliance")) or 0)
        donor_bucket_counts["general"] += int(_safe_int(row.get("stale_comment_bucket_general")) or 0)
    portfolio_stale_bucket_mix = _bucket_mix_text(portfolio_stale_bucket_totals)
    portfolio_donor_stale_bucket_mix = _donor_bucket_mix_text(portfolio_donor_stale_bucket_totals)
    portfolio_top_stale_bucket = (
        max(portfolio_stale_bucket_totals.items(), key=lambda item: item[1])[0]
        if any(portfolio_stale_bucket_totals.values())
        else ""
    )
    portfolio_policy_status = _first_nonempty(metrics_rows, "review_workflow_policy_status")
    portfolio_policy_go_no_go = _first_nonempty(metrics_rows, "review_workflow_policy_go_no_go_flag")
    portfolio_policy_next_operational_action = _first_nonempty(metrics_rows, "review_workflow_next_operational_action")
    portfolio_next_bucket = _first_nonempty(metrics_rows, "next_review_bucket")
    portfolio_next_action = _first_nonempty(metrics_rows, "next_recommended_action")
    featured_architect_grounded_rate = _safe_float(
        quality_payload.get("citations", {}).get("architect_retrieval_grounded_citation_rate")
        if isinstance(quality_payload.get("citations"), dict)
        else None
    )
    featured_architect_fallback_count = _safe_int(
        quality_payload.get("citations", {}).get("architect_fallback_namespace_citation_count")
        if isinstance(quality_payload.get("citations"), dict)
        else None
    )
    featured_architect_signal_summary = (
        quality_payload.get("citations", {}).get("architect_signal_summary")
        if isinstance(quality_payload.get("citations"), dict)
        else {}
    )
    featured_architect_counts = (
        featured_architect_signal_summary.get("evidence_signal_counts")
        if isinstance(featured_architect_signal_summary, dict)
        and isinstance(featured_architect_signal_summary.get("evidence_signal_counts"), dict)
        else {}
    )
    featured_architect_signal_mix = _bucket_mix_text(
        {str(key): int(value or 0) for key, value in featured_architect_counts.items()}
    )
    featured_top_architect_signal = (
        max(featured_architect_counts.items(), key=lambda item: int(item[1] or 0))[0]
        if featured_architect_counts
        else ""
    )
    scorecard_text = (pilot_pack_dir / "pilot-scorecard.md").read_text(encoding="utf-8")
    conditional_reasons = _extract_markdown_bullets(scorecard_text, "## Conditions Before Buyer Decision")
    (output_dir / "README.md").write_text(
        _build_summary(
            executive_pack_name=output_dir.name,
            pilot_pack_name=pilot_pack_dir.name,
            case_dir=resolved_case_dir,
            selected_row=selected_row,
            total_cases=len(rows),
            done_cases=done_cases,
            featured_review_readiness=featured_review_readiness,
            featured_triage_summary=featured_triage_summary,
            featured_critic_payload=critic_payload,
            featured_mel_summary=featured_mel_summary,
            featured_architect_grounded_rate=featured_architect_grounded_rate,
            featured_architect_fallback_count=featured_architect_fallback_count,
            featured_architect_signal_mix=featured_architect_signal_mix,
            featured_top_architect_signal=featured_top_architect_signal,
            review_ready_cases=f"{review_ready_cases_count}/{len(rows)}",
            portfolio_open_findings_avg=portfolio_open_findings_avg,
            portfolio_open_comments_avg=portfolio_open_comments_avg,
            portfolio_ack_comments_avg=portfolio_ack_comments_avg,
            portfolio_overdue_comments_avg=portfolio_overdue_comments_avg,
            portfolio_stale_comments_avg=portfolio_stale_comments_avg,
            portfolio_comment_resolution_rate_avg=portfolio_comment_resolution_rate_avg,
            portfolio_comment_acknowledgment_rate_avg=portfolio_comment_acknowledgment_rate_avg,
            portfolio_critic_finding_resolution_rate_avg=portfolio_critic_finding_resolution_rate_avg,
            portfolio_critic_finding_ack_rate_avg=portfolio_critic_finding_ack_rate_avg,
            portfolio_architect_hits_avg=portfolio_architect_hits_avg,
            portfolio_architect_grounded_rate_avg=portfolio_architect_grounded_rate_avg,
            portfolio_architect_fallback_avg=portfolio_architect_fallback_avg,
            portfolio_architect_signal_mix=portfolio_architect_signal_mix,
            portfolio_top_architect_signal=portfolio_top_architect_signal,
            portfolio_fallback_avg=portfolio_fallback_avg,
            portfolio_low_confidence_avg=portfolio_low_confidence_avg,
            portfolio_smart_avg=portfolio_smart_avg,
            portfolio_mov_avg=portfolio_mov_avg,
            portfolio_owner_avg=portfolio_owner_avg,
            portfolio_reviewer_workflow_resolution_rate_avg=portfolio_reviewer_workflow_resolution_rate_avg,
            portfolio_reviewer_workflow_ack_rate_avg=portfolio_reviewer_workflow_ack_rate_avg,
            portfolio_finding_ack_queue_avg=portfolio_finding_ack_queue_avg,
            portfolio_finding_resolve_queue_avg=portfolio_finding_resolve_queue_avg,
            portfolio_comment_ack_queue_avg=portfolio_comment_ack_queue_avg,
            portfolio_comment_resolve_queue_avg=portfolio_comment_resolve_queue_avg,
            portfolio_comment_reopen_queue_avg=portfolio_comment_reopen_queue_avg,
            portfolio_comment_age_d3_7_avg=portfolio_comment_age_d3_7_avg,
            portfolio_comment_age_gt_7d_avg=portfolio_comment_age_gt_7d_avg,
            portfolio_stale_bucket_mix=portfolio_stale_bucket_mix,
            portfolio_top_stale_bucket=portfolio_top_stale_bucket,
            portfolio_donor_stale_bucket_mix=portfolio_donor_stale_bucket_mix,
            portfolio_policy_status=portfolio_policy_status,
            portfolio_policy_go_no_go=portfolio_policy_go_no_go,
            portfolio_policy_next_operational_action=portfolio_policy_next_operational_action,
            portfolio_next_bucket=portfolio_next_bucket,
            portfolio_next_action=portfolio_next_action,
            conditional_reasons=conditional_reasons,
        ),
        encoding="utf-8",
    )
    print(f"executive pack saved to {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
