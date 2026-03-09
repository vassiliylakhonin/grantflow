#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def _latest_matching(build_dir: Path, pattern: str, *, kind: str) -> Path | None:
    candidates = []
    for path in build_dir.glob(pattern):
        if not path.exists():
            continue
        if kind == "dir" and not path.is_dir():
            continue
        if kind == "file" and not path.is_file():
            continue
        candidates.append(path)
    if not candidates:
        return None
    return max(candidates, key=lambda path: (path.stat().st_mtime, path.name))


def _resolve_latest_link(build_dir: Path, link_name: str, *, kind: str) -> Path | None:
    link_path = build_dir / link_name
    if not (link_path.exists() or link_path.is_symlink()):
        return None
    target = link_path.resolve()
    if kind == "dir" and target.is_dir():
        return target
    if kind == "file" and target.is_file():
        return target
    return None


def _safe_rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _zip_detail(path: Path, root: Path) -> str:
    size_mb = path.stat().st_size / (1024 * 1024)
    return f"`{_safe_rel(path, root)}` ({size_mb:.2f} MB)"


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _read_json_dict(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _extract_backtick_value(text: str, prefix: str) -> str:
    for line in text.splitlines():
        if line.startswith(prefix) and "`" in line:
            parts = line.split("`")
            if len(parts) >= 3:
                return parts[1]
    return "-"


def _extract_suffix_value(text: str, prefix: str) -> str:
    for line in text.splitlines():
        if line.startswith(prefix):
            return line[len(prefix) :].strip() or "-"
    return "-"


def _extract_line_token(text: str, prefix: str) -> str:
    for line in text.splitlines():
        if line.startswith(prefix):
            return line[len(prefix) :].strip() or "-"
    return "-"


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


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a send-oriented index of current GrantFlow fast/full demo bundles."
    )
    parser.add_argument("--build-dir", default="build")
    parser.add_argument("--output", default="build/send-bundle-index.md")
    args = parser.parse_args()

    build_dir = Path(str(args.build_dir)).resolve()
    output_path = Path(str(args.output)).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    latest_fast_dir = _resolve_latest_link(build_dir, "latest-fast-send-bundle", kind="dir") or _latest_matching(
        build_dir, "release-demo-bundle-fast*/*", kind="dir"
    )
    latest_fast_zip = _resolve_latest_link(build_dir, "latest-fast-send-bundle.zip", kind="file") or _latest_matching(
        build_dir, "release-demo-bundle-fast*/*.zip", kind="file"
    )
    latest_full_dir = _resolve_latest_link(build_dir, "latest-full-send-bundle", kind="dir") or _latest_matching(
        build_dir, "release-demo-bundle/*", kind="dir"
    )
    latest_full_zip = _resolve_latest_link(build_dir, "latest-full-send-bundle.zip", kind="file") or _latest_matching(
        build_dir, "release-demo-bundle/*.zip", kind="file"
    )
    latest_handout = _latest_matching(build_dir, "pilot-handout*.md", kind="file")
    latest_open_order = build_dir / "latest-open-order.md"
    executive_readme = build_dir / "latest-executive-pack" / "README.md"
    executive_summary_path = build_dir / "latest-executive-pack" / "pilot-portfolio-summary.json"
    executive_text = _read_text(executive_readme)
    executive_summary = _read_json_dict(executive_summary_path)
    featured_donor = _extract_backtick_value(executive_text, "- Featured donor: `")
    featured_preset = _extract_backtick_value(executive_text, "- Featured preset: `")
    open_findings = _extract_backtick_value(executive_text, "- Open critic findings (featured case): `")
    fallback_citations = _extract_backtick_value(executive_text, "- Fallback/strategy citations (featured case): `")
    logframe_ready = _extract_backtick_value(executive_text, "- Cases with complete LogFrame operational coverage: `")
    smart_coverage = _extract_backtick_value(executive_text, "- SMART coverage (featured case): `")
    architect_hits = _format_num(executive_summary.get("avg_architect_retrieval_hits_count"))
    architect_grounded_rate = _format_num(executive_summary.get("avg_architect_retrieval_grounded_citation_rate"))
    architect_fallback = _format_num(executive_summary.get("avg_architect_fallback_namespace_citation_count"))
    architect_signal_mix = str(executive_summary.get("architect_evidence_signal_mix") or "").strip() or "-"
    top_architect_signal = str(executive_summary.get("top_architect_evidence_signal") or "").strip() or "-"
    mel_hits = _format_num(executive_summary.get("avg_mel_retrieval_hits_count"))
    mel_grounded_rate = _format_num(executive_summary.get("avg_mel_retrieval_grounded_citation_rate"))
    mel_fallback = _format_num(executive_summary.get("avg_mel_fallback_namespace_citation_count"))
    mel_signal_mix = str(executive_summary.get("mel_evidence_signal_mix") or "").strip() or "-"
    top_mel_signal = str(executive_summary.get("top_mel_evidence_signal") or "").strip() or "-"
    next_primary_action = _extract_backtick_value(executive_text, "- Next primary review action (featured case): `")
    finding_ack_queue = _extract_backtick_value(executive_text, "- Finding ack queue (featured case): `")
    finding_resolve_queue = _extract_backtick_value(executive_text, "- Finding resolve queue (featured case): `")
    comment_ack_queue = _extract_backtick_value(executive_text, "- Comment ack queue (featured case): `")
    comment_resolve_queue = _extract_backtick_value(executive_text, "- Comment resolve queue (featured case): `")
    comment_reopen_queue = _extract_backtick_value(executive_text, "- Comment reopen queue (featured case): `")
    critic_resolution_rate = _extract_backtick_value(executive_text, "- Average critic finding resolution rate: `")
    critic_ack_rate = _extract_backtick_value(executive_text, "- Average critic finding acknowledgment rate: `")
    next_bucket = _extract_backtick_value(executive_text, "- Next review bucket (featured case): `")
    next_action = _extract_suffix_value(executive_text, "- Next recommended action (featured case): ")
    top_reviewer_action = _extract_suffix_value(executive_text, "- Top reviewer action 1 (featured case): ")
    stale_bucket_mix = _extract_backtick_value(executive_text, "- Stale comment bucket mix: `")
    top_stale_bucket = _extract_backtick_value(executive_text, "- Top stale comment bucket: `")
    latest_fast_manifest = build_dir / "latest-fast-send-bundle-manifest.json"
    fast_bundle_manifest = _read_json_dict(latest_fast_manifest)
    latest_fast_readme = latest_fast_dir / "README.md" if latest_fast_dir is not None else None
    fast_bundle_text = _read_text(latest_fast_readme) if latest_fast_readme is not None else ""
    send_policy_status = str(fast_bundle_manifest.get("send_policy_status") or "").strip() or _extract_backtick_value(
        fast_bundle_text, "- Send policy status: `"
    )
    send_policy_classification = str(
        fast_bundle_manifest.get("send_policy_classification") or ""
    ).strip() or _extract_backtick_value(fast_bundle_text, "- Send policy classification: `")
    send_policy_action = str(
        fast_bundle_manifest.get("next_operational_action_before_external_send") or ""
    ).strip() or _extract_backtick_value(fast_bundle_text, "- Next operational action before external send: `")
    bundle_manifest_name = _safe_rel(latest_fast_manifest, build_dir) if latest_fast_manifest.exists() else "-"

    lines: list[str] = []
    lines.append("# GrantFlow Send Bundle Index")
    lines.append("")
    lines.append(f"Generated at: {datetime.now(timezone.utc).isoformat()}")
    lines.append(f"- Build root: `{build_dir}`")
    lines.append("")
    if send_policy_classification == "internal-only":
        lines.append("## External Send Warning")
        lines.append("")
        lines.append(
            "**DO NOT SEND EXTERNALLY:** current workflow policy is `internal-only` and this bundle should stay in internal review until the next operational action is cleared."
        )
        if send_policy_action != "-":
            lines.append(f"- Required next action: `{send_policy_action}`")
        lines.append("")
    elif send_policy_classification == "send-with-conditions":
        lines.append("## External Send Caution")
        lines.append("")
        lines.append(
            "**SEND WITH CONDITIONS:** review the current workflow action and outstanding issues before external sharing."
        )
        if send_policy_action != "-":
            lines.append(f"- Required next action: `{send_policy_action}`")
        lines.append("")
    lines.append("## Recommended Send Choice")
    lines.append("")
    if latest_fast_dir is not None:
        lines.append(f"1. Default buyer send: `{_safe_rel(latest_fast_dir, build_dir)}`")
        if latest_fast_zip is not None:
            lines.append(f"2. Fast zip for email or chat send: {_zip_detail(latest_fast_zip, build_dir)}")
    else:
        lines.append("1. Fast buyer bundle not found. Run `make release-demo-bundle-fast`.")
    if latest_full_dir is not None:
        lines.append(
            f"3. Full send bundle when archive-level diligence is needed: `{_safe_rel(latest_full_dir, build_dir)}`"
        )
        if latest_full_zip is not None:
            lines.append(f"4. Full zip: {_zip_detail(latest_full_zip, build_dir)}")
    else:
        lines.append("3. Full release bundle not found. Run `make release-demo-bundle` if needed.")
    lines.append("")
    lines.append("## When To Use Which")
    lines.append("")
    lines.append(
        "- Fast bundle: first buyer intro, quick follow-up, short partner thread, lightweight internal review."
    )
    lines.append(
        "- Full bundle: deeper diligence, archive review, broader internal circulation, partner technical follow-up."
    )
    lines.append(
        "- Pilot archive/OEM artifacts: only when the recipient needs raw evidence or technical diligence details."
    )
    lines.append("")
    if send_policy_classification != "-":
        lines.append("## Send Policy")
        lines.append("")
        lines.append(f"- Current classification: `{send_policy_classification}`")
        if send_policy_status != "-":
            lines.append(f"- Workflow policy status: `{send_policy_status}`")
        if send_policy_action != "-":
            lines.append(f"- Next operational action before external send: `{send_policy_action}`")
        if bundle_manifest_name != "-":
            lines.append(f"- Manifest: `{bundle_manifest_name}`")
        lines.append("")
    lines.append("## Draft Grounding Snapshot")
    lines.append("")
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
    if executive_text:
        lines.append("## Featured Readiness Snapshot")
        lines.append("")
        lines.append(f"- Featured donor: `{featured_donor}`")
        lines.append(f"- Featured preset: `{featured_preset}`")
        lines.append(f"- Open critic findings: `{open_findings}`")
        lines.append(f"- Fallback/strategy citations: `{fallback_citations}`")
        lines.append(f"- Complete LogFrame operational coverage: `{logframe_ready}`")
        lines.append(f"- SMART coverage (featured case): `{smart_coverage}`")
        lines.append(f"- Architect retrieval hits per case: `{architect_hits}`")
        lines.append(f"- Architect grounded citation rate: `{architect_grounded_rate}`")
        lines.append(f"- Architect fallback citations per case: `{architect_fallback}`")
        if architect_signal_mix != "-":
            lines.append(f"- Architect evidence signal mix: `{architect_signal_mix}`")
        if top_architect_signal != "-":
            lines.append(f"- Top architect evidence signal: `{top_architect_signal}`")
        lines.append(f"- MEL retrieval hits per case: `{mel_hits}`")
        lines.append(f"- MEL grounded citation rate: `{mel_grounded_rate}`")
        lines.append(f"- MEL fallback citations per case: `{mel_fallback}`")
        if mel_signal_mix != "-":
            lines.append(f"- MEL evidence signal mix: `{mel_signal_mix}`")
        if top_mel_signal != "-":
            lines.append(f"- Top MEL evidence signal: `{top_mel_signal}`")
        lines.append(f"- Next primary review action: `{next_primary_action}`")
        lines.append(f"- Finding ack queue: `{finding_ack_queue}`")
        lines.append(f"- Finding resolve queue: `{finding_resolve_queue}`")
        lines.append(f"- Comment ack queue: `{comment_ack_queue}`")
        lines.append(f"- Comment resolve queue: `{comment_resolve_queue}`")
        lines.append(f"- Comment reopen queue: `{comment_reopen_queue}`")
        if critic_resolution_rate != "-":
            lines.append(f"- Portfolio critic finding resolution rate: `{critic_resolution_rate}`")
        if critic_ack_rate != "-":
            lines.append(f"- Portfolio critic finding acknowledgment rate: `{critic_ack_rate}`")
        lines.append(f"- Next review bucket: `{next_bucket}`")
        lines.append(f"- Next recommended action: {next_action}")
        if top_reviewer_action != "-":
            lines.append(f"- Top reviewer action: {top_reviewer_action}")
        if stale_bucket_mix != "-":
            lines.append(f"- Stale comment bucket mix: `{stale_bucket_mix}`")
        if top_stale_bucket != "-":
            lines.append(f"- Top stale comment bucket: `{top_stale_bucket}`")
        lines.append("")
    lines.append("## Supporting Artifacts")
    lines.append("")
    lines.append(
        f"- Pilot handout: `{_safe_rel(latest_handout, build_dir)}`"
        if latest_handout is not None
        else "- Pilot handout: missing"
    )
    lines.append(
        f"- Latest open order: `{_safe_rel(latest_open_order, build_dir)}`"
        if latest_open_order.exists()
        else "- Latest open order: missing"
    )
    lines.append("")
    lines.append("## Send Order")
    lines.append("")
    lines.append("1. Send the fast bundle by default.")
    lines.append("2. If questions come back on evidence, attach the full bundle.")
    lines.append(
        "3. If the audience is technical or OEM-oriented, follow with the OEM pack or pilot archive, not before."
    )
    lines.append("")

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"send bundle index saved to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
