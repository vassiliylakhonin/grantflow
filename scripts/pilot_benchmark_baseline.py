#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from math import ceil
from pathlib import Path
from typing import Any


FIELDNAMES = [
    "case_dir",
    "preset_key",
    "donor_id",
    "pilot_time_to_first_draft_seconds",
    "pilot_time_to_terminal_seconds",
    "pilot_review_loops",
    "baseline_type",
    "baseline_method",
    "baseline_source",
    "baseline_confidence",
    "benchmark_baseline_type",
    "benchmark_method",
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


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _safe_float(value: str | None) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_int(value: str | None) -> int | None:
    try:
        if value is None or value == "":
            return None
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _derive_first_draft_baseline(current_seconds: float | None) -> int:
    if current_seconds is None:
        return 14400
    return max(int(round(current_seconds * 1.75)), int(round(current_seconds + 3600)), 14400)


def _derive_terminal_baseline(current_seconds: float | None) -> int:
    if current_seconds is None:
        return 86400
    return max(int(round(current_seconds * 2.5)), int(round(current_seconds + 14400)), 86400)


def _derive_review_loops_baseline(current_loops: int | None) -> int:
    if current_loops is None:
        return 5
    return max(current_loops + 2, ceil(current_loops * 1.5), 5)


def _load_curated_assumptions(path: Path | None) -> dict[str, dict[str, Any]]:
    if path is None or not path.exists():
        return {}
    payload = _read_json(path)
    if not isinstance(payload, dict):
        raise SystemExit(f"Benchmark assumptions file must contain an object: {path}")
    out: dict[str, dict[str, Any]] = {}
    for preset_key, row in payload.items():
        if isinstance(preset_key, str) and isinstance(row, dict):
            out[preset_key.strip()] = row
    return out


def _build_rows(metrics_rows: list[dict[str, str]], *, curated: dict[str, dict[str, Any]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    capture_date = datetime.now(timezone.utc).date().isoformat()
    for source in metrics_rows:
        current_first = _safe_float(source.get("time_to_first_draft_seconds"))
        current_terminal = _safe_float(source.get("time_to_terminal_seconds"))
        current_loops = _safe_int(source.get("status_change_count"))
        preset_key = str(source.get("preset_key") or "")
        curated_row = curated.get(preset_key.strip(), {})
        baseline_first = (
            _safe_int(str(curated_row.get("baseline_time_to_first_draft_seconds")))
            if curated_row.get("baseline_time_to_first_draft_seconds") is not None
            else _derive_first_draft_baseline(current_first)
        )
        baseline_terminal = (
            _safe_int(str(curated_row.get("baseline_time_to_terminal_seconds")))
            if curated_row.get("baseline_time_to_terminal_seconds") is not None
            else _derive_terminal_baseline(current_terminal)
        )
        baseline_loops = (
            _safe_int(str(curated_row.get("baseline_review_loops")))
            if curated_row.get("baseline_review_loops") is not None
            else _derive_review_loops_baseline(current_loops)
        )
        rows.append(
            {
                "case_dir": str(source.get("case_dir") or ""),
                "preset_key": preset_key,
                "donor_id": str(source.get("donor_id") or ""),
                "pilot_time_to_first_draft_seconds": str(source.get("time_to_first_draft_seconds") or ""),
                "pilot_time_to_terminal_seconds": str(source.get("time_to_terminal_seconds") or ""),
                "pilot_review_loops": str(source.get("status_change_count") or ""),
                "baseline_type": "illustrative",
                "baseline_method": str(curated_row.get("benchmark_method") or "conservative_demo_benchmark_v1"),
                "baseline_source": "GrantFlow demo benchmark assumptions",
                "baseline_confidence": "illustrative",
                "benchmark_baseline_type": str(curated_row.get("benchmark_baseline_type") or "illustrative"),
                "benchmark_method": str(curated_row.get("benchmark_method") or "conservative_demo_benchmark_v1"),
                "baseline_time_to_first_draft_seconds": str(baseline_first),
                "baseline_time_to_terminal_seconds": str(baseline_terminal),
                "baseline_review_loops": str(baseline_loops),
                "baseline_owner": "GrantFlow demo benchmark",
                "baseline_capture_date": capture_date,
                "baseline_notes": str(
                    curated_row.get("baseline_notes")
                    or (
                        "Illustrative benchmark baseline for demo and pilot-pack storytelling only. "
                        "This is not a measured customer baseline and must be replaced before a real pilot decision."
                    )
                ),
            }
        )
    return rows


def _build_markdown(rows: list[dict[str, str]], *, pilot_pack_name: str) -> str:
    lines: list[str] = []
    lines.append("# Benchmark Baseline")
    lines.append("")
    lines.append(f"Generated at: {datetime.now(timezone.utc).isoformat()}")
    lines.append(f"- Pilot pack: `{pilot_pack_name}`")
    lines.append("")
    lines.append("## Purpose")
    lines.append("This file provides an illustrative benchmark baseline for demo and buyer-facing pilot evidence only.")
    lines.append("It is not measured customer data and must not be presented as actual pre-pilot performance.")
    lines.append("")
    lines.append("## Benchmark Method")
    lines.append("- Preferred path: curated demo assumptions per representative preset when available.")
    lines.append("- Fallback path: conservative uplift over current pilot timings and review loops.")
    lines.append("- Formula fallback minimums: first draft 4h, terminal 24h, review loops 5.")
    lines.append("")
    lines.append("## Case Table")
    lines.append("")
    lines.append(
        "| Preset | Donor | Baseline Type | Benchmark First Draft (s) | Benchmark Terminal (s) | Benchmark Review Loops |"
    )
    lines.append("|---|---|---|---:|---:|---:|")
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{row.get('preset_key') or '-'}`",
                    f"`{row.get('donor_id') or '-'}`",
                    f"`{row.get('benchmark_baseline_type') or '-'}`",
                    row.get("baseline_time_to_first_draft_seconds") or "-",
                    row.get("baseline_time_to_terminal_seconds") or "-",
                    row.get("baseline_review_loops") or "-",
                ]
            )
            + " |"
        )
    lines.append("")
    lines.append("## Usage")
    lines.append("- Use this only when a demo or pilot evidence bundle needs an illustrative before/after view.")
    lines.append("- Replace it with measured baseline data before any real pilot go/no-go decision.")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build an illustrative benchmark baseline from an existing GrantFlow pilot metrics table."
    )
    parser.add_argument("--pilot-pack-dir", default="build/pilot-pack")
    parser.add_argument("--metrics-csv", default="")
    parser.add_argument("--assumptions-json", default="docs/pilot_benchmark_assumptions.json")
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

    assumptions_path = Path(str(args.assumptions_json)).resolve() if str(args.assumptions_json).strip() else None
    curated = _load_curated_assumptions(assumptions_path)
    rows = _build_rows(metrics_rows, curated=curated)
    csv_out = (
        Path(str(args.csv_out)).resolve() if str(args.csv_out).strip() else pilot_pack_dir / "benchmark-baseline.csv"
    )
    md_out = Path(str(args.md_out)).resolve() if str(args.md_out).strip() else pilot_pack_dir / "benchmark-baseline.md"
    _write_csv(csv_out, rows)
    md_out.write_text(_build_markdown(rows, pilot_pack_name=pilot_pack_dir.name), encoding="utf-8")
    print(f"benchmark baseline saved to {csv_out} and {md_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
