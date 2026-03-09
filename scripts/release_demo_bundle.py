#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


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


def _resolve_latest_archive_zip(build_dir: Path) -> Path | None:
    archive_link = build_dir / "latest-pilot-archive"
    if not archive_link.exists() and not archive_link.is_symlink():
        return None
    archive_dir = archive_link.resolve()
    if not archive_dir.exists():
        return None
    latest_named = sorted(archive_dir.glob("*-latest.zip"))
    if latest_named:
        return latest_named[-1]
    zips = sorted(archive_dir.glob("*.zip"))
    if not zips:
        return None
    return max(zips, key=lambda path: (path.stat().st_mtime, path.name))


def _readlink_name(path: Path) -> str:
    if not path.exists() and not path.is_symlink():
        return "-"
    return str(path.readlink()) if path.is_symlink() else path.name


def _format_num(value: object) -> str:
    if value is None or value == "":
        return "-"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value).strip() or "-"
    if number.is_integer():
        return str(int(number))
    return f"{number:.2f}"


def _build_readme(
    *,
    build_dir: Path,
    bundle_name: str,
    archive_zip_name: str | None,
    include_diligence_index: bool,
    include_executive_pack: bool,
    include_pilot_evidence_pack: bool,
    send_policy_status: str | None,
    send_policy_flag: str | None,
    send_policy_action: str | None,
    architect_hits: str,
    architect_grounded_rate: str,
    architect_fallback: str,
    top_architect_signal: str,
    mel_hits: str,
    mel_grounded_rate: str,
    mel_fallback: str,
    top_mel_signal: str,
) -> str:
    lines: list[str] = []
    lines.append("# GrantFlow Release Demo Bundle")
    lines.append("")
    lines.append(f"Generated at: {datetime.now(timezone.utc).isoformat()}")
    lines.append(f"- Bundle name: `{bundle_name}`")
    lines.append(f"- Build root: `{build_dir}`")
    if send_policy_status:
        lines.append(f"- Send policy status: `{send_policy_status}`")
    if send_policy_flag:
        lines.append(f"- Send policy classification: `{send_policy_flag}`")
    if send_policy_action:
        lines.append(f"- Next operational action before external send: `{send_policy_action}`")
    lines.append("")
    lines.append("## Grounding Readiness")
    lines.append(f"- Architect retrieval hits per case: `{architect_hits}`")
    lines.append(f"- Architect grounded citation rate: `{architect_grounded_rate}`")
    lines.append(f"- Architect fallback citations per case: `{architect_fallback}`")
    if top_architect_signal != "-":
        lines.append(f"- Top architect evidence signal: `{top_architect_signal}`")
    lines.append(f"- MEL retrieval hits per case: `{mel_hits}`")
    lines.append(f"- MEL grounded citation rate: `{mel_grounded_rate}`")
    lines.append(f"- MEL fallback citations per case: `{mel_fallback}`")
    if top_mel_signal != "-":
        lines.append(f"- Top MEL evidence signal: `{top_mel_signal}`")
    lines.append("")
    lines.append("## Included")
    lines.append("- `pilot-handout.md`: single-file buyer summary")
    lines.append("- `latest-open-order.md`: what to open and in which order")
    if include_pilot_evidence_pack:
        lines.append("- `pilot-evidence-pack/`: compact pilot evidence summary with before/after and blockers")
    lines.append("- `pilot-portfolio-summary.json`: machine-readable portfolio readiness snapshot")
    lines.append("- `pilot-portfolio-summary.csv`: flat portfolio readiness export")
    if include_diligence_index:
        lines.append("- `diligence-index.md`: index of generated local artifacts")
    if include_executive_pack:
        lines.append("- `executive-pack/`: current buyer-facing package")
    if archive_zip_name:
        lines.append(f"- `artifacts/{archive_zip_name}`: sendable demo archive")
    lines.append("")
    lines.append("## Current Latest Pointers")
    lines.append(f"- Executive pack: `{_readlink_name(build_dir / 'latest-executive-pack')}`")
    lines.append(f"- Pilot pack: `{_readlink_name(build_dir / 'latest-pilot-pack')}`")
    lines.append(f"- Case-study pack: `{_readlink_name(build_dir / 'latest-case-study-pack')}`")
    lines.append(f"- OEM pack: `{_readlink_name(build_dir / 'latest-oem-pack')}`")
    lines.append(f"- Pilot archive: `{_readlink_name(build_dir / 'latest-pilot-archive')}`")
    lines.append("")
    lines.append("## Send Order")
    send_order = ["Share `pilot-handout.md` first."]
    if include_pilot_evidence_pack:
        send_order.append("Use `pilot-evidence-pack/README.md` for the compact pilot evidence view.")
    if include_executive_pack:
        send_order.append("Use `executive-pack/` for the buyer-facing packet.")
    if archive_zip_name:
        send_order.append("If needed, share the zip under `artifacts/`.")
    send_order.append("Use `latest-open-order.md` to walk the recipient through the materials.")
    for index, item in enumerate(send_order, start=1):
        lines.append(f"{index}. {item}")
    lines.append("")
    lines.append("## Notes")
    lines.append("- This is a demo/pilot sharing bundle, not a final donor submission package.")
    lines.append("- Human compliance review remains mandatory.")
    if send_policy_flag == "internal-only":
        lines.append(
            "- Current policy classification is `internal-only`; do not send externally until workflow issues are cleared."
        )
    return "\n".join(lines) + "\n"


