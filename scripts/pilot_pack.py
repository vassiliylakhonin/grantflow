#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _copy_if_exists(src: Path, dst: Path) -> None:
    if src.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def _copy_tree(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def _build_summary(
    rows: list[dict[str, Any]],
    *,
    demo_pack_dir_name: str,
    include_productization_memo: bool,
) -> str:
    lines: list[str] = []
    lines.append("# Pilot Pack")
    lines.append("")
    lines.append(f"Generated at: {datetime.now(timezone.utc).isoformat()}")
    lines.append("")
    lines.append("## Purpose")
    lines.append(
        "This bundle is intended for pilot review with proposal operations stakeholders. "
        "It combines live run evidence, sample export artifacts, and pilot evaluation guidance."
    )
    lines.append("")
    lines.append("## Included")
    lines.append(f"- Live run evidence copied from `{demo_pack_dir_name}`")
    lines.append("- Buyer-facing context note (`buyer-one-pager.md`)")
    lines.append("- Pilot evaluation checklist (`pilot-evaluation-checklist.md`)")
    lines.append("- Demo runbook (`demo-runbook.md`)")
    if include_productization_memo:
        lines.append("- Productization gaps memo (`productization-gaps-memo.md`)")
    lines.append("")
    lines.append("## Case Summary")
    lines.append("")
    lines.append("| Preset | Donor | Job ID | Status | Quality | Critic | Citations | HITL |")
    lines.append("|---|---|---|---|---:|---:|---:|---|")
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{row.get('preset_key')}`",
                    f"`{row.get('donor_id')}`",
                    f"`{row.get('job_id')}`",
                    str(row.get("status")),
                    str(row.get("quality_score")),
                    str(row.get("critic_score")),
                    str(row.get("citation_count")),
                    "yes" if row.get("hitl_enabled") else "no",
                ]
            )
            + " |"
        )
    lines.append("")
    lines.append("## Recommended Stakeholder Review")
    lines.append("1. Review `live-runs/summary.md` for overall case outcomes and artifact inventory.")
    lines.append(
        "2. Open one representative case folder and inspect `status.json`, `quality.json`, `critic.json`, and exports."
    )
    lines.append(
        "3. Use `pilot-evaluation-checklist.md` to map these outputs to pilot success criteria and go/no-go decision."
    )
    lines.append("")
    lines.append("## Notes")
    lines.append("- These are pilot artifacts, not final donor submissions.")
    lines.append("- Grounding quality remains dependent on corpus quality when retrieval is enabled.")
    lines.append("- Final compliance sign-off remains human-owned.")
    lines.append("")
    lines.append("## Suggested Next Review Questions")
    lines.append("- Which donor/program combinations should be included in a real pilot?")
    lines.append("- What internal review roles need access to findings, comments, and export packages?")
    lines.append("- Which baseline metrics should be captured before pilot start?")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Assemble a buyer-facing GrantFlow pilot pack from a demo-pack run.")
    parser.add_argument("--demo-pack-dir", default="build/demo-pack")
    parser.add_argument("--output-dir", default="build/pilot-pack")
    parser.add_argument("--include-productization-memo", action="store_true")
    args = parser.parse_args()

    demo_pack_dir = Path(str(args.demo_pack_dir)).resolve()
    output_dir = Path(str(args.output_dir)).resolve()

    benchmark_path = demo_pack_dir / "benchmark-results.json"
    if not benchmark_path.exists():
        raise SystemExit(f"Missing benchmark results: {benchmark_path}")

    rows = _read_json(benchmark_path)
    if not isinstance(rows, list) or not rows:
        raise SystemExit("demo-pack benchmark-results.json must contain a non-empty list")

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    _copy_tree(demo_pack_dir, output_dir / "live-runs")

    repo_root = Path(__file__).resolve().parents[1]
    _copy_if_exists(repo_root / "docs" / "buyer-one-pager.md", output_dir / "buyer-one-pager.md")
    _copy_if_exists(repo_root / "docs" / "pilot-evaluation-checklist.md", output_dir / "pilot-evaluation-checklist.md")
    _copy_if_exists(repo_root / "docs" / "demo-runbook.md", output_dir / "demo-runbook.md")
    if bool(args.include_productization_memo):
        _copy_if_exists(repo_root / "docs" / "productization-gaps-memo.md", output_dir / "productization-gaps-memo.md")

    (output_dir / "README.md").write_text(
        _build_summary(
            rows,
            demo_pack_dir_name=demo_pack_dir.name,
            include_productization_memo=bool(args.include_productization_memo),
        ),
        encoding="utf-8",
    )
    print(f"pilot pack saved to {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
