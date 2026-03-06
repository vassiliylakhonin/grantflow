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
    lines.append("## Notes")
    lines.append("")
    lines.append("- This guide depends on `make latest-links` having run successfully.")
    lines.append("- Missing entries indicate the corresponding pack has not been generated yet.")
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"latest open order saved to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
