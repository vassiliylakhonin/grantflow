#!/usr/bin/env python3
from __future__ import annotations

import argparse
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
from toc_snapshot import build_toc_snapshot


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
    clean = [float(v) for v in values if v is not None]
    if not clean:
        return None
    return sum(clean) / len(clean)


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


def _top_blocking_thresholds(conditions: list[str], *, limit: int = 3) -> list[str]:
    priority_tokens = (
        "reviewer workflow resolution rate",
        "reviewer workflow acknowledgment rate",
        "comment threads aged >7d",
        "review workflow sla policy",
        "architect grounding",
        "mel grounding",
        "fallback/strategy citations",
        "finding ack queue",
    )
    ranked: list[str] = []
    seen: set[str] = set()
    for token in priority_tokens:
        for condition in conditions:
            normalized = condition.strip()
            if not normalized or normalized in seen:
                continue
            if token in normalized.lower():
                ranked.append(normalized)
                seen.add(normalized)
                if len(ranked) >= limit:
                    return ranked
    for condition in conditions:
        normalized = condition.strip()
        if normalized and normalized not in seen:
            ranked.append(normalized)
            seen.add(normalized)
            if len(ranked) >= limit:
                break
    return ranked


def _load_case_quality(pilot_pack_dir: Path, case_dir: str) -> dict[str, Any]:
    if not case_dir:
        return {}
    path = pilot_pack_dir / "live-runs" / case_dir / "quality.json"
    if not path.exists():
        return {}
    payload = _read_json(path)
    return payload if isinstance(payload, dict) else {}


def _load_case_critic(pilot_pack_dir: Path, case_dir: str) -> dict[str, Any]:
    if not case_dir:
        return {}
    path = pilot_pack_dir / "live-runs" / case_dir / "critic.json"
    if not path.exists():
        return {}
    payload = _read_json(path)
    return payload if isinstance(payload, dict) else {}


def _load_case_export_payload(pilot_pack_dir: Path, case_dir: str) -> dict[str, Any]:
    if not case_dir:
        return {}
    path = pilot_pack_dir / "live-runs" / case_dir / "export-payload.json"
    if not path.exists():
        return {}
    payload = _read_json(path)
    return payload if isinstance(payload, dict) else {}


def _load_case_status(pilot_pack_dir: Path, case_dir: str) -> dict[str, Any]:
    if not case_dir:
        return {}
    path = pilot_pack_dir / "live-runs" / case_dir / "status.json"
    if not path.exists():
        return {}
    payload = _read_json(path)
    return payload if isinstance(payload, dict) else {}


def _review_readiness_from_payloads(
    quality_payload: dict[str, Any],
    critic_payload: dict[str, Any],
    export_payload: dict[str, Any],
    status_payload: dict[str, Any],
    *,
    donor_id: str = "",
) -> dict[str, Any]:
    readiness = (
        quality_payload.get("review_readiness_summary")
        if isinstance(quality_payload.get("review_readiness_summary"), dict)
        else {}
    )
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
    raw_findings = critic_payload.get("fatal_flaws")
    findings = [row for row in raw_findings if isinstance(row, dict)] if isinstance(raw_findings, list) else []
    if isinstance(readiness.get("comment_triage_summary"), dict):
        enriched = {**comment_defaults, **readiness}
        if not isinstance(enriched.get("action_queue_summary"), dict):
            comment_triage = enriched.get("comment_triage_summary")
            enriched["action_queue_summary"] = _review_action_queue_summary_payload(
                critic_findings=findings,
                comment_triage_summary=comment_triage if isinstance(comment_triage, dict) else {},
            )
        if not isinstance(enriched.get("reviewer_workflow_summary"), dict):
            comment_triage = enriched.get("comment_triage_summary")
            enriched["reviewer_workflow_summary"] = _reviewer_workflow_summary_payload(
                critic_findings=findings,
                comment_triage_summary=comment_triage if isinstance(comment_triage, dict) else {},
            )
        if not isinstance(enriched.get("review_workflow_policy_summary"), dict):
            enriched["review_workflow_policy_summary"] = _review_workflow_policy_summary_payload(
                reviewer_workflow_summary=(
                    enriched.get("reviewer_workflow_summary")
                    if isinstance(enriched.get("reviewer_workflow_summary"), dict)
                    else {}
                ),
                action_queue_summary=(
                    enriched.get("action_queue_summary")
                    if isinstance(enriched.get("action_queue_summary"), dict)
                    else {}
                ),
                comment_triage_summary=(
                    enriched.get("comment_triage_summary")
                    if isinstance(enriched.get("comment_triage_summary"), dict)
                    else {}
                ),
            )
        if not isinstance(enriched.get("throughput_summary"), dict):
            raw_events = status_payload.get("job_events") if isinstance(status_payload.get("job_events"), list) else []
            timeline = [
                {"ts": item.get("ts"), "type": item.get("type"), "status": item.get("status")}
                for item in raw_events
                if isinstance(item, dict)
                and str(item.get("type") or "").strip()
                in {"critic_finding_status_changed", "review_comment_added", "review_comment_status_changed"}
            ]
            enriched["throughput_summary"] = _review_workflow_throughput_summary_payload(timeline=timeline)
        if not isinstance(enriched.get("queue_delta_summary"), dict):
            enriched["queue_delta_summary"] = _review_workflow_queue_delta_summary_payload(
                action_queue_summary=(
                    enriched.get("action_queue_summary")
                    if isinstance(enriched.get("action_queue_summary"), dict)
                    else {}
                ),
                throughput_summary=(
                    enriched.get("throughput_summary") if isinstance(enriched.get("throughput_summary"), dict) else {}
                ),
            )
        return enriched
    payload_root = export_payload.get("payload") if isinstance(export_payload.get("payload"), dict) else {}
    review_comments = (
        [row for row in payload_root.get("review_comments") or [] if isinstance(row, dict)]
        if isinstance(payload_root, dict)
        else []
    )
    if not review_comments:
        return {**comment_defaults, **readiness}
    comment_triage = _comment_triage_summary_payload(
        review_comments=review_comments,
        critic_findings=findings,
        donor_id=donor_id,
    )
    reviewer_workflow_summary = _reviewer_workflow_summary_payload(
        critic_findings=findings,
        comment_triage_summary=comment_triage,
    )
    action_queue_summary = _review_action_queue_summary_payload(
        critic_findings=findings,
        comment_triage_summary=comment_triage,
    )
    throughput_summary = _review_workflow_throughput_summary_payload(
        timeline=[
            {"ts": item.get("ts"), "type": item.get("type"), "status": item.get("status")}
            for item in (status_payload.get("job_events") if isinstance(status_payload.get("job_events"), list) else [])
            if isinstance(item, dict)
            and str(item.get("type") or "").strip()
            in {"critic_finding_status_changed", "review_comment_added", "review_comment_status_changed"}
        ]
    )
    return {
        **comment_defaults,
        **readiness,
        "open_review_comments": comment_triage.get("open_comment_count"),
        "resolved_review_comments": comment_triage.get("resolved_comment_count"),
        "acknowledged_review_comments": comment_triage.get("acknowledged_comment_count"),
        "pending_review_comments": comment_triage.get("pending_comment_count"),
        "overdue_review_comments": comment_triage.get("overdue_comment_count"),
        "stale_open_review_comments": comment_triage.get("stale_open_comment_count"),
        "linked_review_comments": comment_triage.get("linked_comment_count"),
        "orphan_linked_review_comments": comment_triage.get("orphan_linked_comment_count"),
        "review_comment_resolution_rate": readiness.get("review_comment_resolution_rate"),
        "review_comment_acknowledgment_rate": readiness.get("review_comment_acknowledgment_rate"),
        "comment_triage_summary": comment_triage,
        "reviewer_workflow_summary": reviewer_workflow_summary,
        "action_queue_summary": action_queue_summary,
        "throughput_summary": throughput_summary,
        "queue_delta_summary": _review_workflow_queue_delta_summary_payload(
            action_queue_summary=action_queue_summary,
            throughput_summary=throughput_summary,
        ),
        "review_workflow_policy_summary": _review_workflow_policy_summary_payload(
            reviewer_workflow_summary=reviewer_workflow_summary,
            action_queue_summary=action_queue_summary,
            comment_triage_summary=comment_triage,
        ),
    }


