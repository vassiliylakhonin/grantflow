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


def _resolve_featured_case(
    rows: list[dict[str, Any]],
    *,
    preset_key: str,
    case_dir: str,
) -> dict[str, Any]:
    if case_dir:
        for row in rows:
            if str(row.get("case_dir") or "").strip() == case_dir:
                return row
        raise SystemExit(f"Case dir not found in benchmark rows: {case_dir}")
    if preset_key:
        for row in rows:
            if str(row.get("preset_key") or "").strip() == preset_key:
                return row
        raise SystemExit(f"Preset key not found in benchmark rows: {preset_key}")
    if not rows:
        raise SystemExit("benchmark rows must not be empty")
    return rows[0]


def _safe_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


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


def _build_handout(
    *,
    pilot_pack_name: str,
    executive_pack_name: str,
    rows: list[dict[str, Any]],
    featured_row: dict[str, Any],
    quality_avg: float | None,
    critic_avg: float | None,
    verdict: str,
    readiness: str,
    baseline_complete_cases: str,
    featured_review_readiness: dict[str, Any],
    featured_triage_summary: dict[str, Any],
    featured_critic_payload: dict[str, Any],
    featured_mel_summary: dict[str, Any],
    review_ready_cases: str,
    current_conditions: list[str],
) -> str:
    done_cases = sum(1 for row in rows if str(row.get("status") or "").strip().lower() == "done")
    donors = sorted({str(row.get("donor_id") or "").strip() for row in rows if str(row.get("donor_id") or "").strip()})
    lines: list[str] = []
    lines.append("# GrantFlow Pilot Handout")
    lines.append("")
    lines.append(f"Generated at: {datetime.now(timezone.utc).isoformat()}")
    lines.append(f"- Source pilot pack: `{pilot_pack_name}`")
    lines.append(f"- Source executive pack: `{executive_pack_name}`")
    lines.append("")
    lines.append("## One-Line Summary")
    lines.append(
        "GrantFlow is proposal operations infrastructure for donor workflows: structured drafting, governed review, traceability, and export-ready artifacts."
    )
    lines.append("")
    lines.append("## Pilot Snapshot")
    lines.append(f"- Cases reviewed: `{len(rows)}`")
    lines.append(f"- Terminal done cases: `{done_cases}/{len(rows)}`")
    lines.append(f"- Donors represented: {', '.join(f'`{donor}`' for donor in donors) if donors else '-'}")
    lines.append(
        f"- Average quality score: `{quality_avg:.2f}`" if quality_avg is not None else "- Average quality score: `-`"
    )
    lines.append(
        f"- Average critic score: `{critic_avg:.2f}`" if critic_avg is not None else "- Average critic score: `-`"
    )
    lines.append(f"- Current scorecard verdict: `{verdict}`")
    lines.append(f"- Current readiness color: `{readiness}`")
    lines.append(f"- Baseline-complete cases: `{baseline_complete_cases}`")
    lines.append(f"- Cases with complete LogFrame operational coverage: `{review_ready_cases}`")
    lines.append("")
    lines.append("## Why This Matters")
    lines.append("- Faster path to a reviewable draft, not just generated text.")
    lines.append("- Lower review chaos through explicit workflow state and traceability.")
    lines.append("- Exportable artifacts for downstream proposal operations.")
    lines.append("")
    if current_conditions:
        lines.append("## Current Conditions")
        for reason in current_conditions:
            lines.append(f"- {reason}")
        lines.append("")
    lines.append("## Featured Case")
    lines.append(f"- Donor: `{featured_row.get('donor_id')}`")
    lines.append(f"- Preset: `{featured_row.get('preset_key')}`")
    lines.append(f"- Case dir: `{featured_row.get('case_dir')}`")
    lines.append(f"- Job ID: `{featured_row.get('job_id')}`")
    lines.append(f"- Status: `{featured_row.get('status')}`")
    lines.append(f"- HITL enabled: `{'true' if featured_row.get('hitl_enabled') else 'false'}`")
    if featured_review_readiness:
        lines.append(f"- Open critic findings: `{featured_review_readiness.get('open_critic_findings', '-')}`")
        lines.append(f"- Open review comments: `{featured_review_readiness.get('open_review_comments', '-')}`")
        lines.append(f"- Resolved review comments: `{featured_review_readiness.get('resolved_review_comments', '-')}`")
        lines.append(f"- Overdue review comments: `{featured_review_readiness.get('overdue_review_comments', '-')}`")
        lines.append(
            f"- Fallback/strategy citations: `{featured_review_readiness.get('fallback_strategy_citations', '-')}`"
        )
    if featured_triage_summary:
        if str(featured_triage_summary.get("next_review_bucket") or "").strip():
            lines.append(f"- Next review bucket: `{featured_triage_summary.get('next_review_bucket')}`")
        if str(featured_triage_summary.get("next_recommended_action") or "").strip():
            lines.append(f"- Next recommended action: {featured_triage_summary.get('next_recommended_action')}")
    comment_triage = (
        featured_review_readiness.get("comment_triage_summary")
        if isinstance(featured_review_readiness.get("comment_triage_summary"), dict)
        else {}
    )
    if comment_triage:
        if str(comment_triage.get("next_comment_section") or "").strip():
            lines.append(f"- Next comment section: `{comment_triage.get('next_comment_section')}`")
        if str(comment_triage.get("next_recommended_action") or "").strip():
            lines.append(f"- Next comment action: {comment_triage.get('next_recommended_action')}")
    top_finding_titles, top_reviewer_actions = _top_reviewer_items(featured_critic_payload)
    fallback_next_action = str(featured_triage_summary.get("next_recommended_action") or "").strip()
    if fallback_next_action and fallback_next_action not in top_reviewer_actions:
        top_reviewer_actions.insert(0, fallback_next_action)
    if top_finding_titles:
        lines.append(f"- Priority reviewer items: {', '.join(top_finding_titles)}")
    for index, action in enumerate(top_reviewer_actions[:2], start=1):
        lines.append(f"- Top reviewer action {index}: {action}")
    if featured_mel_summary:
        mov = featured_mel_summary.get("means_of_verification_coverage_rate")
        owner = featured_mel_summary.get("owner_coverage_rate")
        smart = featured_mel_summary.get("smart_field_coverage_rate")
        lines.append(f"- SMART coverage: `{smart:.2f}`" if isinstance(smart, (int, float)) else "- SMART coverage: `-`")
        lines.append(f"- MoV coverage: `{mov:.2f}`" if isinstance(mov, (int, float)) else "- MoV coverage: `-`")
        lines.append(f"- Owner coverage: `{owner:.2f}`" if isinstance(owner, (int, float)) else "- Owner coverage: `-`")
    lines.append("")
    lines.append("## What To Open Next")
    lines.append("1. `buyer-brief.md` for the short commercial summary.")
    lines.append("2. `pilot-scorecard.md` for the current go/no-go decision.")
    lines.append("3. `pilot-metrics.md` for process metrics.")
    lines.append(
        f"4. `case-study/{featured_row.get('case_dir')}/README.md` inside the executive pack for the representative case."
    )
    lines.append("")
    lines.append("## Current Constraint")
    lines.append(
        "- This pilot evidence is strong on workflow traces and exports, but baseline capture is still incomplete."
    )
    lines.append("- Final donor compliance review remains human-owned.")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a short one-file pilot handout from existing GrantFlow pilot/executive artifacts."
    )
    parser.add_argument("--pilot-pack-dir", default="build/pilot-pack")
    parser.add_argument("--executive-pack-dir", default="build/executive-pack")
    parser.add_argument("--output", default="build/pilot-handout.md")
    parser.add_argument("--preset-key", default="")
    parser.add_argument("--case-dir", default="")
    args = parser.parse_args()

    pilot_pack_dir = Path(str(args.pilot_pack_dir)).resolve()
    executive_pack_dir = Path(str(args.executive_pack_dir)).resolve()
    output_path = Path(str(args.output)).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    benchmark_path = pilot_pack_dir / "live-runs" / "benchmark-results.json"
    scorecard_path = pilot_pack_dir / "pilot-scorecard.md"
    metrics_path = pilot_pack_dir / "pilot-metrics.csv"
    if not benchmark_path.exists():
        raise SystemExit(f"Missing benchmark results: {benchmark_path}")
    if not scorecard_path.exists():
        raise SystemExit(f"Missing pilot scorecard: {scorecard_path}")
    if not metrics_path.exists():
        raise SystemExit(f"Missing pilot metrics csv: {metrics_path}")

    rows = _read_json(benchmark_path)
    if not isinstance(rows, list) or not rows:
        raise SystemExit("pilot benchmark results must contain a non-empty list")

    featured_row = _resolve_featured_case(
        rows,
        preset_key=str(args.preset_key).strip(),
        case_dir=str(args.case_dir).strip(),
    )

    scorecard_text = scorecard_path.read_text(encoding="utf-8")
    verdict = next(
        (line.split("`")[1] for line in scorecard_text.splitlines() if line.startswith("- Verdict: `") and "`" in line),
        "-",
    )
    readiness = next(
        (
            line.split("`")[1]
            for line in scorecard_text.splitlines()
            if line.startswith("- Readiness: `") and "`" in line
        ),
        "-",
    )
    baseline_complete_cases = next(
        (
            line.split("`")[1]
            for line in scorecard_text.splitlines()
            if line.startswith("- Baseline-complete cases: `") and "`" in line
        ),
        "-",
    )
    current_conditions = _extract_markdown_bullets(scorecard_text, "## Conditions Before Buyer Decision")

    quality_values = [float(row["quality_score"]) for row in rows if str(row.get("quality_score") or "").strip()]
    critic_values = [float(row["critic_score"]) for row in rows if str(row.get("critic_score") or "").strip()]
    quality_avg = sum(quality_values) / len(quality_values) if quality_values else None
    critic_avg = sum(critic_values) / len(critic_values) if critic_values else None

    quality_path = pilot_pack_dir / "live-runs" / str(featured_row.get("case_dir") or "") / "quality.json"
    quality_payload = _read_json(quality_path) if quality_path.exists() else {}
    featured_review_readiness = (
        quality_payload.get("review_readiness_summary") if isinstance(quality_payload, dict) else {}
    )
    featured_review_readiness = featured_review_readiness if isinstance(featured_review_readiness, dict) else {}
    featured_review_readiness = {
        "open_review_comments": 0,
        "resolved_review_comments": 0,
        "pending_review_comments": 0,
        "overdue_review_comments": 0,
        "linked_review_comments": 0,
        "orphan_linked_review_comments": 0,
        **featured_review_readiness,
    }
    featured_triage_summary = quality_payload.get("triage_summary") if isinstance(quality_payload, dict) else {}
    featured_triage_summary = featured_triage_summary if isinstance(featured_triage_summary, dict) else {}
    featured_mel_summary = quality_payload.get("mel") if isinstance(quality_payload, dict) else {}
    featured_mel_summary = featured_mel_summary if isinstance(featured_mel_summary, dict) else {}
    critic_path = pilot_pack_dir / "live-runs" / str(featured_row.get("case_dir") or "") / "critic.json"
    featured_critic_payload = _read_json(critic_path) if critic_path.exists() else {}
    featured_critic_payload = featured_critic_payload if isinstance(featured_critic_payload, dict) else {}
    export_payload_path = pilot_pack_dir / "live-runs" / str(featured_row.get("case_dir") or "") / "export-payload.json"
    export_payload = _read_json(export_payload_path) if export_payload_path.exists() else {}
    export_payload = export_payload if isinstance(export_payload, dict) else {}
    if not featured_triage_summary:
        triage_from_critic = featured_critic_payload.get("triage_summary")
        featured_triage_summary = triage_from_critic if isinstance(triage_from_critic, dict) else {}
    if not featured_triage_summary:
        raw_findings = featured_critic_payload.get("fatal_flaws")
        findings = [row for row in raw_findings if isinstance(row, dict)] if isinstance(raw_findings, list) else []
        featured_triage_summary = (
            _critic_triage_summary_payload(findings, donor_id=str(featured_row.get("donor_id") or "").strip())
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
        raw_findings = featured_critic_payload.get("fatal_flaws")
        findings = [row for row in raw_findings if isinstance(row, dict)] if isinstance(raw_findings, list) else []
        if review_comments:
            comment_triage = _comment_triage_summary_payload(
                review_comments=review_comments,
                critic_findings=findings,
                donor_id=str(featured_row.get("donor_id") or "").strip(),
            )
            featured_review_readiness = {
                **featured_review_readiness,
                "open_review_comments": comment_triage.get("open_comment_count"),
                "resolved_review_comments": comment_triage.get("resolved_comment_count"),
                "pending_review_comments": comment_triage.get("pending_comment_count"),
                "overdue_review_comments": comment_triage.get("overdue_comment_count"),
                "linked_review_comments": comment_triage.get("linked_comment_count"),
                "orphan_linked_review_comments": comment_triage.get("orphan_linked_comment_count"),
                "comment_triage_summary": comment_triage,
            }

    review_ready_cases_count = 0
    for row in rows:
        row_quality_path = pilot_pack_dir / "live-runs" / str(row.get("case_dir") or "") / "quality.json"
        row_quality = _read_json(row_quality_path) if row_quality_path.exists() else {}
        mel = row_quality.get("mel") if isinstance(row_quality, dict) else {}
        if not isinstance(mel, dict):
            continue
        smart = _safe_float(mel.get("smart_field_coverage_rate"))
        mov = _safe_float(mel.get("means_of_verification_coverage_rate"))
        owner = _safe_float(mel.get("owner_coverage_rate"))
        if smart == 1.0 and mov == 1.0 and owner == 1.0:
            review_ready_cases_count += 1

    output_path.write_text(
        _build_handout(
            pilot_pack_name=pilot_pack_dir.name,
            executive_pack_name=executive_pack_dir.name,
            rows=rows,
            featured_row=featured_row,
            quality_avg=quality_avg,
            critic_avg=critic_avg,
            verdict=verdict,
            readiness=readiness,
            baseline_complete_cases=baseline_complete_cases,
            featured_review_readiness=featured_review_readiness,
            featured_triage_summary=featured_triage_summary,
            featured_critic_payload=featured_critic_payload,
            featured_mel_summary=featured_mel_summary,
            review_ready_cases=f"{review_ready_cases_count}/{len(rows)}",
            current_conditions=current_conditions,
        ),
        encoding="utf-8",
    )
    print(f"pilot handout saved to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