def _suffix_bundle_name(bundle_name: str, send_policy_flag: str | None) -> str:
    normalized = str(send_policy_flag or "").strip().lower()
    if normalized == "internal-only" and not bundle_name.endswith("-internal-only"):
        return f"{bundle_name}-internal-only"
    return bundle_name


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Assemble a send-ready GrantFlow release demo bundle from the current latest stack."
    )
    parser.add_argument("--build-dir", default="build")
    parser.add_argument("--output-dir", default="build/release-demo-bundle")
    parser.add_argument("--bundle-name", default="grantflow-demo-bundle")
    parser.add_argument("--include-executive-pack", action="store_true")
    parser.add_argument("--skip-archive", action="store_true")
    parser.add_argument("--skip-diligence-index", action="store_true")
    args = parser.parse_args()

    build_dir = Path(str(args.build_dir)).resolve()
    output_dir = Path(str(args.output_dir)).resolve()
    bundle_name_input = str(args.bundle_name).strip() or "grantflow-demo-bundle"

    send_policy_status = None
    send_policy_flag = None
    send_policy_action = None
    portfolio_summary: dict[str, object] = {}

    latest_pilot_pack = build_dir / "latest-pilot-pack"
    pilot_pack_dir = (
        latest_pilot_pack.resolve() if (latest_pilot_pack.exists() or latest_pilot_pack.is_symlink()) else None
    )
    if pilot_pack_dir:
        portfolio_summary_probe = pilot_pack_dir / "pilot-portfolio-summary.json"
        if portfolio_summary_probe.exists():
            try:
                portfolio_summary = json.loads(portfolio_summary_probe.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                portfolio_summary = {}
            if isinstance(portfolio_summary, dict):
                send_policy_status = (
                    str(portfolio_summary.get("portfolio_review_workflow_policy_status") or "").strip() or None
                )
                send_policy_action = (
                    str(portfolio_summary.get("portfolio_review_workflow_next_operational_action") or "").strip()
                    or None
                )
                go_no_go = (
                    str(portfolio_summary.get("portfolio_review_workflow_policy_go_no_go_flag") or "").strip().lower()
                )
                if go_no_go == "hold":
                    send_policy_flag = "internal-only"
                elif go_no_go == "go_with_conditions":
                    send_policy_flag = "send-with-conditions"
                elif go_no_go == "go":
                    send_policy_flag = "send-safe"

    architect_hits = _format_num(portfolio_summary.get("avg_architect_retrieval_hits_count"))
    architect_grounded_rate = _format_num(portfolio_summary.get("avg_architect_retrieval_grounded_citation_rate"))
    architect_fallback = _format_num(portfolio_summary.get("avg_architect_fallback_namespace_citation_count"))
    top_architect_signal = str(portfolio_summary.get("top_architect_evidence_signal") or "").strip() or "-"
    mel_hits = _format_num(portfolio_summary.get("avg_mel_retrieval_hits_count"))
    mel_grounded_rate = _format_num(portfolio_summary.get("avg_mel_retrieval_grounded_citation_rate"))
    mel_fallback = _format_num(portfolio_summary.get("avg_mel_fallback_namespace_citation_count"))
    top_mel_signal = str(portfolio_summary.get("top_mel_evidence_signal") or "").strip() or "-"

    bundle_name = _suffix_bundle_name(bundle_name_input, send_policy_flag)

    bundle_root = output_dir / bundle_name
    if bundle_root.exists():
        shutil.rmtree(bundle_root)
    bundle_root.mkdir(parents=True, exist_ok=True)

    _copy_if_exists(build_dir / "pilot-handout.md", bundle_root / "pilot-handout.md")
    _copy_if_exists(build_dir / "latest-open-order.md", bundle_root / "latest-open-order.md")
    pilot_evidence_pack_dir = build_dir / "pilot-evidence-pack"
    include_pilot_evidence_pack = pilot_evidence_pack_dir.exists()
    if include_pilot_evidence_pack:
        _copy_tree_if_exists(pilot_evidence_pack_dir, bundle_root / "pilot-evidence-pack")
    if pilot_pack_dir:
        _copy_if_exists(pilot_pack_dir / "pilot-portfolio-summary.json", bundle_root / "pilot-portfolio-summary.json")
        _copy_if_exists(pilot_pack_dir / "pilot-portfolio-summary.csv", bundle_root / "pilot-portfolio-summary.csv")
    include_diligence_index = not bool(args.skip_diligence_index)
    if include_diligence_index:
        _copy_if_exists(build_dir / "diligence-index.md", bundle_root / "diligence-index.md")
    include_executive_pack = bool(args.include_executive_pack)
    if include_executive_pack:
        executive_pack_link = build_dir / "latest-executive-pack"
        if executive_pack_link.exists() or executive_pack_link.is_symlink():
            _copy_tree_if_exists(executive_pack_link.resolve(), bundle_root / "executive-pack")

    archive_zip = _resolve_latest_archive_zip(build_dir)
    archive_zip_name = None
    if archive_zip is not None and not bool(args.skip_archive):
        archive_zip_name = archive_zip.name
        _copy_if_exists(archive_zip, bundle_root / "artifacts" / archive_zip.name)

    manifest = {
        "bundle_name": bundle_name,
        "bundle_name_input": bundle_name_input,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "send_policy_status": send_policy_status,
        "send_policy_classification": send_policy_flag,
        "next_operational_action_before_external_send": send_policy_action,
        "grounding_readiness": {
            "architect_retrieval_hits_per_case": architect_hits,
            "architect_grounded_citation_rate": architect_grounded_rate,
            "architect_fallback_citations_per_case": architect_fallback,
            "top_architect_evidence_signal": top_architect_signal,
            "mel_retrieval_hits_per_case": mel_hits,
            "mel_grounded_citation_rate": mel_grounded_rate,
            "mel_fallback_citations_per_case": mel_fallback,
            "top_mel_evidence_signal": top_mel_signal,
        },
        "includes": {
            "pilot_handout": (bundle_root / "pilot-handout.md").exists(),
            "latest_open_order": (bundle_root / "latest-open-order.md").exists(),
            "pilot_evidence_pack": (bundle_root / "pilot-evidence-pack").exists(),
            "pilot_portfolio_summary_json": (bundle_root / "pilot-portfolio-summary.json").exists(),
            "pilot_portfolio_summary_csv": (bundle_root / "pilot-portfolio-summary.csv").exists(),
            "diligence_index": (bundle_root / "diligence-index.md").exists(),
            "executive_pack": (bundle_root / "executive-pack").exists(),
            "archive_zip": archive_zip_name is not None,
        },
    }
    (bundle_root / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    (bundle_root / "README.md").write_text(
        _build_readme(
            build_dir=build_dir,
            bundle_name=bundle_name,
            archive_zip_name=archive_zip_name,
            include_diligence_index=include_diligence_index,
            include_executive_pack=include_executive_pack,
            include_pilot_evidence_pack=include_pilot_evidence_pack,
            send_policy_status=send_policy_status,
            send_policy_flag=send_policy_flag,
            send_policy_action=send_policy_action,
            architect_hits=architect_hits,
            architect_grounded_rate=architect_grounded_rate,
            architect_fallback=architect_fallback,
            top_architect_signal=top_architect_signal,
            mel_hits=mel_hits,
            mel_grounded_rate=mel_grounded_rate,
            mel_fallback=mel_fallback,
            top_mel_signal=top_mel_signal,
        ),
        encoding="utf-8",
    )

    zip_path = Path(
        shutil.make_archive(str(output_dir / bundle_name), "zip", root_dir=output_dir, base_dir=bundle_name)
    )
    print(f"release demo bundle saved to {bundle_root} and {zip_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