def _triage_summary_from_payloads(
    quality_payload: dict[str, Any],
    critic_payload: dict[str, Any],
    *,
    donor_id: str = "",
) -> dict[str, Any]:
    triage = quality_payload.get("triage_summary") if isinstance(quality_payload.get("triage_summary"), dict) else {}
    if isinstance(triage, dict) and triage:
        return triage
    triage = critic_payload.get("triage_summary") if isinstance(critic_payload.get("triage_summary"), dict) else {}
    if isinstance(triage, dict) and triage:
        return triage
    raw_findings = critic_payload.get("fatal_flaws")
    findings = [row for row in raw_findings if isinstance(row, dict)] if isinstance(raw_findings, list) else []
    return _critic_triage_summary_payload(findings, donor_id=donor_id) if findings else {}


def _top_reviewer_actions_from_critic(critic_payload: dict[str, Any], *, donor_id: str = "") -> list[str]:
    raw_findings = critic_payload.get("fatal_flaws")
    findings = [row for row in raw_findings if isinstance(row, dict)] if isinstance(raw_findings, list) else []
    if not findings:
        return []
    triage = _critic_triage_summary_payload(findings, donor_id=donor_id)
    raw_actions = triage.get("top_reviewer_actions")
    if not isinstance(raw_actions, list):
        return []
    return [str(value or "").strip() for value in raw_actions if str(value or "").strip()]


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


def _next_ops_sequence(
    *,
    queue_next_primary_action: str | None,
    review_policy_next_operational_action: str | None,
    triage_next_action: str | None,
    current_conditions: list[str],
    limit: int = 3,
) -> list[str]:
    normalized_map = {
        "ack_finding": "Acknowledge the open critic findings queue and assign owners for the next review cycle.",
        "resolve_finding": "Resolve acknowledged critic findings after the revised draft is regenerated.",
        "ack_comment": "Acknowledge open reviewer comments and route them to the correct section owner.",
        "resolve_comment": "Resolve reviewer comments that already have enough revised evidence to close.",
        "reopen_comment": "Reopen comment threads that still block reviewer acceptance after re-checking the revised draft.",
        "triage_open_findings": "Triage the remaining open findings and bind them to the next reviewer action queue.",
        "resolve_overdue_comments": "Resolve overdue reviewer comments before the next buyer-facing review checkpoint.",
        "clear_stale_comment_threads": "Clear stale reviewer comment threads before external sharing or pilot sign-off.",
    }
    sequence: list[str] = []
    seen: set[str] = set()
    for candidate in (
        str(queue_next_primary_action or "").strip(),
        str(review_policy_next_operational_action or "").strip(),
        str(triage_next_action or "").strip(),
    ):
        if not candidate:
            continue
        text = normalized_map.get(candidate, candidate)
        if text not in seen:
            sequence.append(text)
            seen.add(text)
        if len(sequence) >= limit:
            return sequence
    for condition in current_conditions:
        lowered = condition.lower()
        if "baseline comparison" in lowered:
            text = "Capture baseline metrics for every case before the formal buyer go/no-go review."
        elif "comment threads aged >7d" in lowered or "stale reviewer comment" in lowered:
            text = "Reduce stale reviewer comment threads older than seven days before external sharing."
        elif "reviewer workflow resolution rate" in lowered:
            text = "Improve reviewer resolution throughput so open review items start closing inside the target SLA."
        elif "reviewer workflow acknowledgment rate" in lowered:
            text = "Improve reviewer acknowledgment throughput so new review items are triaged inside the target SLA."
        else:
            continue
        if text not in seen:
            sequence.append(text)
            seen.add(text)
        if len(sequence) >= limit:
            break
    return sequence


