#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

OEM_DOCS = (
    "docs/oem-one-pager.md",
    "docs/architecture.md",
    "docs/operations-runbook.md",
    "docs/contributor-map.md",
    "docs/api-stability-policy.md",
    "docs/demo-runbook.md",
    "docs/productization-gaps-memo.md",
    "SECURITY.md",
    "README.md",
)

OEM_OPTIONAL_DIRS = ("docs/samples",)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _copy_if_exists(src: Path, dst: Path) -> None:
    if src.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def _copy_tree_if_exists(src: Path, dst: Path) -> None:
    if not src.exists():
        return
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def _slugify(value: str) -> str:
    token = "".join(ch if ch.isalnum() else "-" for ch in value.strip().lower())
    while "--" in token:
        token = token.replace("--", "-")
    return token.strip("-") or "pack"


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
    oem_pack_name: str,
    pilot_pack_name: str,
    executive_pack_name: str,
    featured_case_dir: str,
    rows: list[dict[str, Any]],
) -> str:
    done_cases = sum(1 for row in rows if str(row.get("status") or "").strip().lower() == "done")
    donors = sorted({str(row.get("donor_id") or "").strip() for row in rows if str(row.get("donor_id") or "").strip()})

    lines: list[str] = []
    lines.append("# GrantFlow OEM Pack")
    lines.append("")
    lines.append(f"Generated at: {datetime.now(timezone.utc).isoformat()}")
    lines.append(f"- OEM pack: `{oem_pack_name}`")
    lines.append(f"- Source pilot pack: `{pilot_pack_name}`")
    lines.append(f"- Source executive pack: `{executive_pack_name}`")
    lines.append("")
    lines.append("## Purpose")
    lines.append(
        "This folder is intended for technical partners, OEM evaluators, and platform diligence reviews. "
        "It combines product framing, architecture/ops/security docs, and one representative packaged case."
    )
    lines.append("")
    lines.append("## Snapshot")
    lines.append(f"- Cases represented in source pilot pack: `{len(rows)}`")
    lines.append(f"- Terminal done cases: `{done_cases}/{len(rows)}`")
    lines.append(f"- Donors represented: {', '.join(f'`{donor}`' for donor in donors) if donors else '-'}")
    lines.append(f"- Featured case: `{featured_case_dir}`")
    lines.append("")
    lines.append("## Open In Order")
    lines.append("1. `oem-one-pager.md`")
    lines.append("2. `architecture.md`")
    lines.append("3. `operations-runbook.md`")
    lines.append("4. `contributor-map.md`")
    lines.append("5. `api-stability-policy.md`")
    lines.append("6. `executive-pack/README.md`")
    lines.append("7. `executive-pack/case-study/.../README.md`")
    lines.append("")
    lines.append("## Notes")
    lines.append("- This pack is for technical and product diligence, not final customer delivery.")
    lines.append("- Built-in auth is API-key oriented; enterprise IAM is expected at partner/gateway layer.")
    lines.append("- Human compliance review remains mandatory for real donor submissions.")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Assemble a technical OEM/partner diligence pack from existing GrantFlow bundles."
    )
    parser.add_argument("--pilot-pack-dir", default="build/pilot-pack")
    parser.add_argument("--executive-pack-dir", default="build/executive-pack")
    parser.add_argument("--output-dir", default="build/oem-pack")
    parser.add_argument("--preset-key", default="")
    parser.add_argument("--case-dir", default="")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    pilot_pack_dir = Path(str(args.pilot_pack_dir)).resolve()
    executive_pack_dir = Path(str(args.executive_pack_dir)).resolve()
    output_dir = Path(str(args.output_dir)).resolve()

    benchmark_path = pilot_pack_dir / "live-runs" / "benchmark-results.json"
    if not benchmark_path.exists():
        raise SystemExit(f"Missing pilot benchmark results: {benchmark_path}")
    rows = _read_json(benchmark_path)
    if not isinstance(rows, list) or not rows:
        raise SystemExit("pilot pack live-runs/benchmark-results.json must contain a non-empty list")

    featured_case_dir = _resolve_case_dir(
        rows,
        preset_key=str(args.preset_key).strip(),
        case_dir=str(args.case_dir).strip(),
    )

    if not executive_pack_dir.exists():
        raise SystemExit(f"Missing executive pack directory: {executive_pack_dir}. Run make executive-pack first.")

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for relative_path in OEM_DOCS:
        src = repo_root / relative_path
        _copy_if_exists(src, output_dir / Path(relative_path).name)

    for relative_dir in OEM_OPTIONAL_DIRS:
        src_dir = repo_root / relative_dir
        if src_dir.exists():
            _copy_tree_if_exists(src_dir, output_dir / Path(relative_dir).name)

    _copy_tree_if_exists(executive_pack_dir, output_dir / "executive-pack")

    (output_dir / "README.md").write_text(
        _build_summary(
            oem_pack_name=output_dir.name,
            pilot_pack_name=pilot_pack_dir.name,
            executive_pack_name=executive_pack_dir.name,
            featured_case_dir=featured_case_dir,
            rows=rows,
        ),
        encoding="utf-8",
    )
    print(f"oem pack saved to {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
