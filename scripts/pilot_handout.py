#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


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
    lines.append("")
    lines.append("## Why This Matters")
    lines.append("- Faster path to a reviewable draft, not just generated text.")
    lines.append("- Lower review chaos through explicit workflow state and traceability.")
    lines.append("- Exportable artifacts for downstream proposal operations.")
    lines.append("")
    lines.append("## Featured Case")
    lines.append(f"- Donor: `{featured_row.get('donor_id')}`")
    lines.append(f"- Preset: `{featured_row.get('preset_key')}`")
    lines.append(f"- Case dir: `{featured_row.get('case_dir')}`")
    lines.append(f"- Job ID: `{featured_row.get('job_id')}`")
    lines.append(f"- Status: `{featured_row.get('status')}`")
    lines.append(f"- HITL enabled: `{'true' if featured_row.get('hitl_enabled') else 'false'}`")
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

    quality_values = [float(row["quality_score"]) for row in rows if str(row.get("quality_score") or "").strip()]
    critic_values = [float(row["critic_score"]) for row in rows if str(row.get("critic_score") or "").strip()]
    quality_avg = sum(quality_values) / len(quality_values) if quality_values else None
    critic_avg = sum(critic_values) / len(critic_values) if critic_values else None

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
        ),
        encoding="utf-8",
    )
    print(f"pilot handout saved to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
