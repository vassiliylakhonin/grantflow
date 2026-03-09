#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from grantflow.api.public_views import _comment_triage_summary_payload, _critic_triage_summary_payload


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


def _review_readiness_from_payloads(
    quality_payload: dict[str, Any],
    critic_payload: dict[str, Any],
    export_payload: dict[str, Any],
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
    if isinstance(readiness.get("comment_triage_summary"), dict):
        return {**comment_defaults, **readiness}
    payload_root = export_payload.get("payload") if isinstance(export_payload.get("payload"), dict) else {}
    review_comments = (
        [row for row in payload_root.get("review_comments") or [] if isinstance(row, dict)]
        if isinstance(payload_root, dict)
        else []
    )
    raw_findings = critic_payload.get("fatal_flaws")
    findings = [row for row in raw_findings if isinstance(row, dict)] if isinstance(raw_findings, list) else []
    if not review_comments:
        return {**comment_defaults, **readiness}
    comment_triage = _comment_triage_summary_payload(
        review_comments=review_comments,
        critic_findings=findings,
        donor_id=donor_id,
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


def _build_brief(
    rows: list[dict[str, Any]],
    *,
    pilot_pack_name: str,
    include_productization_memo: bool,
    current_conditions: list[str],
    triage_next_action: str | None,
    triage_next_bucket: str | None,
    triage_top_ids: list[str],
    triage_top_actions: list[str],
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
    lines.append("")
    if triage_next_action or triage_next_bucket or triage_top_ids:
        lines.append("## Review Triage Snapshot")
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
    lines.append("## What This Demonstrates")
    lines.append("- Structured draft generation through a controlled pipeline, not one-shot text output.")
    lines.append(
        "- Reviewable traces available per case: status, quality, critic findings, citations, versions, events."
    )
    lines.append("- Optional human checkpoint flow with approve/resume behavior.")
    lines.append("- Exportable review artifacts for downstream proposal workflow.")
    lines.append("")
    if current_conditions:
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
    readiness_summaries = [
        _review_readiness_from_payloads(
            quality_payload,
            critic_payload,
            export_payload,
            donor_id=str(row.get("donor_id") or "").strip(),
        )
        for row, quality_payload, critic_payload, export_payload in zip(
            rows, quality_payloads, critic_payloads, export_payloads, strict=False
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
    for item in comment_triage_summaries:
        if not isinstance(item, dict):
            continue
        raw = item.get("stale_comment_bucket_counts")
        if not isinstance(raw, dict):
            continue
        for bucket in stale_bucket_totals:
            stale_bucket_totals[bucket] += int(raw.get(bucket) or 0)
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
    text = _build_brief(
        rows,
        pilot_pack_name=pilot_pack_dir.name,
        include_productization_memo=include_productization_memo,
        current_conditions=current_conditions,
        triage_next_action=(triage_next_action or None),
        triage_next_bucket=(triage_next_bucket or None),
        triage_top_ids=triage_top_ids,
        triage_top_actions=triage_top_actions,
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
        f"- Comment threads aged 3-7d per case: `{_format_num(age_d3_7_avg)}`",
        f"- Comment threads aged >7d per case: `{_format_num(age_gt_7d_avg)}`",
        *(
            [f"- Stale comment bucket mix: `{_bucket_mix_text(stale_bucket_totals)}`"]
            if any(stale_bucket_totals.values())
            else []
        ),
        *([f"- Top stale comment bucket: `{top_stale_bucket}`"] if top_stale_bucket else []),
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
