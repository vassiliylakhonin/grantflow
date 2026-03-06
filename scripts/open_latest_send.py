#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


FULL_OPEN_ORDER = (
    (("latest-send-bundle-index.md", "send-bundle-index.md"), "Send bundle index"),
    (("latest-fast-send-bundle/README.md",), "Fast send bundle overview"),
    (("latest-fast-send-bundle/pilot-handout.md",), "Fast send pilot handout"),
    (("latest-fast-send-bundle/executive-pack/README.md",), "Fast send executive pack"),
    (("latest-full-send-bundle/README.md",), "Full send bundle overview"),
)

FAST_OPEN_ORDER = (
    (("latest-send-bundle-index.md", "send-bundle-index.md"), "Send bundle index"),
    (("latest-fast-send-bundle/README.md",), "Fast send bundle overview"),
    (("latest-fast-send-bundle/pilot-handout.md",), "Fast send pilot handout"),
    (("latest-fast-send-bundle/executive-pack/README.md",), "Fast send executive pack"),
    (("latest-fast-send-bundle/executive-pack/buyer-brief.md",), "Fast send buyer brief"),
)


def _resolve_targets(build_dir: Path, *, profile: str) -> list[tuple[str, Path]]:
    open_order = FAST_OPEN_ORDER if profile == "fast" else FULL_OPEN_ORDER
    targets: list[tuple[str, Path]] = []
    missing: list[str] = []
    for candidate_paths, label in open_order:
        resolved_path: Path | None = None
        for relative_path in candidate_paths:
            path = (build_dir / relative_path).resolve()
            if path.exists():
                resolved_path = path
                break
        if resolved_path is None:
            missing.append(" or ".join(candidate_paths))
            continue
        targets.append((label, resolved_path))
    if missing:
        raise SystemExit(
            "Missing send artifacts. Run `make send-bundle-index-refresh` first. Missing: "
            + ", ".join(f"`{item}`" for item in missing)
        )
    return targets


def _print_targets(targets: list[tuple[str, Path]]) -> None:
    print("GrantFlow latest send open order")
    for index, (label, path) in enumerate(targets, start=1):
        print(f"{index}. {label}: {path}")


def _open_targets(targets: list[tuple[str, Path]]) -> None:
    if sys.platform != "darwin":
        raise SystemExit("`--mode open` is supported only on macOS. Use `--mode print` elsewhere.")
    for _, path in targets:
        subprocess.run(["open", str(path)], check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Print or open the latest GrantFlow send artifacts.")
    parser.add_argument("--build-dir", default="build")
    parser.add_argument("--mode", choices=("print", "open"), default="print")
    parser.add_argument("--profile", choices=("fast", "full"), default="full")
    args = parser.parse_args()

    build_dir = Path(str(args.build_dir)).resolve()
    targets = _resolve_targets(build_dir, profile=str(args.profile))
    _print_targets(targets)
    if args.mode == "open":
        _open_targets(targets)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
