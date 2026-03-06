#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
from pathlib import Path


DIRECTORY_PATTERNS = (
    "demo-pack*",
    "pilot-pack*",
    "case-study-pack*",
    "executive-pack*",
    "oem-pack*",
    "pilot-archive*",
)

FILE_PATTERNS = (
    "diligence-index.md",
)


def _dedupe(paths: list[Path]) -> list[Path]:
    seen: set[Path] = set()
    ordered: list[Path] = []
    for path in paths:
        if path in seen:
            continue
        seen.add(path)
        ordered.append(path)
    return ordered


def _collect_paths(build_dir: Path) -> list[Path]:
    paths: list[Path] = []
    for pattern in DIRECTORY_PATTERNS:
        paths.extend(path for path in build_dir.glob(pattern) if path.is_dir())
    for pattern in FILE_PATTERNS:
        paths.extend(path for path in build_dir.glob(pattern) if path.is_file())
    return _dedupe(sorted(paths))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Remove generated GrantFlow demo/pilot/commercial artifacts under build/."
    )
    parser.add_argument("--build-dir", default="build")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    build_dir = Path(str(args.build_dir)).resolve()
    if not build_dir.exists():
        print(f"build dir does not exist: {build_dir}")
        return 0

    paths = _collect_paths(build_dir)
    if not paths:
        print(f"no demo artifacts found under {build_dir}")
        return 0

    for path in paths:
        print(f"{'would remove' if args.dry_run else 'removing'} {path}")
        if args.dry_run:
            continue
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
