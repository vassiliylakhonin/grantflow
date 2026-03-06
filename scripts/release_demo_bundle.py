#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
from datetime import datetime, timezone
from pathlib import Path


def _copy_if_exists(src: Path, dst: Path) -> None:
    if not src.exists():
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


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


def _build_readme(*, build_dir: Path, bundle_name: str, archive_zip_name: str | None) -> str:
    lines: list[str] = []
    lines.append("# GrantFlow Release Demo Bundle")
    lines.append("")
    lines.append(f"Generated at: {datetime.now(timezone.utc).isoformat()}")
    lines.append(f"- Bundle name: `{bundle_name}`")
    lines.append(f"- Build root: `{build_dir}`")
    lines.append("")
    lines.append("## Included")
    lines.append("- `pilot-handout.md`: single-file buyer summary")
    lines.append("- `latest-open-order.md`: what to open and in which order")
    lines.append("- `diligence-index.md`: index of generated local artifacts")
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
    lines.append("1. Share `pilot-handout.md` first.")
    lines.append("2. If needed, share the zip under `artifacts/`.")
    lines.append("3. Use `latest-open-order.md` to walk the recipient through the materials.")
    lines.append("")
    lines.append("## Notes")
    lines.append("- This is a demo/pilot sharing bundle, not a final donor submission package.")
    lines.append("- Human compliance review remains mandatory.")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Assemble a send-ready GrantFlow release demo bundle from the current latest stack."
    )
    parser.add_argument("--build-dir", default="build")
    parser.add_argument("--output-dir", default="build/release-demo-bundle")
    parser.add_argument("--bundle-name", default="grantflow-demo-bundle")
    args = parser.parse_args()

    build_dir = Path(str(args.build_dir)).resolve()
    output_dir = Path(str(args.output_dir)).resolve()
    bundle_name = str(args.bundle_name).strip() or "grantflow-demo-bundle"

    bundle_root = output_dir / bundle_name
    if bundle_root.exists():
        shutil.rmtree(bundle_root)
    bundle_root.mkdir(parents=True, exist_ok=True)

    _copy_if_exists(build_dir / "pilot-handout.md", bundle_root / "pilot-handout.md")
    _copy_if_exists(build_dir / "latest-open-order.md", bundle_root / "latest-open-order.md")
    _copy_if_exists(build_dir / "diligence-index.md", bundle_root / "diligence-index.md")

    archive_zip = _resolve_latest_archive_zip(build_dir)
    archive_zip_name = None
    if archive_zip is not None:
        archive_zip_name = archive_zip.name
        _copy_if_exists(archive_zip, bundle_root / "artifacts" / archive_zip.name)

    (bundle_root / "README.md").write_text(
        _build_readme(
            build_dir=build_dir,
            bundle_name=bundle_name,
            archive_zip_name=archive_zip_name,
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
