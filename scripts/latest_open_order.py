#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path


LINK_ORDER = (
    ("latest-diligence-index.md", "Index of all generated artifacts."),
    ("latest-executive-pack", "Primary buyer-facing bundle."),
    ("latest-pilot-pack", "Full pilot evidence bundle."),
    ("latest-case-study-pack", "Representative single-case pack."),
    ("latest-oem-pack", "Technical diligence bundle."),
    ("latest-pilot-archive", "Sendable archive staging folder."),
)


def _readlink_target(path: Path) -> str:
    if not path.exists() and not path.is_symlink():
        return "-"
    if not path.is_symlink():
        return str(path.name)
    return str(path.readlink())


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


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


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a short open-order guide for the latest GrantFlow demo/commercial artifacts."
    )
    parser.add_argument("--build-dir", default="build")
    parser.add_argument("--output", default="build/latest-open-order.md")
    args = parser.parse_args()

    build_dir = Path(str(args.build_dir)).resolve()
    output_path = Path(str(args.output)).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    executive_readme = build_dir / "latest-executive-pack" / "README.md"
    executive_text = _read_text(executive_readme)
    featured_donor = _extract_backtick_value(executive_text, "- Featured donor: `")
    open_findings = _extract_backtick_value(executive_text, "- Open critic findings (featured case): `")
    fallback_citations = _extract_backtick_value(executive_text, "- Fallback/strategy citations (featured case): `")
    logframe_ready = _extract_backtick_value(executive_text, "- Cases with complete LogFrame operational coverage: `")
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

    lines: list[str] = []
    lines.append("# GrantFlow Latest Open Order")
    lines.append("")
    lines.append(f"Generated at: {datetime.now(timezone.utc).isoformat()}")
    lines.append(f"- Build root: `{build_dir}`")
    lines.append("")
    lines.append("## Recommended Order")
    lines.append("")
    for index, (link_name, purpose) in enumerate(LINK_ORDER, start=1):
        link_path = build_dir / link_name
        target = _readlink_target(link_path)
        status = "present" if link_path.exists() or link_path.is_symlink() else "missing"
        lines.append(f"{index}. `{link_name}` -> `{target}` ({status})")
        lines.append(f"   {purpose}")
    lines.append("")
    lines.append("## Suggested Review Path")
    lines.append("")
    lines.append("1. Open `latest-executive-pack/README.md` first.")
    lines.append("2. Then read `latest-executive-pack/buyer-brief.md` and `latest-executive-pack/pilot-scorecard.md`.")
    lines.append("3. Use `latest-pilot-pack/README.md` for complete evidence and exports.")
    lines.append("4. Use `latest-case-study-pack/.../README.md` for the representative example.")
    lines.append("5. Use `latest-oem-pack/README.md` when the audience is technical or partnership-focused.")
    lines.append("6. Use `latest-pilot-archive/` or the zip under the archive folder for external sharing.")
    lines.append("")
    if executive_text:
        lines.append("## Featured Readiness Snapshot")
        lines.append("")
        lines.append(f"- Featured donor: `{featured_donor}`")
        lines.append(f"- Open critic findings: `{open_findings}`")
        lines.append(f"- Fallback/strategy citations: `{fallback_citations}`")
        lines.append(f"- Complete LogFrame operational coverage: `{logframe_ready}`")
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
        lines.append("")
    lines.append("## Notes")
    lines.append("")
    lines.append("- This guide depends on `make latest-links` having run successfully.")
    lines.append("- Missing entries indicate the corresponding pack has not been generated yet.")
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"latest open order saved to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