def _suggested_demo_console_actions(
    *,
    queue_next_primary_action: str | None,
    avg_finding_ack_queue: float | None,
    avg_comment_ack_queue: float | None,
    avg_comment_resolve_queue: float | None,
    avg_comment_reopen_queue: float | None,
    limit: int = 2,
) -> list[str]:
    actions: list[str] = []
    seen: set[str] = set()

    def add(text: str) -> None:
        if text not in seen and len(actions) < limit:
            actions.append(text)
            seen.add(text)

    primary = str(queue_next_primary_action or "").strip().lower()
    if primary == "ack_finding" or (avg_finding_ack_queue or 0) > 0:
        add(
            "`/demo -> Critic Findings -> Filter Finding Status=open -> Use Suggested Finding Action (ack_finding) -> Preview Acknowledge Findings -> Apply Acknowledge Findings`"
        )
    if primary == "ack_comment" or (avg_comment_ack_queue or 0) > 0:
        add(
            "`/demo -> Review Comments -> List Filter Status=open -> Use Suggested Comment Action (ack_comment) -> Preview Acknowledge Comments -> Apply Acknowledge Comments`"
        )
    if primary == "resolve_comment" or (avg_comment_resolve_queue or 0) > 0:
        add(
            "`/demo -> Review Comments -> List Filter Status=acknowledged -> Use Suggested Comment Action (resolve_comment) -> Preview Resolve Comments -> Apply Resolve Comments`"
        )
    if primary == "reopen_comment" or (avg_comment_reopen_queue or 0) > 0:
        add(
            "`/demo -> Review Comments -> List Filter Status=resolved -> Use Suggested Comment Action (reopen_comment) -> Preview Reopen Comments -> Apply Reopen Comments`"
        )
    return actions


