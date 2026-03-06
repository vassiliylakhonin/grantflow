#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


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


def _build_case_row(case_dir: Path, benchmark_row: dict[str, Any]) -> dict[str, Any]:
    metrics_path = case_dir / "metrics.json"
    quality_path = case_dir / "quality.json"
    metrics = _read_json(metrics_path) if metrics_path.exists() else {}
    quality = _read_json(quality_path) if quality_path.exists() else {}

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
    lines.append("")
    lines.append("## Case Table")
    lines.append("")
    lines.append(
        "| Preset | Donor | Status | HITL | Quality | Critic | Citations | First Draft (s) | Terminal (s) | Pending HITL (s) |"
    )
    lines.append("|---|---|---|---|---:|---:|---:|---:|---:|---:|")
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
                    _fmt(_safe_int(row.get("citation_count"))),
                    _fmt(_safe_float(row.get("time_to_first_draft_seconds"))),
                    _fmt(_safe_float(row.get("time_to_terminal_seconds"))),
                    _fmt(_safe_float(row.get("time_in_pending_hitl_seconds"))),
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
