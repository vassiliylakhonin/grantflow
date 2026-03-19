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
    ("latest-fast-send-bundle-manifest.json", "release-demo-bundle-fast*/*/manifest.json"),
    ("latest-full-send-bundle-manifest.json", "release-demo-bundle/*/manifest.json"),
)

PREFERRED_TARGETS = {
    "latest-demo-pack": "demo-pack",
    "latest-pilot-pack": "pilot-pack",
    "latest-case-study-pack": "case-study-pack",
    "latest-executive-pack": "executive-pack",
    "latest-oem-pack": "oem-pack",
    "latest-pilot-archive": "pilot-archive",
    "latest-fast-send-bundle": "release-demo-bundle-fast/grantflow-demo-bundle-fast",
    "latest-full-send-bundle": "release-demo-bundle/grantflow-demo-bundle",
    "latest-diligence-index.md": "diligence-index.md",
    "latest-send-bundle-index.md": "send-bundle-index.md",
    "latest-fast-send-bundle.zip": "release-demo-bundle-fast/grantflow-demo-bundle-fast.zip",
    "latest-full-send-bundle.zip": "release-demo-bundle/grantflow-demo-bundle.zip",
}


def _preferred_target_path(build_dir: Path, link_name: str) -> Path | None:
    preferred_name = PREFERRED_TARGETS.get(link_name)
    if preferred_name:
        if link_name in {
            "latest-fast-send-bundle",
            "latest-fast-send-bundle.zip",
            "latest-fast-send-bundle-manifest.json",
        }:
            preferred_choice = _most_recent_existing(
                _internal_only_variant(build_dir, preferred_name),
                build_dir / preferred_name,
            )
            if preferred_choice is not None:
                return preferred_choice
        if link_name in {
            "latest-full-send-bundle",
            "latest-full-send-bundle.zip",
            "latest-full-send-bundle-manifest.json",
        }:
            preferred_choice = _most_recent_existing(
                _internal_only_variant(build_dir, preferred_name),
                build_dir / preferred_name,
            )
            if preferred_choice is not None:
                return preferred_choice
        preferred_path = build_dir / preferred_name
        if preferred_path.exists():
            return preferred_path
    if link_name == "latest-fast-send-bundle-manifest.json":
        base = _preferred_target_path(build_dir, "latest-fast-send-bundle")
        if base is not None:
            manifest = base / "manifest.json"
            if manifest.exists():
                return manifest
    if link_name == "latest-full-send-bundle-manifest.json":
        base = _preferred_target_path(build_dir, "latest-full-send-bundle")
        if base is not None:
            manifest = base / "manifest.json"
            if manifest.exists():
                return manifest
    return None


def _internal_only_variant(build_dir: Path, preferred_name: str) -> Path | None:
    preferred_path = build_dir / preferred_name
    path_string = str(preferred_path)
    if path_string.endswith(".zip"):
        alt = Path(path_string[:-4] + "-internal-only.zip")
    elif path_string.endswith("/manifest.json"):
        alt = Path(path_string[: -len("/manifest.json")] + "-internal-only/manifest.json")
    else:
        alt = Path(path_string + "-internal-only")
    return alt if alt.exists() else None


def _most_recent_existing(*paths: Path | None) -> Path | None:
    candidates = [path for path in paths if path is not None and path.exists()]
    if not candidates:
        return None
    return max(candidates, key=lambda path: (path.stat().st_mtime, path.name))


def _is_generated_pack(path: Path, *, link_name: str, expect_file: bool) -> bool:
    if path.name == link_name or path.name.startswith("latest-"):
        return False
    if expect_file:
        return path.is_file()
    return path.is_dir()


def _pick_latest(build_dir: Path, pattern: str, *, link_name: str, expect_file: bool) -> Path | None:
    preferred_path = _preferred_target_path(build_dir, link_name)
    if preferred_path is not None and _is_generated_pack(preferred_path, link_name=link_name, expect_file=expect_file):
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
