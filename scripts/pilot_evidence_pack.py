#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _copy_if_exists(src: Path, dst: Path) -> None:
    if not src.exists():
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def _copy_tree_if_exists(src: Path, dst: Path) -> None:
    if not src.exists():
        return
    if dst.exists():
        shutil.rmtree(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, dst)


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


def _format_num(value: float | int | None) -> str:
    if value is None:
        return "-"
    if isinstance(value, int):
        return str(value)
    if float(value).is_integer():
        return str(int(value))
    return f"{value:.2f}"


def _format_seconds(seconds: float | int | None) -> str:
    if seconds is None:
        return "-"
    total = int(round(float(seconds)))
    minutes, sec = divmod(total, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h {minutes}m"
    if minutes:
        return f"{minutes}m {sec}s"
    return f"{sec}s"


def _parse_conditions(scorecard_text: str) -> list[str]:
    lines = scorecard_text.splitlines()
    out: list[str] = []
    capture = False
    for line in lines:
        if line.strip() in {"## Current Conditions", "## Conditions Before Buyer Decision"}:
            capture = True
            continue
        if capture and line.startswith("## "):
            break
        if capture and line.startswith("- "):
            out.append(line[2:].strip())
    return out


def _top_blockers(conditions: list[str], *, limit: int = 3) -> list[str]:
    priority_tokens = (
        "resolution rate",
        "acknowledgment rate",
        ">7d",
        "stale",
        "baseline",
        "fallback",
        "queue",
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
            if len(ranked) >= limit:
                break
    return ranked


def _before_after_rows(metrics_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for row in metrics_rows:
        baseline_first = _safe_float(row.get("baseline_time_to_first_draft_seconds"))
        baseline_terminal = _safe_float(row.get("baseline_time_to_terminal_seconds"))
        baseline_loops = _safe_int(row.get("baseline_review_loops"))
        out.append(
            {
                "preset_key": str(row.get("preset_key") or "").strip(),
                "donor_id": str(row.get("donor_id") or "").strip(),
                "baseline_present": (
                    "yes"
                    if baseline_first is not None or baseline_terminal is not None or baseline_loops is not None
                    else "no"
                ),
                "baseline_first": _format_seconds(baseline_first),
                "current_first": _format_seconds(_safe_float(row.get("time_to_first_draft_seconds"))),
                "baseline_terminal": _format_seconds(baseline_terminal),
                "current_terminal": _format_seconds(_safe_float(row.get("time_to_terminal_seconds"))),
                "baseline_loops": str(baseline_loops) if baseline_loops is not None else "-",
                "current_finding_ack_queue": _format_num(_safe_float(row.get("finding_ack_queue_count"))),
                "current_open_review_comments": _format_num(_safe_int(row.get("open_review_comments"))),
            }
        )
    return out


def _representative_case(metrics_rows: list[dict[str, str]]) -> dict[str, str]:
    if not metrics_rows:
        return {}
    return sorted(
        metrics_rows,
        key=lambda row: (
            -(float(row.get("quality_score") or 0.0)),
            -(float(row.get("critic_score") or 0.0)),
            str(row.get("preset_key") or ""),
        ),
    )[0]


def _build_readme(
    *,
    portfolio_summary: dict[str, Any],
    metrics_rows: list[dict[str, str]],
    scorecard_text: str,
    case_study_name: str | None,
    has_executive_pack: bool,
) -> str:
    blockers = _top_blockers(_parse_conditions(scorecard_text))
    before_after = _before_after_rows(metrics_rows)
    rep = _representative_case(metrics_rows)

    lines: list[str] = []
    lines.append("# Pilot Evidence Pack")
    lines.append("")
    lines.append(f"Generated at: {datetime.now(timezone.utc).isoformat()}")
    lines.append("")
    lines.append("## Purpose")
    lines.append(
        "This compact bundle is meant for pilot conversations. It shows current workflow evidence, evidence quality, "
        "and any before/after baseline coverage already captured."
    )
    lines.append("")
    lines.append("## Current Pilot State")
    lines.append(f"- Cases: `{_format_num(_safe_int(portfolio_summary.get('case_count')))}`")
    lines.append(f"- Average quality score: `{_format_num(_safe_float(portfolio_summary.get('avg_quality_score')))}`")
    lines.append(f"- Average critic score: `{_format_num(_safe_float(portfolio_summary.get('avg_critic_score')))}`")
    lines.append(
        f"- Workflow policy status: `{str(portfolio_summary.get('portfolio_review_workflow_policy_status') or '-').strip() or '-'}`"
    )
    lines.append(
        f"- Go/no-go: `{str(portfolio_summary.get('portfolio_review_workflow_policy_go_no_go_flag') or '-').strip() or '-'}`"
    )
    lines.append(
        f"- Next operational action: `{str(portfolio_summary.get('portfolio_review_workflow_next_operational_action') or '-').strip() or '-'}`"
    )
    lines.append("")
    lines.append("## Draft Evidence Layer")
    lines.append(
        f"- Architect grounding rate: `{_format_num(_safe_float(portfolio_summary.get('avg_architect_retrieval_grounded_citation_rate')))}`"
    )
    lines.append(
        f"- MEL grounding rate: `{_format_num(_safe_float(portfolio_summary.get('avg_mel_retrieval_grounded_citation_rate')))}`"
    )
    lines.append(
        f"- Architect fallback citations per case: `{_format_num(_safe_float(portfolio_summary.get('avg_architect_fallback_namespace_citation_count')))}`"
    )
    lines.append(
        f"- MEL fallback citations per case: `{_format_num(_safe_float(portfolio_summary.get('avg_mel_fallback_namespace_citation_count')))}`"
    )
    if str(portfolio_summary.get("top_architect_evidence_signal") or "").strip():
        lines.append(f"- Top architect evidence signal: `{portfolio_summary.get('top_architect_evidence_signal')}`")
    if str(portfolio_summary.get("top_mel_evidence_signal") or "").strip():
        lines.append(f"- Top MEL evidence signal: `{portfolio_summary.get('top_mel_evidence_signal')}`")
    lines.append("")
    lines.append("## Review Workflow Evidence")
    lines.append(
        f"- Average finding ack queue per case: `{_format_num(_safe_float(portfolio_summary.get('avg_finding_ack_queue')))}`"
    )
    lines.append(
        f"- Average comment resolve queue per case: `{_format_num(_safe_float(portfolio_summary.get('avg_comment_resolve_queue')))}`"
    )
    lines.append(
        f"- Average reviewer workflow resolution rate: `{_format_num(_safe_float(portfolio_summary.get('avg_reviewer_workflow_resolution_rate')))}`"
    )
    lines.append(
        f"- Average reviewer workflow acknowledgment rate: `{_format_num(_safe_float(portfolio_summary.get('avg_reviewer_workflow_acknowledgment_rate')))}`"
    )
    lines.append(
        f"- Stale thread donor/bucket mix: `{str(portfolio_summary.get('stale_thread_donor_bucket_mix') or '-').strip() or '-'}`"
    )
    lines.append("")
    lines.append("## Top Blocking Thresholds")
    if blockers:
        for item in blockers:
            lines.append(f"- {item}")
    else:
        lines.append("- No blocking thresholds currently recorded.")
    lines.append("")
    lines.append("## Before/After Snapshot")
    lines.append("")
    lines.append(
        "| Preset | Donor | Baseline Present | Baseline First Draft | Current First Draft | Baseline Terminal | Current Terminal | Baseline Review Loops | Current Finding Ack Queue | Current Open Review Comments |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---:|---:|")
    for row in before_after:
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{row['preset_key']}`",
                    f"`{row['donor_id']}`",
                    row["baseline_present"],
                    row["baseline_first"],
                    row["current_first"],
                    row["baseline_terminal"],
                    row["current_terminal"],
                    row["baseline_loops"],
                    row["current_finding_ack_queue"],
                    row["current_open_review_comments"],
                ]
            )
            + " |"
        )
    lines.append("")
    lines.append("## Representative Case")
    if rep:
        lines.append(f"- Preset: `{str(rep.get('preset_key') or '').strip()}`")
        lines.append(f"- Donor: `{str(rep.get('donor_id') or '').strip()}`")
        lines.append(f"- Quality score: `{_format_num(_safe_float(rep.get('quality_score')))}`")
        lines.append(f"- Critic score: `{_format_num(_safe_float(rep.get('critic_score')))}`")
        lines.append(
            f"- Next review action: `{str(rep.get('next_recommended_action') or rep.get('review_workflow_next_operational_action') or '-').strip() or '-'}`"
        )
    else:
        lines.append("- No representative case available.")
    lines.append("")
    lines.append("## Included")
    lines.append("- `evidence-summary.json`: machine-readable pilot evidence snapshot")
    lines.append("- `pilot-pack/`: full pilot evidence bundle")
    if has_executive_pack:
        lines.append("- `executive-pack/`: short buyer-facing packet")
    if case_study_name:
        lines.append(f"- `case-study/{case_study_name}/`: representative case")
    lines.append("- `baseline-fill-template.csv` and `baseline-fill-template.md` when available")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Assemble a compact GrantFlow pilot evidence pack.")
    parser.add_argument("--pilot-pack-dir", default="build/pilot-pack")
    parser.add_argument("--executive-pack-dir", default="build/executive-pack")
    parser.add_argument("--case-study-dir", default="build/case-study-pack")
    parser.add_argument("--output-dir", default="build/pilot-evidence-pack")
    args = parser.parse_args()

    pilot_pack_dir = Path(str(args.pilot_pack_dir)).resolve()
    executive_pack_dir = Path(str(args.executive_pack_dir)).resolve()
    case_study_dir = Path(str(args.case_study_dir)).resolve()
    output_dir = Path(str(args.output_dir)).resolve()

    portfolio_summary_path = pilot_pack_dir / "pilot-portfolio-summary.json"
    metrics_csv_path = pilot_pack_dir / "pilot-metrics.csv"
    scorecard_path = pilot_pack_dir / "pilot-scorecard.md"
    if not portfolio_summary_path.exists():
        raise SystemExit(f"Missing portfolio summary: {portfolio_summary_path}")
    if not metrics_csv_path.exists():
        raise SystemExit(f"Missing metrics csv: {metrics_csv_path}")
    if not scorecard_path.exists():
        raise SystemExit(f"Missing scorecard: {scorecard_path}")

    portfolio_summary = _read_json(portfolio_summary_path)
    if not isinstance(portfolio_summary, dict):
        raise SystemExit("pilot-portfolio-summary.json must contain an object")
    metrics_rows = _read_csv_rows(metrics_csv_path)
    scorecard_text = scorecard_path.read_text(encoding="utf-8")

    case_study_name = None
    if case_study_dir.exists():
        case_dirs = sorted([path for path in case_study_dir.iterdir() if path.is_dir()])
        if case_dirs:
            case_study_name = case_dirs[0].name

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    _copy_tree_if_exists(pilot_pack_dir, output_dir / "pilot-pack")
    _copy_tree_if_exists(executive_pack_dir, output_dir / "executive-pack")
    if case_study_name:
        _copy_tree_if_exists(case_study_dir / case_study_name, output_dir / "case-study" / case_study_name)
    _copy_if_exists(pilot_pack_dir / "baseline-fill-template.csv", output_dir / "baseline-fill-template.csv")
    _copy_if_exists(pilot_pack_dir / "baseline-fill-template.md", output_dir / "baseline-fill-template.md")

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "portfolio_summary": portfolio_summary,
        "top_blocking_thresholds": _top_blockers(_parse_conditions(scorecard_text)),
        "before_after_rows": _before_after_rows(metrics_rows),
        "representative_case": _representative_case(metrics_rows),
        "case_study": case_study_name or "",
    }
    (output_dir / "evidence-summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (output_dir / "README.md").write_text(
        _build_readme(
            portfolio_summary=portfolio_summary,
            metrics_rows=metrics_rows,
            scorecard_text=scorecard_text,
            case_study_name=case_study_name,
            has_executive_pack=executive_pack_dir.exists(),
        ),
        encoding="utf-8",
    )
    print(f"pilot evidence pack saved to {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
