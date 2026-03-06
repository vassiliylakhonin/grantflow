#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path


LINK_SPECS = (
    ("latest-demo-pack", "demo-pack*"),
    ("latest-pilot-pack", "pilot-pack*"),
    ("latest-case-study-pack", "case-study-pack*"),
    ("latest-executive-pack", "executive-pack*"),
    ("latest-oem-pack", "oem-pack*"),
    ("latest-pilot-archive", "pilot-archive*"),
    ("latest-fast-send-bundle", "release-demo-bundle-fast*/*"),
    ("latest-full-send-bundle", "release-demo-bundle/*"),
)

FILE_LINK_SPECS = (
    ("latest-diligence-index.md", "diligence-index.md"),
    ("latest-send-bundle-index.md", "send-bundle-index.md"),
    ("latest-fast-send-bundle.zip", "release-demo-bundle-fast*/*.zip"),
    ("latest-full-send-bundle.zip", "release-demo-bundle/*.zip"),
)

PREFERRED_TARGETS = {
    "latest-demo-pack": "demo-pack",
    "latest-pilot-pack": "pilot-pack",
    "latest-case-study-pack": "case-study-pack",
    "latest-executive-pack": "executive-pack",
    "latest-oem-pack": "oem-pack",
    "latest-pilot-archive": "pilot-archive",
    "latest-diligence-index.md": "diligence-index.md",
    "latest-send-bundle-index.md": "send-bundle-index.md",
}


def _is_generated_pack(path: Path, *, link_name: str, expect_file: bool) -> bool:
    if path.name == link_name or path.name.startswith("latest-"):
        return False
    if expect_file:
        return path.is_file()
    return path.is_dir()


def _pick_latest(build_dir: Path, pattern: str, *, link_name: str, expect_file: bool) -> Path | None:
    preferred_name = PREFERRED_TARGETS.get(link_name)
    if preferred_name:
        preferred_path = build_dir / preferred_name
        if preferred_path.exists() and _is_generated_pack(preferred_path, link_name=link_name, expect_file=expect_file):
            return preferred_path

    candidates = [
        path
        for path in build_dir.glob(pattern)
        if _is_generated_pack(path, link_name=link_name, expect_file=expect_file)
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda path: (path.stat().st_mtime, path.name))


def _replace_symlink(link_path: Path, target: Path) -> None:
    if link_path.exists() or link_path.is_symlink():
        if link_path.is_dir() and not link_path.is_symlink():
            raise SystemExit(f"Refusing to replace non-symlink directory: {link_path}")
        link_path.unlink()
    target_rel = target.relative_to(link_path.parent)
    link_path.symlink_to(target_rel, target_is_directory=target.is_dir())


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create stable latest-* symlinks for generated GrantFlow demo/commercial artifacts."
    )
    parser.add_argument("--build-dir", default="build")
    args = parser.parse_args()

    build_dir = Path(str(args.build_dir)).resolve()
    build_dir.mkdir(parents=True, exist_ok=True)

    created = 0
    for link_name, pattern in LINK_SPECS:
        target = _pick_latest(build_dir, pattern, link_name=link_name, expect_file=False)
        if target is None:
            continue
        link_path = build_dir / link_name
        _replace_symlink(link_path, target)
        print(f"{link_path} -> {target}")
        created += 1

    for link_name, pattern in FILE_LINK_SPECS:
        target = _pick_latest(build_dir, pattern, link_name=link_name, expect_file=True)
        if target is None:
            continue
        link_path = build_dir / link_name
        _replace_symlink(link_path, target)
        print(f"{link_path} -> {target}")
        created += 1

    if created == 0:
        print(f"no generated artifacts found under {build_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
