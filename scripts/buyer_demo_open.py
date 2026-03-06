#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


OPEN_ORDER = (
    (("latest-open-order.md",), "Opening guide"),
    (("pilot-handout.md", "pilot-handout-smoke.md"), "Single-file buyer summary"),
    (("latest-executive-pack/README.md",), "Executive pack overview"),
    (("latest-executive-pack/buyer-brief.md",), "Executive commercial summary"),
    (("latest-executive-pack/pilot-scorecard.md",), "Current pilot verdict"),
    (("latest-executive-pack/pilot-metrics.md",), "Pilot metrics summary"),
)


def _resolve_targets(build_dir: Path) -> list[tuple[str, Path]]:
    targets: list[tuple[str, Path]] = []
    missing: list[str] = []
    for candidate_paths, label in OPEN_ORDER:
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
            "Missing buyer demo artifacts. Run `make pilot-refresh-fast` or "
            "`make buyer-demo-open-refresh` first. Missing: " + ", ".join(f"`{item}`" for item in missing)
        )
    return targets


def _print_targets(targets: list[tuple[str, Path]]) -> None:
    print("GrantFlow buyer demo open order")
    for index, (label, path) in enumerate(targets, start=1):
        print(f"{index}. {label}: {path}")


def _open_targets(targets: list[tuple[str, Path]]) -> None:
    if sys.platform != "darwin":
        raise SystemExit("`--mode open` is supported only on macOS. Use `--mode print` elsewhere.")
    for _, path in targets:
        subprocess.run(["open", str(path)], check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Print or open the recommended buyer-facing GrantFlow demo materials.")
    parser.add_argument("--build-dir", default="build")
    parser.add_argument("--mode", choices=("print", "open"), default="print")
    args = parser.parse_args()

    build_dir = Path(str(args.build_dir)).resolve()
    targets = _resolve_targets(build_dir)
    _print_targets(targets)
    if args.mode == "open":
        _open_targets(targets)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