def _build_brief(
    rows: list[dict[str, Any]],
    *,
    pilot_pack_name: str,
    include_productization_memo: bool,
    current_conditions: list[str],
    top_blocking_thresholds: list[str],
    triage_next_action: str | None,
    triage_next_bucket: str | None,
    triage_top_ids: list[str],
    triage_top_actions: list[str],
    queue_next_primary_action: str | None,
    avg_finding_ack_queue: float | None,
    avg_finding_resolve_queue: float | None,
    avg_comment_ack_queue: float | None,
    avg_comment_resolve_queue: float | None,
    avg_comment_reopen_queue: float | None,
    avg_critic_finding_resolution_rate: float | None,
    avg_critic_finding_ack_rate: float | None,
    avg_architect_hits: float | None,
    avg_architect_grounded_rate: float | None,
    avg_architect_fallback_count: float | None,
    architect_signal_mix: str,
    top_architect_signal: str | None,
    avg_mel_hits: float | None,
    avg_mel_grounded_rate: float | None,
    avg_mel_fallback_count: float | None,
    mel_signal_mix: str,
    top_mel_signal: str | None,
    review_policy_status: str | None,
    review_policy_go_no_go: str | None,
    review_policy_next_operational_action: str | None,
    representative_case_label: str,
    representative_toc_snapshot: list[str],
) -> str:
    done_count = sum(1 for row in rows if str(row.get("status") or "").strip().lower() == "done")
    hitl_count = sum(1 for row in rows if bool(row.get("hitl_enabled")))
    avg_quality = _avg([_safe_float(row.get("quality_score")) for row in rows])
    avg_critic = _avg([_safe_float(row.get("critic_score")) for row in rows])
    avg_citations = _avg([_safe_int(row.get("citation_count")) for row in rows])

    donors = sorted({str(row.get("donor_id") or "").strip() for row in rows if str(row.get("donor_id") or "").strip()})

    lines: list[str] = []
    lines.append("# GrantFlow Buyer Brief")
    lines.append("")
    lines.append(f"Generated at: {datetime.now(timezone.utc).isoformat()}")
    lines.append("")
    lines.append("## Executive Summary")
    lines.append(
        "GrantFlow is a proposal operations backend for institutional funding workflows. "
        "This brief summarizes a pilot-ready evidence bundle generated from live runs and export artifacts."
    )
    lines.append("")
    lines.append("## Current Evidence Snapshot")
    lines.append(f"- Pilot pack: `{pilot_pack_name}`")
    lines.append(f"- Cases reviewed: `{len(rows)}`")
    lines.append(f"- Terminal done cases: `{done_count}/{len(rows)}`")
    lines.append(f"- Donors represented: {', '.join(f'`{donor}`' for donor in donors) if donors else '-' }")
    lines.append(f"- Cases with HITL review path: `{hitl_count}`")
    lines.append(f"- Average quality score: `{_format_num(avg_quality)}`")
    lines.append(f"- Average critic score: `{_format_num(avg_critic)}`")
    lines.append(f"- Average citation count: `{_format_num(avg_citations)}`")
    lines.append(f"- Average architect retrieval hits per case: `{_format_num(avg_architect_hits)}`")
    lines.append(f"- Average architect grounded citation rate: `{_format_num(avg_architect_grounded_rate)}`")
    lines.append(f"- Average architect fallback citations per case: `{_format_num(avg_architect_fallback_count)}`")
    if architect_signal_mix and architect_signal_mix != "-":
        lines.append(f"- Architect evidence signal mix: `{architect_signal_mix}`")
    if top_architect_signal:
        lines.append(f"- Top architect evidence signal: `{top_architect_signal}`")
    lines.append(f"- Average MEL retrieval hits per case: `{_format_num(avg_mel_hits)}`")
    lines.append(f"- Average MEL grounded citation rate: `{_format_num(avg_mel_grounded_rate)}`")
    lines.append(f"- Average MEL fallback citations per case: `{_format_num(avg_mel_fallback_count)}`")
    if mel_signal_mix and mel_signal_mix != "-":
        lines.append(f"- MEL evidence signal mix: `{mel_signal_mix}`")
    if top_mel_signal:
        lines.append(f"- Top MEL evidence signal: `{top_mel_signal}`")
    if review_policy_status:
        lines.append(f"- Review workflow policy status: `{review_policy_status}`")
    if review_policy_go_no_go:
        lines.append(f"- Review workflow policy go/no-go: `{review_policy_go_no_go}`")
    if review_policy_next_operational_action:
        lines.append(f"- Review workflow next operational action: `{review_policy_next_operational_action}`")
    lines.append("")
    if triage_next_action or triage_next_bucket or triage_top_ids:
        lines.append("## Review Triage Snapshot")
        if queue_next_primary_action:
            lines.append(f"- Next primary review action: `{queue_next_primary_action}`")
        if triage_next_bucket:
            lines.append(f"- Next review bucket: `{triage_next_bucket}`")
        if triage_next_action:
            lines.append(f"- Next recommended action: {triage_next_action}")
        for index, action in enumerate(triage_top_actions[:2], start=1):
            lines.append(f"- Top reviewer action {index}: {action}")
        if triage_top_ids:
            lines.append(
                f"- Top priority finding ids: {', '.join(f'`{item}`' for item in triage_top_ids if str(item).strip())}"
            )
        lines.append("")
    next_ops_sequence = _next_ops_sequence(
        queue_next_primary_action=queue_next_primary_action,
        review_policy_next_operational_action=review_policy_next_operational_action,
        triage_next_action=triage_next_action,
        current_conditions=current_conditions,
    )
    if next_ops_sequence:
        lines.append("## Next Ops Sequence")
        for index, step in enumerate(next_ops_sequence, start=1):
            lines.append(f"{index}. {step}")
        lines.append("")
    suggested_actions = _suggested_demo_console_actions(
        queue_next_primary_action=queue_next_primary_action,
        avg_finding_ack_queue=avg_finding_ack_queue,
        avg_comment_ack_queue=avg_comment_ack_queue,
        avg_comment_resolve_queue=avg_comment_resolve_queue,
        avg_comment_reopen_queue=avg_comment_reopen_queue,
    )
    if suggested_actions:
        lines.append("## Suggested Demo Console Actions")
        for action in suggested_actions:
            lines.append(f"- {action}")
        lines.append("")
    if representative_toc_snapshot:
        lines.append("## Representative ToC Snapshot")
        lines.append(f"Source case: `{representative_case_label}`")
        for line in representative_toc_snapshot:
            lines.append(f"- {line}")
        lines.append("")
    lines.append("## What This Demonstrates")
    lines.append("- Structured draft generation through a controlled pipeline, not one-shot text output.")
    lines.append(
        "- Reviewable traces available per case: status, quality, critic findings, citations, versions, events."
    )
    lines.append("- Optional human checkpoint flow with approve/resume behavior.")
    lines.append("- Exportable review artifacts for downstream proposal workflow.")
    lines.append("")
    if current_conditions:
        if top_blocking_thresholds:
            lines.append("## Top Blocking Thresholds")
            for reason in top_blocking_thresholds:
                lines.append(f"- {reason}")
            lines.append("")
        lines.append("## Current Conditions")
        for reason in current_conditions:
            lines.append(f"- {reason}")
        lines.append("")
    lines.append("## Why This Matters To Proposal Teams")
    lines.append("- Reduces review chaos by keeping draft state and evidence in one workflow.")
    lines.append("- Improves evaluability of draft quality before formal compliance sign-off.")
    lines.append("- Creates reusable proposal operations infrastructure instead of ad-hoc drafting.")
    lines.append("")
    lines.append("## Recommended Pilot Scope")
    lines.append("- Start with `2-3` donors and `5-10` representative proposal cases.")
    lines.append("- Capture baseline cycle-time and review-loop metrics before pilot start.")
    lines.append("- Use evidence from `live-runs/` plus `pilot-evaluation-checklist.md` for go/no-go review.")
    lines.append("")
    lines.append("## Important Constraints")
    lines.append("- These materials are pilot artifacts, not final donor submissions.")
    lines.append("- Grounding quality remains corpus-dependent when retrieval is enabled.")
    lines.append("- Final compliance responsibility remains with human reviewers.")
    if include_productization_memo:
        lines.append(
            "- Productization and enterprise-readiness gaps are documented separately in `productization-gaps-memo.md`."
        )
    lines.append("")
    lines.append("## Suggested Next Conversation")
    lines.append("1. Choose target donors and real proposal cases for a bounded pilot.")
    lines.append("2. Define pilot success metrics and review owners.")
    lines.append("3. Run a pilot bundle and compare process outcomes against baseline.")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a short buyer-facing executive brief from a GrantFlow pilot pack."
    )
    parser.add_argument("--pilot-pack-dir", default="build/pilot-pack")
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    pilot_pack_dir = Path(str(args.pilot_pack_dir)).resolve()
    benchmark_path = pilot_pack_dir / "live-runs" / "benchmark-results.json"
    if not benchmark_path.exists():
        raise SystemExit(f"Missing pilot benchmark results: {benchmark_path}")

    rows = _read_json(benchmark_path)
    if not isinstance(rows, list) or not rows:
        raise SystemExit("pilot pack live-runs/benchmark-results.json must contain a non-empty list")

    quality_payloads = [_load_case_quality(pilot_pack_dir, str(row.get("case_dir") or "").strip()) for row in rows]
    critic_payloads = [_load_case_critic(pilot_pack_dir, str(row.get("case_dir") or "").strip()) for row in rows]
    export_payloads = [
        _load_case_export_payload(pilot_pack_dir, str(row.get("case_dir") or "").strip()) for row in rows
    ]
    status_payloads = [_load_case_status(pilot_pack_dir, str(row.get("case_dir") or "").strip()) for row in rows]
    readiness_summaries = [
        _review_readiness_from_payloads(
            quality_payload,
            critic_payload,
            export_payload,
            status_payload,
            donor_id=str(row.get("donor_id") or "").strip(),
        )
        for row, quality_payload, critic_payload, export_payload, status_payload in zip(
            rows, quality_payloads, critic_payloads, export_payloads, status_payloads, strict=False
        )
    ]
    triage_summaries = []
    for row, quality_payload, critic_payload in zip(rows, quality_payloads, critic_payloads, strict=False):
        triage = _triage_summary_from_payloads(
            quality_payload,
            critic_payload,
            donor_id=str(row.get("donor_id") or "").strip(),
        )
        if isinstance(triage, dict) and triage:
            triage_summaries.append(triage)
    mel_summaries = [payload.get("mel") for payload in quality_payloads if isinstance(payload.get("mel"), dict)]

    open_findings_avg = _avg(
        [_safe_int(item.get("open_critic_findings")) for item in readiness_summaries if isinstance(item, dict)]
    )
    open_comments_avg = _avg(
        [_safe_int(item.get("open_review_comments")) for item in readiness_summaries if isinstance(item, dict)]
    )
    resolved_comments_avg = _avg(
        [_safe_int(item.get("resolved_review_comments")) for item in readiness_summaries if isinstance(item, dict)]
    )
    acknowledged_comments_avg = _avg(
        [_safe_int(item.get("acknowledged_review_comments")) for item in readiness_summaries if isinstance(item, dict)]
    )
    overdue_comments_avg = _avg(
        [_safe_int(item.get("overdue_review_comments")) for item in readiness_summaries if isinstance(item, dict)]
    )
    stale_comments_avg = _avg(
        [_safe_int(item.get("stale_open_review_comments")) for item in readiness_summaries if isinstance(item, dict)]
    )
    resolution_rate_avg = _avg(
        [
            _safe_float(item.get("review_comment_resolution_rate"))
            for item in readiness_summaries
            if isinstance(item, dict)
        ]
    )
    acknowledgment_rate_avg = _avg(
        [
            _safe_float(item.get("review_comment_acknowledgment_rate"))
            for item in readiness_summaries
            if isinstance(item, dict)
        ]
    )
    workflow_resolution_rate_avg = _avg(
        [
            _safe_float(
                item.get("reviewer_workflow_summary", {}).get("resolution_rate")
                if isinstance(item.get("reviewer_workflow_summary"), dict)
                else None
            )
            for item in readiness_summaries
            if isinstance(item, dict)
        ]
    )
    workflow_acknowledgment_rate_avg = _avg(
        [
            _safe_float(
                item.get("reviewer_workflow_summary", {}).get("acknowledgment_rate")
                if isinstance(item.get("reviewer_workflow_summary"), dict)
                else None
            )
            for item in readiness_summaries
            if isinstance(item, dict)
        ]
    )
    avg_finding_ack_queue = _avg(
        [
            _safe_float(
                item.get("action_queue_summary", {}).get("finding_ack_queue_count")
                if isinstance(item.get("action_queue_summary"), dict)
                else None
            )
            for item in readiness_summaries
            if isinstance(item, dict)
        ]
    )
    avg_finding_resolve_queue = _avg(
        [
            _safe_float(
                item.get("action_queue_summary", {}).get("finding_resolve_queue_count")
                if isinstance(item.get("action_queue_summary"), dict)
                else None
            )
            for item in readiness_summaries
            if isinstance(item, dict)
        ]
    )
    avg_comment_ack_queue = _avg(
        [
            _safe_float(
                item.get("action_queue_summary", {}).get("comment_ack_queue_count")
                if isinstance(item.get("action_queue_summary"), dict)
                else None
            )
            for item in readiness_summaries
            if isinstance(item, dict)
        ]
    )
    avg_comment_resolve_queue = _avg(
        [
            _safe_float(
                item.get("action_queue_summary", {}).get("comment_resolve_queue_count")
                if isinstance(item.get("action_queue_summary"), dict)
                else None
            )
            for item in readiness_summaries
            if isinstance(item, dict)
        ]
    )
    avg_comment_reopen_queue = _avg(
        [
            _safe_float(
                item.get("action_queue_summary", {}).get("comment_reopen_queue_count")
                if isinstance(item.get("action_queue_summary"), dict)
                else None
            )
            for item in readiness_summaries
            if isinstance(item, dict)
        ]
    )
    avg_finding_ack_completed = _avg(
        [
            _safe_float(
                item.get("throughput_summary", {}).get("finding_ack_completed_count")
                if isinstance(item.get("throughput_summary"), dict)
                else None
            )
            for item in readiness_summaries
            if isinstance(item, dict)
        ]
    )
    avg_comment_resolve_completed = _avg(
        [
            _safe_float(
                item.get("throughput_summary", {}).get("comment_resolve_completed_count")
                if isinstance(item.get("throughput_summary"), dict)
                else None
            )
            for item in readiness_summaries
            if isinstance(item, dict)
        ]
    )
    dominant_completed_action = next(
        (
            str(item.get("throughput_summary", {}).get("dominant_completed_action") or "").strip()
            for item in readiness_summaries
            if isinstance(item, dict)
            and isinstance(item.get("throughput_summary"), dict)
            and str(item.get("throughput_summary", {}).get("dominant_completed_action") or "").strip()
        ),
        "",
    )
    avg_critic_finding_resolution_rate = _avg(
        [
            _safe_float(item.get("critic_finding_resolution_rate"))
            for item in readiness_summaries
            if isinstance(item, dict) and _safe_float(item.get("critic_finding_resolution_rate")) is not None
        ]
    )
    avg_critic_finding_ack_rate = _avg(
        [
            _safe_float(item.get("critic_finding_acknowledgment_rate"))
            for item in readiness_summaries
            if isinstance(item, dict) and _safe_float(item.get("critic_finding_acknowledgment_rate")) is not None
        ]
    )
    if avg_critic_finding_resolution_rate is None or avg_critic_finding_ack_rate is None:
        critic_resolution_values: list[float] = []
        critic_ack_values: list[float] = []
        for critic_payload in critic_payloads:
            if not isinstance(critic_payload, dict):
                continue
            raw_findings = critic_payload.get("fatal_flaws")
            findings = [row for row in raw_findings if isinstance(row, dict)] if isinstance(raw_findings, list) else []
            if not findings:
                continue
            resolved_count = sum(
                1 for item in findings if str(item.get("status") or "").strip().lower() in {"resolved", "closed"}
            )
            acknowledged_count = sum(
                1 for item in findings if str(item.get("status") or "").strip().lower() == "acknowledged"
            )
            critic_resolution_values.append(resolved_count / len(findings))
            critic_ack_values.append((resolved_count + acknowledged_count) / len(findings))
        if avg_critic_finding_resolution_rate is None:
            avg_critic_finding_resolution_rate = _avg(critic_resolution_values)
        if avg_critic_finding_ack_rate is None:
            avg_critic_finding_ack_rate = _avg(critic_ack_values)
    age_d3_7_avg = _avg(
        [
            _safe_int(
                item.get("comment_triage_summary", {}).get("aging_band_counts", {}).get("d3_7")
                if isinstance(item.get("comment_triage_summary"), dict)
                else None
            )
            for item in readiness_summaries
            if isinstance(item, dict)
        ]
    )
    age_gt_7d_avg = _avg(
        [
            _safe_int(
                item.get("comment_triage_summary", {}).get("aging_band_counts", {}).get("gt_7d")
                if isinstance(item.get("comment_triage_summary"), dict)
                else None
            )
            for item in readiness_summaries
            if isinstance(item, dict)
        ]
    )
    fallback_citations_avg = _avg(
        [_safe_int(item.get("fallback_strategy_citations")) for item in readiness_summaries if isinstance(item, dict)]
    )
    architect_hits_avg = _avg(
        [
            _safe_int(item.get("state", {}).get("architect_retrieval", {}).get("hits_count"))
            for item in status_payloads
            if isinstance(item, dict) and isinstance(item.get("state"), dict)
        ]
    )
    architect_grounded_rate_avg = _avg(
        [
            _safe_float(
                item.get("citations", {}).get("architect_retrieval_grounded_citation_rate")
                if isinstance(item.get("citations"), dict)
                else None
            )
            for item in quality_payloads
            if isinstance(item, dict)
        ]
    )
    architect_fallback_avg = _avg(
        [
            _safe_int(
                item.get("citations", {}).get("architect_fallback_namespace_citation_count")
                if isinstance(item.get("citations"), dict)
                else None
            )
            for item in quality_payloads
            if isinstance(item, dict)
        ]
    )
    architect_signal_totals: dict[str, int] = {}
    for payload in quality_payloads:
        if not isinstance(payload, dict):
            continue
        citations = payload.get("citations")
        if not isinstance(citations, dict):
            continue
        summary = citations.get("architect_signal_summary")
        if not isinstance(summary, dict):
            continue
        counts = summary.get("evidence_signal_counts")
        if not isinstance(counts, dict):
            continue
        for key, value in counts.items():
            token = str(key or "").strip()
            if token:
                architect_signal_totals[token] = architect_signal_totals.get(token, 0) + int(_safe_int(value) or 0)
    top_architect_signal = (
        max(architect_signal_totals.items(), key=lambda item: item[1])[0] if architect_signal_totals else ""
    )
    mel_hits_avg = _avg(
        [
            _safe_float(item.get("mel", {}).get("retrieval_hits_count") if isinstance(item.get("mel"), dict) else None)
            for item in quality_payloads
            if isinstance(item, dict)
        ]
    )
    mel_grounded_rate_avg = _avg(
        [
            _safe_float(
                item.get("citations", {}).get("mel_retrieval_grounded_citation_rate")
                if isinstance(item.get("citations"), dict)
                else None
            )
            for item in quality_payloads
            if isinstance(item, dict)
        ]
    )
    mel_fallback_avg = _avg(
        [
            _safe_int(
                item.get("citations", {}).get("mel_fallback_namespace_citation_count")
                if isinstance(item.get("citations"), dict)
                else None
            )
            for item in quality_payloads
            if isinstance(item, dict)
        ]
    )
    mel_signal_totals: dict[str, int] = {}
    for payload in quality_payloads:
        if not isinstance(payload, dict):
            continue
        citations = payload.get("citations")
        if not isinstance(citations, dict):
            continue
        if int(_safe_int(citations.get("mel_retrieval_grounded_citation_count")) or 0) > 0:
            mel_signal_totals["retrieved donor evidence"] = mel_signal_totals.get("retrieved donor evidence", 0) + 1
        elif int(_safe_int(citations.get("mel_strategy_reference_citation_count")) or 0) > 0:
            mel_signal_totals["strategy reference"] = mel_signal_totals.get("strategy reference", 0) + 1
    top_mel_signal = max(mel_signal_totals.items(), key=lambda item: item[1])[0] if mel_signal_totals else ""
    low_confidence_avg = _avg(
        [_safe_int(item.get("low_confidence_citations")) for item in readiness_summaries if isinstance(item, dict)]
    )
    mov_coverage_avg = _avg(
        [
            _safe_float(item.get("means_of_verification_coverage_rate"))
            for item in mel_summaries
            if isinstance(item, dict)
        ]
    )
    owner_coverage_avg = _avg(
        [_safe_float(item.get("owner_coverage_rate")) for item in mel_summaries if isinstance(item, dict)]
    )
    smart_coverage_avg = _avg(
        [_safe_float(item.get("smart_field_coverage_rate")) for item in mel_summaries if isinstance(item, dict)]
    )
    review_ready_cases = sum(
        1
        for item in mel_summaries
        if isinstance(item, dict)
        and _safe_float(item.get("means_of_verification_coverage_rate")) == 1.0
        and _safe_float(item.get("owner_coverage_rate")) == 1.0
        and _safe_float(item.get("smart_field_coverage_rate")) == 1.0
    )
    triage_next_action = next(
        (
            str(item.get("next_recommended_action") or "").strip()
            for item in triage_summaries
            if isinstance(item, dict) and str(item.get("next_recommended_action") or "").strip()
        ),
        "",
    )
    triage_next_bucket = next(
        (
            str(item.get("next_review_bucket") or "").strip()
            for item in triage_summaries
            if isinstance(item, dict) and str(item.get("next_review_bucket") or "").strip()
        ),
        "",
    )
    triage_top_ids: list[str] = []
    triage_top_actions: list[str] = []
    queue_next_primary_action = next(
        (
            str(item.get("action_queue_summary", {}).get("next_primary_action") or "").strip()
            for item in readiness_summaries
            if isinstance(item, dict)
            and isinstance(item.get("action_queue_summary"), dict)
            and str(item.get("action_queue_summary", {}).get("next_primary_action") or "").strip()
        ),
        "",
    )
    policy_rank = {"breach": 3, "attention": 2, "healthy": 1}
    review_policy_status = ""
    review_policy_go_no_go = ""
    review_policy_next_operational_action = ""
    for item in readiness_summaries:
        if not isinstance(item, dict):
            continue
        policy = item.get("review_workflow_policy_summary")
        if not isinstance(policy, dict):
            continue
        current_status = str(policy.get("status") or "").strip().lower()
        if current_status and policy_rank.get(current_status, 0) > policy_rank.get(review_policy_status, 0):
            review_policy_status = current_status
            review_policy_go_no_go = str(policy.get("go_no_go_flag") or "").strip().lower()
            review_policy_next_operational_action = str(policy.get("next_operational_action") or "").strip()
    for item in triage_summaries:
        if not isinstance(item, dict):
            continue
        raw_ids = item.get("top_priority_finding_ids")
        if not isinstance(raw_ids, list):
            continue
        for value in raw_ids:
            token = str(value or "").strip()
            if token and token not in triage_top_ids:
                triage_top_ids.append(token)
            if len(triage_top_ids) >= 3:
                break
        if len(triage_top_ids) >= 3:
            break
    for item in triage_summaries:
        if not isinstance(item, dict):
            continue
        raw_actions = item.get("top_reviewer_actions")
        if not isinstance(raw_actions, list):
            continue
        for value in raw_actions:
            token = str(value or "").strip()
            if token and token not in triage_top_actions:
                triage_top_actions.append(token)
            if len(triage_top_actions) >= 3:
                break
        if len(triage_top_actions) >= 3:
            break
    if not triage_top_actions:
        for row, critic_payload in zip(rows, critic_payloads, strict=False):
            for action in _top_reviewer_actions_from_critic(
                critic_payload,
                donor_id=str(row.get("donor_id") or "").strip(),
            ):
                if action and action not in triage_top_actions:
                    triage_top_actions.append(action)
                if len(triage_top_actions) >= 3:
                    break
            if len(triage_top_actions) >= 3:
                break
    if not triage_top_actions and triage_next_action:
        triage_top_actions.append(triage_next_action)
    comment_triage_summaries = [
        item.get("comment_triage_summary")
        for item in readiness_summaries
        if isinstance(item, dict) and isinstance(item.get("comment_triage_summary"), dict)
    ]
    next_comment_section = next(
        (
            str(item.get("next_comment_section") or "").strip()
            for item in comment_triage_summaries
            if isinstance(item, dict) and str(item.get("next_comment_section") or "").strip()
        ),
        "",
    )
    next_comment_bucket = next(
        (
            str(item.get("next_comment_bucket") or "").strip()
            for item in comment_triage_summaries
            if isinstance(item, dict) and str(item.get("next_comment_bucket") or "").strip()
        ),
        "",
    )
    next_comment_action = next(
        (
            str(item.get("next_recommended_action") or "").strip()
            for item in comment_triage_summaries
            if isinstance(item, dict) and str(item.get("next_recommended_action") or "").strip()
        ),
        "",
    )
    stale_bucket_totals = {"logic": 0, "grounding": 0, "measurement": 0, "compliance": 0, "general": 0}
    donor_stale_bucket_totals: dict[str, dict[str, int]] = {}
    for item in comment_triage_summaries:
        if not isinstance(item, dict):
            continue
        raw = item.get("stale_comment_bucket_counts")
        if not isinstance(raw, dict):
            continue
        for bucket in stale_bucket_totals:
            stale_bucket_totals[bucket] += int(raw.get(bucket) or 0)
    for row, item in zip(rows, comment_triage_summaries, strict=False):
        if not isinstance(item, dict):
            continue
        raw = item.get("stale_comment_bucket_counts")
        if not isinstance(raw, dict):
            continue
        donor = str(row.get("donor_id") or "").strip() or "unknown"
        donor_bucket_counts = donor_stale_bucket_totals.setdefault(
            donor, {"logic": 0, "grounding": 0, "measurement": 0, "compliance": 0, "general": 0}
        )
        for bucket in donor_bucket_counts:
            donor_bucket_counts[bucket] += int(raw.get(bucket) or 0)
    top_stale_bucket = (
        max(stale_bucket_totals.items(), key=lambda pair: pair[1])[0] if any(stale_bucket_totals.values()) else ""
    )

    output_path = Path(str(args.output)).resolve() if str(args.output).strip() else pilot_pack_dir / "buyer-brief.md"
    include_productization_memo = (pilot_pack_dir / "productization-gaps-memo.md").exists()
    scorecard_path = pilot_pack_dir / "pilot-scorecard.md"
    current_conditions = (
        _extract_markdown_bullets(scorecard_path.read_text(encoding="utf-8"), "## Conditions Before Buyer Decision")
        if scorecard_path.exists()
        else []
    )
    top_blocking_thresholds = _top_blocking_thresholds(current_conditions)
    representative_case_label = str(rows[0].get("case_dir") or "").strip() if rows else ""
    representative_toc_snapshot = build_toc_snapshot(export_payloads[0]) if export_payloads else []
    text = _build_brief(
        rows,
        pilot_pack_name=pilot_pack_dir.name,
        include_productization_memo=include_productization_memo,
        current_conditions=current_conditions,
        top_blocking_thresholds=top_blocking_thresholds,
        triage_next_action=(triage_next_action or None),
        triage_next_bucket=(triage_next_bucket or None),
        triage_top_ids=triage_top_ids,
        triage_top_actions=triage_top_actions,
        queue_next_primary_action=(queue_next_primary_action or None),
        avg_finding_ack_queue=avg_finding_ack_queue,
        avg_finding_resolve_queue=avg_finding_resolve_queue,
        avg_comment_ack_queue=avg_comment_ack_queue,
        avg_comment_resolve_queue=avg_comment_resolve_queue,
        avg_comment_reopen_queue=avg_comment_reopen_queue,
        avg_critic_finding_resolution_rate=avg_critic_finding_resolution_rate,
        avg_critic_finding_ack_rate=avg_critic_finding_ack_rate,
        avg_architect_hits=architect_hits_avg,
        avg_architect_grounded_rate=architect_grounded_rate_avg,
        avg_architect_fallback_count=architect_fallback_avg,
        architect_signal_mix=_bucket_mix_text(architect_signal_totals),
        top_architect_signal=(top_architect_signal or None),
        avg_mel_hits=mel_hits_avg,
        avg_mel_grounded_rate=mel_grounded_rate_avg,
        avg_mel_fallback_count=mel_fallback_avg,
        mel_signal_mix=_bucket_mix_text(mel_signal_totals),
        top_mel_signal=(top_mel_signal or None),
        review_policy_status=(review_policy_status or None),
        review_policy_go_no_go=(review_policy_go_no_go or None),
        review_policy_next_operational_action=(review_policy_next_operational_action or None),
        representative_case_label=representative_case_label,
        representative_toc_snapshot=representative_toc_snapshot,
    )
    insert_lines = [
        "## Review Readiness Snapshot",
        f"- Open critic findings per case: `{_format_num(open_findings_avg)}`",
        f"- Open review comments per case: `{_format_num(open_comments_avg)}`",
        f"- Resolved review comments per case: `{_format_num(resolved_comments_avg)}`",
        f"- Acknowledged review comments per case: `{_format_num(acknowledged_comments_avg)}`",
        f"- Overdue review comments per case: `{_format_num(overdue_comments_avg)}`",
        f"- Stale open review comments per case: `{_format_num(stale_comments_avg)}`",
        f"- Average review comment resolution rate: `{_format_num(resolution_rate_avg)}`",
        f"- Average review comment acknowledgment rate: `{_format_num(acknowledgment_rate_avg)}`",
        f"- Average reviewer workflow resolution rate: `{_format_num(workflow_resolution_rate_avg)}`",
        f"- Average reviewer workflow acknowledgment rate: `{_format_num(workflow_acknowledgment_rate_avg)}`",
        f"- Average critic finding resolution rate: `{_format_num(avg_critic_finding_resolution_rate)}`",
        f"- Average critic finding acknowledgment rate: `{_format_num(avg_critic_finding_ack_rate)}`",
        f"- Average finding ack queue per case: `{_format_num(avg_finding_ack_queue)}`",
        f"- Average finding resolve queue per case: `{_format_num(avg_finding_resolve_queue)}`",
        f"- Average comment ack queue per case: `{_format_num(avg_comment_ack_queue)}`",
        f"- Average comment resolve queue per case: `{_format_num(avg_comment_resolve_queue)}`",
        f"- Average comment reopen queue per case: `{_format_num(avg_comment_reopen_queue)}`",
        f"- Average finding acks completed per case: `{_format_num(avg_finding_ack_completed)}`",
        f"- Average comment resolves completed per case: `{_format_num(avg_comment_resolve_completed)}`",
        *(
            [f"- Dominant completed workflow action: `{dominant_completed_action}`"]
            if dominant_completed_action
            else []
        ),
        f"- Comment threads aged 3-7d per case: `{_format_num(age_d3_7_avg)}`",
        f"- Comment threads aged >7d per case: `{_format_num(age_gt_7d_avg)}`",
        *(
            [f"- Stale comment bucket mix: `{_bucket_mix_text(stale_bucket_totals)}`"]
            if any(stale_bucket_totals.values())
            else []
        ),
        *([f"- Top stale comment bucket: `{top_stale_bucket}`"] if top_stale_bucket else []),
        *(
            [f"- Stale thread donor/bucket mix: `{_donor_bucket_mix_text(donor_stale_bucket_totals)}`"]
            if any(stale_bucket_totals.values())
            else []
        ),
        f"- Fallback/strategy citations per case: `{_format_num(fallback_citations_avg)}`",
        f"- Low-confidence citations per case: `{_format_num(low_confidence_avg)}`",
        *([f"- Next comment section: `{next_comment_section}`"] if next_comment_section else []),
        *([f"- Next comment bucket: `{next_comment_bucket}`"] if next_comment_bucket else []),
        *([f"- Next comment action: {next_comment_action}"] if next_comment_action else []),
        "",
        "## LogFrame Readiness Snapshot",
        f"- Cases with complete SMART + MoV + owner coverage: `{review_ready_cases}/{len(rows)}`",
        f"- Average SMART field coverage: `{_format_num(smart_coverage_avg)}`",
        f"- Average means-of-verification coverage: `{_format_num(mov_coverage_avg)}`",
        f"- Average owner coverage: `{_format_num(owner_coverage_avg)}`",
        "",
    ]
    text = text.replace(
        "## What This Demonstrates\n",
        "\n".join(insert_lines) + "\n## What This Demonstrates\n",
        1,
    )
    output_path.write_text(text, encoding="utf-8")
    print(f"buyer brief saved to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
