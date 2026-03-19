#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

REQUIRED_LINKS: dict[str, tuple[str, ...]] = {
    "latest-executive-pack": (
        "README.md",
        "buyer-brief.md",
        "pilot-scorecard.md",
    ),
    "latest-pilot-pack": (
        "README.md",
        "pilot-metrics.md",
        "pilot-scorecard.md",
    ),
    "latest-case-study-pack": (),
    "latest-oem-pack": (
        "README.md",
        "oem-one-pager.md",
        "architecture.md",
    ),
    "latest-pilot-archive": (
        "README.md",
        "manifest.json",
    ),
    "latest-diligence-index.md": (),
}


def _check_link(build_dir: Path, link_name: str, required_children: tuple[str, ...]) -> list[str]:
    issues: list[str] = []
    link_path = build_dir / link_name
    if not link_path.exists() and not link_path.is_symlink():
        return [f"missing symlink: {link_name}"]
    if not link_path.is_symlink():
        return [f"not a symlink: {link_name}"]

    resolved = link_path.resolve()
    if not resolved.exists():
        return [f"broken symlink: {link_name} -> {link_path.readlink()}"]

    archive_nested_root: Path | None = None
    if link_name == "latest-pilot-archive" and resolved.is_dir():
        nested_dirs = [path for path in resolved.iterdir() if path.is_dir()]
        if nested_dirs:
            archive_nested_root = sorted(nested_dirs)[0]

    for child in required_children:
        child_path = resolved / child if resolved.is_dir() else None
        if child_path is not None and child_path.exists():
            continue
        if archive_nested_root is not None and (archive_nested_root / child).exists():
            continue
        issues.append(f"missing required artifact under {link_name}: {child}")

    if link_name == "latest-case-study-pack" and resolved.is_dir():
        child_dirs = [path for path in resolved.iterdir() if path.is_dir()]
        if not child_dirs:
            issues.append("latest-case-study-pack has no case subdirectories")
        elif not (child_dirs[0] / "README.md").exists():
            issues.append(f"latest-case-study-pack first case is missing README.md: {child_dirs[0].name}")

    return issues


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify that build/latest-* symlinks and their key demo artifacts are present."
    )
    parser.add_argument("--build-dir", default="build")
    args = parser.parse_args()

    build_dir = Path(str(args.build_dir)).resolve()
    issues: list[str] = []
    for link_name, required_children in REQUIRED_LINKS.items():
        issues.extend(_check_link(build_dir, link_name, required_children))

    if issues:
        for issue in issues:
            print(f"FAIL {issue}")
        raise SystemExit(1)

    for link_name in REQUIRED_LINKS:
        link_path = build_dir / link_name
        print(f"OK {link_name} -> {link_path.readlink()}")
    print("latest stack verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
