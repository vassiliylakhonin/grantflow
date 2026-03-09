#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from grantflow.api.public_views import _critic_triage_summary_payload


ROOT_FILES = (
    "buyer-brief.md",
    "pilot-scorecard.md",
    "pilot-metrics.md",
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
    review_ready_cases: str,
    portfolio_open_findings_avg: float | None,
    portfolio_fallback_avg: float | None,
    portfolio_low_confidence_avg: float | None,
    portfolio_smart_avg: float | None,
    portfolio_mov_avg: float | None,
    portfolio_owner_avg: float | None,
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
    lines.append(f"- Average fallback/strategy citations per case: `{_format_num(portfolio_fallback_avg)}`")
    lines.append(f"- Average low-confidence citations per case: `{_format_num(portfolio_low_confidence_avg)}`")
    lines.append(f"- Average SMART coverage: `{_format_num(portfolio_smart_avg)}`")
    lines.append(f"- Average MoV coverage: `{_format_num(portfolio_mov_avg)}`")
    lines.append(f"- Average owner coverage: `{_format_num(portfolio_owner_avg)}`")
    lines.append("")
    lines.append("## Readiness Snapshot")
    lines.append(
        f"- Open critic findings (featured case): `{featured_review_readiness.get('open_critic_findings', '-')}`"
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
    featured_triage_summary = quality_payload.get("triage_summary")
    if not isinstance(featured_triage_summary, dict):
        featured_triage_summary = {}
    featured_mel_summary = quality_payload.get("mel")
    if not isinstance(featured_mel_summary, dict):
        featured_mel_summary = {}
    critic_payload = _read_json(pilot_pack_dir / "live-runs" / resolved_case_dir / "critic.json")
    if not isinstance(critic_payload, dict):
        critic_payload = {}
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
    portfolio_fallback_avg = _avg([_safe_int(row.get("fallback_strategy_citations")) for row in metrics_rows])
    portfolio_low_confidence_avg = _avg([_safe_int(row.get("low_confidence_citations")) for row in metrics_rows])
    portfolio_smart_avg = _avg([_safe_float(row.get("smart_field_coverage_rate")) for row in metrics_rows])
    portfolio_mov_avg = _avg([_safe_float(row.get("means_of_verification_coverage_rate")) for row in metrics_rows])
    portfolio_owner_avg = _avg([_safe_float(row.get("owner_coverage_rate")) for row in metrics_rows])
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
            review_ready_cases=f"{review_ready_cases_count}/{len(rows)}",
            portfolio_open_findings_avg=portfolio_open_findings_avg,
            portfolio_fallback_avg=portfolio_fallback_avg,
            portfolio_low_confidence_avg=portfolio_low_confidence_avg,
            portfolio_smart_avg=portfolio_smart_avg,
            portfolio_mov_avg=portfolio_mov_avg,
            portfolio_owner_avg=portfolio_owner_avg,
            conditional_reasons=conditional_reasons,
        ),
        encoding="utf-8",
    )
    print(f"executive pack saved to {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
