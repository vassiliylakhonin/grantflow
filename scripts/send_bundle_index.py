#!/usr/bin/env python3
from __future__ import annotations

import argparse
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


def _safe_rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _zip_detail(path: Path, root: Path) -> str:
    size_mb = path.stat().st_size / (1024 * 1024)
    return f"`{_safe_rel(path, root)}` ({size_mb:.2f} MB)"


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

    latest_fast_dir = _latest_matching(build_dir, "release-demo-bundle-fast*/*", kind="dir")
    latest_fast_zip = _latest_matching(build_dir, "release-demo-bundle-fast*/*.zip", kind="file")
    latest_full_dir = _latest_matching(build_dir, "release-demo-bundle/*", kind="dir")
    latest_full_zip = _latest_matching(build_dir, "release-demo-bundle/*.zip", kind="file")
    latest_handout = _latest_matching(build_dir, "pilot-handout*.md", kind="file")
    latest_open_order = build_dir / "latest-open-order.md"

    lines: list[str] = []
    lines.append("# GrantFlow Send Bundle Index")
    lines.append("")
    lines.append(f"Generated at: {datetime.now(timezone.utc).isoformat()}")
    lines.append(f"- Build root: `{build_dir}`")
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
