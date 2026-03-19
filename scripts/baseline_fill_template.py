#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
from pathlib import Path

FIELDNAMES = [
    "case_dir",
    "preset_key",
    "donor_id",
    "pilot_time_to_first_draft_seconds",
    "pilot_time_to_terminal_seconds",
    "pilot_review_loops",
    "pilot_pause_count",
    "pilot_resume_count",
    "pilot_quality_score",
    "pilot_critic_score",
    "pilot_citation_count",
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
]


def _read_metrics_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _build_rows(metrics_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for source in metrics_rows:
        rows.append(
            {
                "case_dir": str(source.get("case_dir") or ""),
                "preset_key": str(source.get("preset_key") or ""),
                "donor_id": str(source.get("donor_id") or ""),
                "pilot_time_to_first_draft_seconds": str(source.get("time_to_first_draft_seconds") or ""),
                "pilot_time_to_terminal_seconds": str(source.get("time_to_terminal_seconds") or ""),
                "pilot_review_loops": str(source.get("status_change_count") or ""),
                "pilot_pause_count": str(source.get("pause_count") or ""),
                "pilot_resume_count": str(source.get("resume_count") or ""),
                "pilot_quality_score": str(source.get("quality_score") or ""),
                "pilot_critic_score": str(source.get("critic_score") or ""),
                "pilot_citation_count": str(source.get("citation_count") or ""),
                "baseline_type": "measured",
                "baseline_method": "",
                "baseline_source": "",
                "baseline_confidence": "",
                "baseline_time_to_first_draft_seconds": str(source.get("baseline_time_to_first_draft_seconds") or ""),
                "baseline_time_to_terminal_seconds": str(source.get("baseline_time_to_terminal_seconds") or ""),
                "baseline_review_loops": str(source.get("baseline_review_loops") or ""),
                "baseline_owner": "",
                "baseline_capture_date": "",
                "baseline_notes": str(source.get("baseline_notes") or ""),
            }
        )
    return rows


def _build_markdown(rows: list[dict[str, str]], *, pilot_pack_name: str) -> str:
    lines: list[str] = []
    lines.append("# Baseline Fill Template")
    lines.append("")
    lines.append(f"Generated at: {datetime.now(timezone.utc).isoformat()}")
    lines.append(f"- Pilot pack: `{pilot_pack_name}`")
    lines.append("")
    lines.append("## How To Use")
    lines.append("1. Fill baseline columns for each representative case before the pilot starts.")
    lines.append("2. Record source, method, owner, and capture date for each row.")
    lines.append("3. Keep pilot columns unchanged; they are copied from `pilot-metrics.csv`.")
    lines.append(
        "4. Save the completed sheet as `measured-baseline.csv` in the pilot pack directory or pass it to `pilot-metrics`."
    )
    lines.append("5. Re-run `make pilot-metrics` and `make pilot-scorecard` after measured values are filled.")
    lines.append("")
    lines.append("## Fields To Fill")
    lines.append("- `baseline_type` (`measured` for real pilot evidence)")
    lines.append("- `baseline_method`")
    lines.append("- `baseline_source` (`CRM export`, `proposal tracker`, `manual timing log`, etc.)")
    lines.append(
        "- `baseline_confidence` (`1.0` for measured log-backed values; lower only if partially reconstructed)"
    )
    lines.append("- `baseline_time_to_first_draft_seconds`")
    lines.append("- `baseline_time_to_terminal_seconds`")
    lines.append("- `baseline_review_loops`")
    lines.append("- `baseline_owner`")
    lines.append("- `baseline_capture_date`")
    lines.append("- `baseline_notes`")
    lines.append("")
    lines.append("## Case Table")
    lines.append("")
    lines.append(
        "| Preset | Donor | Pilot First Draft (s) | Pilot Terminal (s) | Pilot Review Loops | Baseline First Draft (s) | Baseline Terminal (s) | Baseline Review Loops |"
    )
    lines.append("|---|---|---:|---:|---:|---:|---:|---:|")
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{row.get('preset_key')}`",
                    f"`{row.get('donor_id')}`",
                    row.get("pilot_time_to_first_draft_seconds") or "-",
                    row.get("pilot_time_to_terminal_seconds") or "-",
                    row.get("pilot_review_loops") or "-",
                    row.get("baseline_time_to_first_draft_seconds") or "-",
                    row.get("baseline_time_to_terminal_seconds") or "-",
                    row.get("baseline_review_loops") or "-",
                ]
            )
            + " |"
        )
    lines.append("")
    lines.append("## Notes")
    lines.append("- This file is an operator worksheet for pilot setup.")
    lines.append(
        "- For real pilot evidence, save the completed version as `measured-baseline.csv` and re-run the pilot artifact generators."
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a fillable baseline worksheet from an existing GrantFlow pilot metrics table."
    )
    parser.add_argument("--pilot-pack-dir", default="build/pilot-pack")
    parser.add_argument("--metrics-csv", default="")
    parser.add_argument("--csv-out", default="")
    parser.add_argument("--md-out", default="")
    args = parser.parse_args()

    pilot_pack_dir = Path(str(args.pilot_pack_dir)).resolve()
    metrics_csv = (
        Path(str(args.metrics_csv)).resolve() if str(args.metrics_csv).strip() else pilot_pack_dir / "pilot-metrics.csv"
    )
    if not metrics_csv.exists():
        raise SystemExit(f"Missing pilot metrics csv: {metrics_csv}. Run make pilot-metrics first.")

    metrics_rows = _read_metrics_csv(metrics_csv)
    if not metrics_rows:
        raise SystemExit("pilot metrics csv must contain at least one case row")

    rows = _build_rows(metrics_rows)
    csv_out = (
        Path(str(args.csv_out)).resolve()
        if str(args.csv_out).strip()
        else pilot_pack_dir / "baseline-fill-template.csv"
    )
    md_out = (
        Path(str(args.md_out)).resolve() if str(args.md_out).strip() else pilot_pack_dir / "baseline-fill-template.md"
    )
    _write_csv(csv_out, rows)
    md_out.write_text(_build_markdown(rows, pilot_pack_name=pilot_pack_dir.name), encoding="utf-8")
    print(f"baseline fill template saved to {csv_out} and {md_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
